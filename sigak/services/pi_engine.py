"""PI 리포트 생성 엔진 — Phase I3 스켈레톤.

CLAUDE.md §5.1 / §7.1 / §7.2 / §7.3 정의.

파이프라인:
  1. UserDataVault 로드 + UserTasteProfile 생성
  2. Apify limit=30 피드 수집 (fetch_ig_profile_for_pi)
  3. determine_pi_photo_count → (public_n, locked_n) 유동 결정
  4. Sonnet Vision 카테고리 선별 (7 카테고리)
  5. KnowledgeMatcher 매칭 → trends / (methodologies, references 는 v1.1+ KB 확장)
  6. R2 저장 (pi_reports/{report_id}/...)
  7. SiaWriter (현 Stub) 로 photo comments + boundary_message + overall_message
  8. 아이작 M REPORT 패턴 필드 (user_summary / needs_statement / user_original_phrases)
     — Phase H 완료 전까지 stub placeholder
  9. DB persist + is_current / version 관리
  10. PIReport 반환

Phase H 완료 후 교체 예정:
  - SiaWriter concrete 주입 (photo comments / overall message)
  - user_summary / needs_statement Haiku 생성
"""
from __future__ import annotations

import base64
import json
import logging
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Optional

import anthropic
from sqlalchemy import text

from config import get_settings
from schemas.pi_report import (
    PhotoCategory,
    PhotoInsight,
    PIReport,
    PIReportSources,
)
from schemas.user_profile import IgLatestPost
from schemas.user_taste import UserTasteProfile
from services import r2_client
from services.coordinate_system import VisualCoordinate
from services.ig_scraper import fetch_ig_profile_for_pi
from services.knowledge_matcher import match_trends_for_user
from services.sia_writer import get_sia_writer
from services.user_data_vault import UserDataVault, load_vault


logger = logging.getLogger(__name__)


class PIEngineError(Exception):
    """복구 불가 오류. caller 는 toekn refund / 사용자 안내."""


# ─────────────────────────────────────────────
#  Photo count 유동 로직
# ─────────────────────────────────────────────

def determine_pi_photo_count(available_photos: int) -> tuple[int, int]:
    """가용 사진 수 → (public_n, locked_n).

    규칙 (CLAUDE.md 확정):
      available <= 15 : 전부 사용. public = max(1, total // 3), locked = total - public
      16 <= available <= 40 : public=5, locked=10 (총 15)
      available > 40 : public=5, locked=max(10, min(available//6, 15))

    예시:
      8  → 3 / 5
      12 → 4 / 8
      20 → 5 / 10
      50 → 5 / 13 (min(8, 15) → 10 과 비교 → 10)
         실제 50//6 = 8, min(8,15)=8, max(10, 8)=10. 따라서 5/10.
      150 → 5 / 15 (150//6=25, min(25,15)=15, max(10,15)=15)
    """
    if available_photos <= 0:
        return (0, 0)
    if available_photos <= 15:
        public = max(1, available_photos // 3)
        return (public, available_photos - public)
    if available_photos <= 40:
        return (5, 10)
    locked = max(10, min(available_photos // 6, 15))
    return (5, locked)


# ─────────────────────────────────────────────
#  Main entry
# ─────────────────────────────────────────────

def generate_pi_report(
    db,
    *,
    user_id: str,
    force_new_version: bool = False,
) -> PIReport:
    """PI 리포트 생성 — 버전 관리 포함.

    Args:
      db: SQLAlchemy session (caller 가 commit)
      user_id: 대상 유저
      force_new_version: True 이면 is_current 아카이브 후 새 버전, False 면 기존 is_current 재사용

    Raises:
      PIEngineError — vault 없음 / Apify 실패 / Sonnet 빈 응답 등 복구 불가
    """
    if db is None:
        raise PIEngineError("db unavailable")

    # 0. 기존 is_current 확인
    if not force_new_version:
        existing = _load_current_report(db, user_id)
        if existing is not None:
            return existing

    # 1. Vault + profile
    vault = load_vault(db, user_id)
    if vault is None:
        raise PIEngineError(f"user_profile not found for user={user_id}")
    profile = vault.get_user_taste_profile()

    # 2. Apify limit=30 피드 수집
    handle = vault.basic_info.ig_handle
    feed_photos: list[IgLatestPost] = []
    ig_analysis_present = False
    if handle:
        status, cache = fetch_ig_profile_for_pi(handle)
        if status == "success" and cache is not None:
            feed_photos = list(cache.latest_posts or [])
            ig_analysis_present = cache.analysis is not None
        elif status == "private":
            # 비공개 계정 — latest_posts 없음. MVP 는 empty 로 진행.
            feed_photos = []
        # skipped / failed 는 feed 없이 진행 (boundary_message 가 동적 대응)

    available = sum(1 for p in feed_photos if p.display_url)
    public_n, locked_n = determine_pi_photo_count(available)

    # 3. KB 매칭
    gender = vault.basic_info.gender if vault.basic_info.gender in ("female", "male") else "female"
    matched = match_trends_for_user(profile, gender=gender, season=None, limit=5)  # type: ignore[arg-type]
    matched_trend_ids = [m.trend.trend_id for m in matched]

    # 4. Sonnet Vision 카테고리 선별 (feed_photos 가 1 장 이상일 때만)
    selections: list[dict] = []
    if feed_photos and (public_n + locked_n > 0):
        try:
            selections = _sonnet_select_for_pi(
                feed_photos=feed_photos,
                public_n=public_n,
                locked_n=locked_n,
                profile=profile,
                matched_trend_ids=matched_trend_ids,
            )
        except PIEngineError:
            raise
        except Exception as e:
            logger.exception("Sonnet PI selection failed: user=%s", user_id)
            raise PIEngineError(f"Sonnet selection failed: {e}")

    # 5. Materialize — R2 저장 + SelectedPhoto 조립
    report_id = _generate_report_id()
    public_photos, locked_photos = _materialize_selections(
        user_id=user_id,
        report_id=report_id,
        feed_photos=feed_photos,
        selections=selections,
        profile=profile,
    )

    # 6. Stub 텍스트 (Phase H 완료 후 concrete 교체)
    writer = get_sia_writer()
    overall = writer.generate_overall_message(
        profile=profile,
        context={"product": "pi", "feed_count": available},
    )
    boundary = _compose_boundary_message(
        profile=profile,
        feed_count=available,
        public_n=len(public_photos),
        locked_n=len(locked_photos),
    )

    # Phase H 완료 시 Haiku 로 교체. 현재 placeholder.
    user_original_phrases = profile.user_original_phrases or []
    user_summary = _stub_user_summary(profile, user_original_phrases)
    needs_statement = _stub_needs_statement(profile)

    # 7. Sources 기록
    sources = PIReportSources(
        feed_photo_count=available,
        ig_analysis_present=ig_analysis_present,
        conversation_field_count=_count_filled_fields(vault),
        user_original_phrases_count=len(user_original_phrases),
        aspiration_history_count=vault.aspiration_count,
        best_shot_history_count=vault.best_shot_count,
        vault_strength_score=profile.strength_score,
        selected_from_count=available,
        public_count=len(public_photos),
        locked_count=len(locked_photos),
    )

    # 8. 버전 계산 + 기존 is_current 아카이브
    new_version = _next_version_for_user(db, user_id)
    _archive_prior_current(db, user_id)

    now = datetime.now(timezone.utc)
    report = PIReport(
        report_id=report_id,
        user_id=user_id,
        version=new_version,
        is_current=True,
        generated_at=now,
        public_photos=public_photos,
        locked_photos=locked_photos,
        user_taste_profile_snapshot=profile.model_dump(mode="json"),
        user_summary=user_summary,
        needs_statement=needs_statement,
        user_original_phrases=user_original_phrases,
        sia_overall_message=overall,
        boundary_message=boundary,
        matched_trend_ids=matched_trend_ids,
        matched_methodology_ids=[],
        matched_reference_ids=[],
        data_sources_used=sources,
    )

    # 9. DB persist
    _persist_report(db, report)
    return report


# ─────────────────────────────────────────────
#  Sonnet Vision selection
# ─────────────────────────────────────────────

_PI_SELECT_SYSTEM_PROMPT = """당신은 SIGAK 의 PI (시각이 본 당신) 선별 엔진입니다.

유저 본인 IG 피드 사진을 받아 7 카테고리 중 적절히 배분하여 선별합니다.

카테고리:
  signature         — 유저다움 집약 (공개 영역). 가장 정체성 드러나는 장면.
  detail_analysis   — 세부 관찰 (특정 각도/구도 선명한 사진)
  aspiration_gap   — 추구미 비교 근거 (유저가 지향하는 방향 보이는 장면)
  weaker_angle     — 거리 있는 방향 (유저답지 않거나 어색한 장면)
  style_element    — 색 팔레트 / 스타일 요소가 뚜렷한 사진
  trend_match      — 매칭된 KB 트렌드 방향에 맞는 사진
  methodology      — 방법론 설명 보조용 (어떤 결을 어떻게 만드는지)

할당 규칙:
  - signature 는 반드시 정확히 public_n 개 (공개 영역)
  - 나머지 6 카테고리에 locked_n 개 배분 (한 카테고리 최소 0 ~ 최대 총 locked_n/2 권장)
  - associated_trend_id 는 trend_match / methodology 카테고리에서만 채움

출력 JSON (엄격):
{
  "selections": [
    {
      "photo_index": 0,
      "category": "signature",
      "rank_within_category": 1,
      "rationale": "짧은 서술, 페르소나 독립 — 객관 팩트 위주",
      "associated_trend_id": null
    }
    // public_n + locked_n 개
  ]
}

Hard Rules:
  - photo_index 는 입력 이미지 순서 0-based
  - selections 개수 = public_n + locked_n 정확
  - rationale 은 1-2 문장, 구어체 어미 금지 (군요 / 같아요 / 것 같 / ㅋㅋ 전부 금지)
  - Sonnet 자체 페르소나 개입 금지 — Sia 해석은 별도 단계 (현 SiaWriter stub) 가 담당
  - JSON 외 텍스트 금지
"""


def _sonnet_select_for_pi(
    *,
    feed_photos: list[IgLatestPost],
    public_n: int,
    locked_n: int,
    profile: UserTasteProfile,
    matched_trend_ids: list[str],
) -> list[dict]:
    """Sonnet Vision 호출. return: selections dict list."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise PIEngineError("ANTHROPIC_API_KEY not configured")

    # 이미지 다운로드 + base64 (Instagram CDN robots.txt 우회)
    image_blocks: list[dict] = []
    index_map: list[int] = []     # 실제 feed_photos index 와 image_block index 매핑
    for idx, post in enumerate(feed_photos):
        if not post.display_url:
            continue
        try:
            import httpx
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(post.display_url)
                resp.raise_for_status()
                b64 = base64.b64encode(resp.content).decode("ascii")
            image_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })
            index_map.append(idx)
        except Exception:
            logger.warning("PI selection: download failed idx=%d", idx)
            continue

    if not image_blocks:
        raise PIEngineError("no downloadable images for PI selection")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Profile summary for Sonnet
    profile_summary = {
        "current_position": (
            profile.current_position.model_dump(mode="json")
            if profile.current_position else None
        ),
        "aspiration_vector": (
            profile.aspiration_vector.model_dump(mode="json")
            if profile.aspiration_vector else None
        ),
        "user_original_phrases": profile.user_original_phrases,
        "strength_score": profile.strength_score,
    }

    text_prompt = (
        f"public_n = {public_n}\n"
        f"locked_n = {locked_n}\n"
        f"profile: {json.dumps(profile_summary, ensure_ascii=False)}\n"
        f"matched_trends: {json.dumps(matched_trend_ids, ensure_ascii=False)}\n"
        f"이미지 수 = {len(image_blocks)}\n\n"
        "photo_index 는 위 이미지 순서 0-based.\n"
        "signature 정확 public_n 개, 나머지 카테고리 총 locked_n 개 분배."
    )

    user_content = image_blocks + [{"type": "text", "text": text_prompt}]

    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=2500,
        system=_PI_SELECT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    if not response.content:
        raise PIEngineError("empty Sonnet response")
    text_blocks = [b.text for b in response.content if b.type == "text"]
    raw = "\n".join(text_blocks).strip()
    raw = _strip_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise PIEngineError(f"Sonnet PI response not valid JSON: {e}")

    selections = parsed.get("selections") if isinstance(parsed, dict) else None
    if not isinstance(selections, list):
        raise PIEngineError("PI selections malformed")

    # photo_index 를 원본 feed_photos index 로 변환 (image_blocks 은 display_url 없는 것 제외했으므로)
    remapped: list[dict] = []
    for entry in selections:
        block_idx = entry.get("photo_index")
        if not isinstance(block_idx, int) or block_idx < 0 or block_idx >= len(index_map):
            continue
        entry["photo_index"] = index_map[block_idx]
        remapped.append(entry)
    return remapped


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        lines = t.split("\n")
        if len(lines) > 1:
            lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


# ─────────────────────────────────────────────
#  Materialize — R2 저장 + PhotoInsight
# ─────────────────────────────────────────────

def _materialize_selections(
    *,
    user_id: str,
    report_id: str,
    feed_photos: list[IgLatestPost],
    selections: list[dict],
    profile: UserTasteProfile,
) -> tuple[list[PhotoInsight], list[PhotoInsight]]:
    """Sonnet 선별 결과 → PhotoInsight + R2 저장. (public, locked) 분리."""
    import httpx
    writer = get_sia_writer()

    publics: list[PhotoInsight] = []
    lockeds: list[PhotoInsight] = []

    for entry in selections:
        idx = entry.get("photo_index")
        category = entry.get("category")
        if not isinstance(idx, int) or idx < 0 or idx >= len(feed_photos):
            continue
        if category not in (
            "signature", "detail_analysis", "aspiration_gap", "weaker_angle",
            "style_element", "trend_match", "methodology",
        ):
            continue

        post = feed_photos[idx]
        if not post.display_url:
            continue

        photo_id = f"photo_{idx:03d}_{uuid.uuid4().hex[:8]}.jpg"
        r2_key = r2_client.user_photo_key(
            user_id, f"pi_reports/{report_id}/{photo_id}",
        )

        # Download + put to R2 (PI 는 영구 저장)
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(post.display_url)
                resp.raise_for_status()
                r2_client.put_bytes(r2_key, resp.content, content_type="image/jpeg")
        except Exception:
            logger.exception("PI photo R2 put failed: idx=%d", idx)
            continue

        stored_url = r2_client.public_url(r2_key) or f"r2://{r2_key}"

        sia_comment = writer.generate_comment_for_photo(
            photo_url=stored_url,
            photo_context={
                "category": category,
                "rank": int(entry.get("rank_within_category") or 0),
                "rationale": entry.get("rationale"),
            },
            profile=profile,
        )

        insight = PhotoInsight(
            photo_id=photo_id,
            stored_url=stored_url,
            category=category,           # type: ignore[arg-type]
            sia_comment=sia_comment,
            rank=int(entry.get("rank_within_category") or 0),
            extracted_colors=None,
            associated_trend_id=entry.get("associated_trend_id"),
        )
        if category == "signature":
            publics.append(insight)
        else:
            lockeds.append(insight)

    publics.sort(key=lambda p: p.rank)
    lockeds.sort(key=lambda p: p.rank)
    return publics, lockeds


# ─────────────────────────────────────────────
#  boundary_message — 유동 카피 (Phase H 교체 대상)
# ─────────────────────────────────────────────

def _compose_boundary_message(
    *,
    profile: UserTasteProfile,
    feed_count: int,
    public_n: int,
    locked_n: int,
) -> str:
    """Stub — Phase H 완료 시 SiaWriter concrete 교체."""
    strength = profile.strength_score
    total_photos = public_n + locked_n
    if feed_count == 0:
        return (
            "피드를 아직 받지 못했어요. "
            "IG 연결 후 재생성하시면 더 풍부한 리포트가 가능해요."
        )
    if feed_count < 15:
        return (
            f"피드가 아직 소담해요 ({feed_count}장). 사진이 더 쌓이면 "
            f"재생성 시 카테고리가 더 풍부해져요. 현재 공개 {public_n}장 / "
            f"잠금 {locked_n}장 (데이터 풍부도 {strength:.0%})."
        )
    return (
        f"피드 {feed_count}장 중 추린 {total_photos}장이에요 "
        f"(공개 {public_n} / 잠금 {locked_n}). "
        f"데이터 풍부도 {strength:.0%}."
    )


def _stub_user_summary(
    profile: UserTasteProfile,
    phrases: list[str],
) -> str:
    """Phase H 전까지 간소 placeholder."""
    if phrases:
        head = phrases[0][:40]
        return f"정세현님은 '{head}' 쪽을 추구하시는 분입니다."
    return "정세현님의 방향을 정리하겠습니다."


def _stub_needs_statement(profile: UserTasteProfile) -> str:
    """Phase H 전까지 간소 placeholder."""
    return "그에 맞는 방향성이 필요합니다."


# ─────────────────────────────────────────────
#  DB persistence — versioning + is_current
# ─────────────────────────────────────────────

def _load_current_report(db, user_id: str) -> Optional[PIReport]:
    """현재 is_current=TRUE 인 리포트 조회. 없으면 None."""
    try:
        row = db.execute(
            text(
                "SELECT report_id, user_id, version, is_current, "
                "       unlocked_at, report_data, created_at "
                "FROM pi_reports "
                "WHERE user_id = :uid AND is_current = TRUE "
                "LIMIT 1"
            ),
            {"uid": user_id},
        ).first()
    except Exception:
        logger.debug("pi_reports read failed — migration pending?")
        return None
    if row is None or not row.report_data:
        return None
    try:
        return PIReport.model_validate(row.report_data)
    except Exception:
        logger.exception("legacy pi_reports row parse failed: user=%s", user_id)
        return None


def _archive_prior_current(db, user_id: str) -> None:
    """기존 is_current=TRUE 를 FALSE 로 (partial UNIQUE 때문에 신규 삽입 전)."""
    try:
        db.execute(
            text(
                "UPDATE pi_reports SET is_current = FALSE, updated_at = NOW() "
                "WHERE user_id = :uid AND is_current = TRUE"
            ),
            {"uid": user_id},
        )
    except Exception:
        logger.debug("archive_prior_current: pi_reports update failed")


def _next_version_for_user(db, user_id: str) -> int:
    try:
        v = db.execute(
            text(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM pi_reports "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).scalar()
        return int(v or 1)
    except Exception:
        return 1


def _persist_report(db, report: PIReport) -> None:
    """신 schema INSERT — report_data 에 전수 JSONB."""
    try:
        db.execute(
            text(
                "INSERT INTO pi_reports "
                "  (report_id, user_id, version, is_current, unlocked_at, "
                "   report_data, created_at, updated_at) "
                "VALUES (:rid, :uid, :ver, TRUE, :ua, CAST(:rd AS jsonb), "
                "        :ca, :ca)"
            ),
            {
                "rid": report.report_id,
                "uid": report.user_id,
                "ver": report.version,
                "ua": report.generated_at,
                "rd": json.dumps(report.model_dump(mode="json"), ensure_ascii=False, default=str),
                "ca": report.generated_at,
            },
        )
    except Exception:
        logger.exception(
            "PI report INSERT failed: user=%s version=%d", report.user_id, report.version,
        )
        raise PIEngineError("persist failed")


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _generate_report_id() -> str:
    return f"pi_{uuid.uuid4().hex[:24]}"


def _count_filled_fields(vault: UserDataVault) -> int:
    sf = vault.structured_fields or {}
    keys = (
        "desired_image", "reference_style", "current_concerns", "self_perception",
        "lifestyle_context", "height", "weight", "shoulder_width",
    )
    return sum(1 for k in keys if sf.get(k))


# ═══════════════════════════════════════════════════════════════════════════════
#  PI v1 — 정면 raw 1장 + vault 5/5 + 9 컴포넌트 3-3-3
# ═══════════════════════════════════════════════════════════════════════════════
#
# 사용자 spec (CLAUDE.md §3.2 + 본인 확정 2026-04-25):
#   - 정면 raw 1장 입력 (IG 피드 25장 모델은 deprecated, generate_pi_report 함수는 유지)
#   - vault 5/5 풀 활용 (verdict/best_shot/aspiration history 포함 — 강화 루프)
#   - 9 컴포넌트 3-3-3 (raw 3 + vault 3 + trend 3)
#   - preview 무료 (cover + celeb-reference) → 결제 50토큰 → 풀 9 컴포넌트
#   - 톤 = 리포트체 (~있어요/~세요) — Sia 친밀체와 분리, Verdict 정중체와도 분리
#
# 인스턴스 분해 (영역):
#   PI-A (본 함수): pi_engine.py 본문 + Sonnet/Haiku 통합 + DB save
#   PI-B (외부 inject): face_features / coord_3axis / matched_celebs / matched_types
#   PI-C (외부 inject): matched_trends / methodology_reasons + 9 컴포넌트 schema
#   PI-D (외부 호출): routes/pi.py + sia_validators_pi.py + alembic upgrade head


# ─────────────────────────────────────────────
#  Prompt loaders (lru_cache 1회)
# ─────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_sonnet_pi_system() -> str:
    return (
        Path(__file__).resolve().parent.parent
        / "prompts" / "sonnet_pi" / "system.md"
    ).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _load_haiku_pi_narrative_system() -> str:
    return (
        Path(__file__).resolve().parent.parent
        / "prompts" / "haiku_pi_narrative" / "base.md"
    ).read_text(encoding="utf-8")


# ─────────────────────────────────────────────
#  Vault history extraction (강화 루프)
# ─────────────────────────────────────────────

def _extract_verdict_history_top(vault: UserDataVault, n: int = 3) -> list[dict]:
    """vault.verdict_history 최신 N — Haiku payload 용 slim dict.

    Haiku prompt 의 [최근 Verdict v2 분석] 영역. 토큰 폭주 방지 위해 핵심만 추출.
    상품명 직접 노출 금지 — Haiku narrative 가 우회 표현 사용 (prompt 명시).
    """
    history = list(getattr(vault, "verdict_history", None) or [])
    if not history:
        return []
    out: list[dict] = []
    for entry in history[-n:]:
        if hasattr(entry, "model_dump"):
            d = entry.model_dump(mode="json")
        elif isinstance(entry, dict):
            d = entry
        else:
            continue
        best_fit = d.get("best_fit_coords") or (
            d.get("best_fit") or {}
        ).get("coords") if isinstance(d.get("best_fit"), dict) else d.get("best_fit_coords")
        out.append({
            "session_id": d.get("session_id") or d.get("verdict_id"),
            "best_fit_coords": best_fit,
            "style_direction": d.get("style_direction") or d.get("style_summary"),
            "top_photo_count": len(d.get("photo_insights") or []),
            "created_at": d.get("created_at"),
        })
    return out


def _extract_best_shot_history_top(vault: UserDataVault, n: int = 2) -> list[dict]:
    """vault.best_shot_history 최신 N — Haiku payload 용 slim."""
    history = list(getattr(vault, "best_shot_history", None) or [])
    if not history:
        return []
    out: list[dict] = []
    for entry in history[-n:]:
        if hasattr(entry, "model_dump"):
            d = entry.model_dump(mode="json")
        elif isinstance(entry, dict):
            d = entry
        else:
            continue
        out.append({
            "session_id": d.get("session_id"),
            "selected_count": len(d.get("selected_photos") or []),
            "uploaded_count": d.get("uploaded_count"),
            "overall_message": (d.get("overall_message") or "")[:200],
            "created_at": d.get("created_at"),
        })
    return out


def _extract_aspiration_history_top(vault: UserDataVault, n: int = 2) -> list[dict]:
    """vault.aspiration_history 최신 N — Haiku payload 용 slim."""
    history = list(getattr(vault, "aspiration_history", None) or [])
    if not history:
        return []
    out: list[dict] = []
    for entry in history[-n:]:
        if hasattr(entry, "model_dump"):
            d = entry.model_dump(mode="json")
        elif isinstance(entry, dict):
            d = entry
        else:
            continue
        narrative = d.get("narrative") if isinstance(d.get("narrative"), dict) else {}
        gap_vector = d.get("gap_vector") if isinstance(d.get("gap_vector"), dict) else {}
        out.append({
            "analysis_id": d.get("analysis_id"),
            "target_type": d.get("target_type"),
            "target_display_name": d.get("target_display_name") or d.get("target_identifier"),
            "primary_axis": gap_vector.get("primary_axis"),
            "gap_summary": (narrative.get("gap_summary") or "")[:120],
            "matched_trend_ids": d.get("matched_trend_ids") or [],
            "created_at": d.get("created_at"),
        })
    return out


# ─────────────────────────────────────────────
#  Sonnet PI — 정면 raw 분석 (face_structure + skin_analysis)
# ─────────────────────────────────────────────

def _sonnet_pi_face_analysis(
    *,
    baseline_photo_r2_key: str,
    face_features: dict,
    matched_types: list[dict],
    matched_celebs: list[dict],
    gender: str,
) -> dict:
    """Sonnet Vision — 정면 raw + face_features → face_structure + skin_analysis JSON.

    raw text 는 dict 안 "_raw" 키로 보존 (caller R2 영구 저장).
    JSON 파싱 실패 시 PIEngineError raise — Haiku narrative 단계에서 fallback 처리 가능.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise PIEngineError("ANTHROPIC_API_KEY not configured")

    # R2 raw 다운로드 + base64
    try:
        photo_bytes = r2_client.get_bytes(baseline_photo_r2_key)
    except Exception as e:
        raise PIEngineError(f"baseline photo fetch failed: {e}")

    if not photo_bytes:
        raise PIEngineError("baseline photo is empty")

    # Anthropic API 5MB base64 제한 — verdict_v2.downscale_image 재활용
    # (긴 변 1568px LANCZOS + JPEG q=85, EXIF orientation, RGB 변환).
    # R2 원본은 raw 영구 보존됨 — 본 다운스케일은 LLM 호출 시점 메모리만.
    from services.verdict_v2 import downscale_image
    downscaled_bytes, content_type = downscale_image(photo_bytes)
    b64 = base64.b64encode(downscaled_bytes).decode("ascii")
    image_block = {
        "type": "image",
        "source": {"type": "base64", "media_type": content_type, "data": b64},
    }

    text_payload = (
        f"face_features:\n{json.dumps(face_features, ensure_ascii=False, indent=2)}\n\n"
        f"matched_types (CLIP top-3):\n{json.dumps(matched_types[:3], ensure_ascii=False, indent=2)}\n\n"
        f"matched_celebs (CLIP top-3):\n{json.dumps(matched_celebs[:3], ensure_ascii=False, indent=2)}\n\n"
        f"gender: {gender}\n\n"
        "위 정면 raw 사진과 face_features, matched 정보로 face_structure 와 skin_analysis 를 객관 분석합니다. "
        "리포트체 어미 (~있어요/~세요) 만 사용. JSON 1개만 출력. 마크다운 wrapper 금지."
    )

    user_content = [image_block, {"type": "text", "text": text_payload}]

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=settings.anthropic_model_sonnet,
        max_tokens=3500,
        system=_load_sonnet_pi_system(),
        messages=[{"role": "user", "content": user_content}],
    )
    if not response.content:
        raise PIEngineError("Sonnet PI empty response")

    text_blocks = [b.text for b in response.content if b.type == "text"]
    raw = "\n".join(text_blocks).strip()
    raw = _strip_fence(raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.exception("Sonnet PI JSON parse failed")
        raise PIEngineError(f"Sonnet PI JSON invalid: {e}")

    if not isinstance(parsed, dict):
        raise PIEngineError("Sonnet PI response not dict")

    parsed["_raw"] = raw   # caller R2 영구 저장
    return parsed


# ─────────────────────────────────────────────
#  Haiku PI narrative — 4 컴포넌트 (cover/type_ref/gap/action)
# ─────────────────────────────────────────────

def _haiku_pi_narrative(
    *,
    user_name: Optional[str],
    profile: UserTasteProfile,
    coord_3axis: VisualCoordinate,
    face_structure: dict,
    skin_analysis: dict,
    matched_types: list[dict],
    matched_celebs: list[dict],
    matched_trends: list[dict],
    methodology_reasons: list[dict],
    verdict_history: list[dict],
    best_shot_history: list[dict],
    aspiration_history: list[dict],
) -> dict:
    """Haiku — vault + matched + history → 4 컴포넌트 narrative JSON.

    raw text 는 "_raw" 키로 보존 (caller R2 저장).
    API 실패 / JSON 파싱 실패 시 deterministic fallback dict 반환 (caller 무영향).
    """
    settings = get_settings()

    honor = (user_name or "").strip()
    if honor and not honor.endswith("님"):
        honor = f"{honor}님"

    aspiration = profile.aspiration_vector
    aspiration_dump = aspiration.model_dump(mode="json") if aspiration else None

    payload_lines: list[str] = []
    payload_lines.append(f"[유저 호명] {honor or '(이름 미지정 — 호명 생략)'}")
    payload_lines.append(
        f"[현재 좌표] shape={coord_3axis.shape:.2f} "
        f"volume={coord_3axis.volume:.2f} age={coord_3axis.age:.2f}"
    )
    if aspiration_dump:
        payload_lines.append(
            f"[추구미 좌표] {json.dumps(aspiration_dump, ensure_ascii=False)}"
        )
    if matched_types:
        payload_lines.append(
            f"[매칭 유형 top-3]\n{json.dumps(matched_types[:3], ensure_ascii=False, indent=2)}"
        )
    if matched_celebs:
        payload_lines.append(
            f"[유사 셀럽 top-3]\n{json.dumps(matched_celebs[:3], ensure_ascii=False, indent=2)}"
        )
    payload_lines.append(
        f"[얼굴형] {face_structure.get('face_type', '(미분류)')} / "
        f"harmony: {face_structure.get('harmony_note', '')}"
    )
    payload_lines.append(
        f"[피부 톤] {skin_analysis.get('tone', '(미분류)')} / "
        f"{skin_analysis.get('tone_description', '')}"
    )
    if methodology_reasons:
        payload_lines.append(
            "[methodology_reasons]\n"
            + json.dumps(methodology_reasons[:8], ensure_ascii=False, indent=2)
        )
    if matched_trends:
        payload_lines.append(
            "[matched_trends + 출처]\n"
            + json.dumps(matched_trends[:5], ensure_ascii=False, indent=2)
        )

    user_phrases = profile.user_original_phrases or []
    if user_phrases:
        payload_lines.append(
            f"[vault user_phrases] {json.dumps(user_phrases[:6], ensure_ascii=False)}"
        )

    payload_lines.append(f"[strength_score] {profile.strength_score:.2f}")

    signals = getattr(profile, "conversation_signals", None)
    if signals is not None:
        try:
            signals_dump = (
                signals.model_dump(mode="json") if hasattr(signals, "model_dump")
                else dict(signals)
            )
            payload_lines.append(
                f"[conversation_signals]\n"
                + json.dumps(signals_dump, ensure_ascii=False, indent=2)
            )
        except Exception:
            pass

    # 강화 루프 — 다른 기능 history 3 영역 (직접 호명 X, 우회 표현 사용)
    if verdict_history:
        payload_lines.append(
            "[최근 Verdict v2 분석] (상품명 직접 호명 X — '지난번' / '이미 보셨던' 우회)\n"
            + json.dumps(verdict_history, ensure_ascii=False, indent=2)
        )
    if best_shot_history:
        payload_lines.append(
            "[최근 Best Shot 결과] (상품명 직접 호명 X — '이미 고르셨던' 우회)\n"
            + json.dumps(best_shot_history, ensure_ascii=False, indent=2)
        )
    if aspiration_history:
        payload_lines.append(
            "[최근 Aspiration 분석] (상품명 직접 호명 X — '지난번 추구미 비교' 우회)\n"
            + json.dumps(aspiration_history, ensure_ascii=False, indent=2)
        )

    payload_lines.append(
        "\n위 데이터로 cover / type_reference / gap_analysis / action_plan "
        "4 컴포넌트 narrative 를 JSON 으로 출력합니다. "
        "리포트체 (~있어요/~세요) 사용. 출처는 자연스럽게 호출."
    )

    user_prompt = "\n\n".join(payload_lines)

    fallback = _build_pi_narrative_fallback(
        honor=honor,
        coord_3axis=coord_3axis,
        face_type=face_structure.get("face_type", ""),
        matched_types=matched_types,
    )
    fallback_text = json.dumps(fallback, ensure_ascii=False)

    if not settings.anthropic_api_key:
        return {**fallback, "_raw": fallback_text}

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model_haiku,
            max_tokens=2200,
            system=_load_haiku_pi_narrative_system(),
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception:
        logger.exception("Haiku PI API failed — fallback")
        return {**fallback, "_raw": fallback_text}

    if not response.content:
        return {**fallback, "_raw": fallback_text}

    text_blocks = [b.text for b in response.content if b.type == "text"]
    raw = "\n".join(text_blocks).strip()
    raw = _strip_fence(raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Haiku PI JSON parse failed — fallback. raw=%r", raw[:200])
        return {**fallback, "_raw": raw}

    if not isinstance(parsed, dict):
        return {**fallback, "_raw": raw}

    # 정합 검증 — 4 컴포넌트 키 부재 시 fallback 으로 보강
    for required_key in ("cover", "type_reference", "gap_analysis", "action_plan"):
        if required_key not in parsed or not isinstance(parsed[required_key], dict):
            parsed[required_key] = fallback.get(required_key, {})

    parsed["_raw"] = raw
    return parsed


def _build_pi_narrative_fallback(
    *,
    honor: str,
    coord_3axis: VisualCoordinate,
    face_type: str,
    matched_types: list[dict],
) -> dict:
    """Haiku 실패 시 deterministic fallback — 페르소나 톤 + A-17/A-20 안전.

    리포트체 어미 사용. 출처/methodology echo 없이 좌표 + 매칭 유형만으로 안전한 4 컴포넌트.
    """
    matched_label = (
        matched_types[0].get("name_kr")
        if matched_types and isinstance(matched_types[0], dict) else None
    ) or "(매칭 유형 미정)"
    matched_one_liner = ""
    if matched_types and isinstance(matched_types[0], dict):
        matched_one_liner = (
            matched_types[0].get("description")
            or matched_types[0].get("one_liner")
            or ""
        )
    if not matched_one_liner:
        matched_one_liner = "(설명 미정)"

    coord_summary = (
        f"shape {coord_3axis.shape:.2f} / volume {coord_3axis.volume:.2f} / "
        f"age {coord_3axis.age:.2f}"
    )
    honor_part = f"{honor} " if honor else ""

    return {
        "cover": {
            "headline": "현재 결을 정리해드려요",
            "subhead": f"좌표 {coord_summary}",
            "body": (
                f"{honor_part}정면 분석 결과 좌표 {coord_summary} 위치예요. "
                "매칭된 유형 결과와 함께 정리해드려요. "
                "조금 더 쓰시면 더 또렷해져요."
            ).strip(),
        },
        "type_reference": {
            "matched_label": matched_label,
            "matched_one_liner": matched_one_liner,
            "match_reason": "좌표 매칭으로 가장 가까운 유형이에요.",
            "secondary": [],
        },
        "gap_analysis": {
            "primary_axis": "shape",
            "primary_direction": "현 위치 유지",
            "primary_narrative": "추구미 좌표 정보가 충분해지면 더 또렷해져요.",
            "secondary_axis": "",
            "secondary_narrative": "",
            "tertiary_narrative": "",
        },
        "action_plan": {
            "primary_action": "현 결 유지",
            "primary_why": "데이터가 더 쌓이면 구체 가이드로 정교해져요.",
            "primary_how": "본인 피드를 한두 번 더 쓰시면 정확도가 올라가요.",
            "secondary_actions": [],
            "expected_effects": [],
            "trend_sources": [],
        },
    }


# ─────────────────────────────────────────────
#  raw 영구 보존 (R2)
# ─────────────────────────────────────────────

def _persist_pi_raw(
    *,
    user_id: str,
    report_id: str,
    version: int,
    kind: str,                # "sonnet" | "haiku"
    raw_text: str,
) -> Optional[str]:
    """LLM raw 응답 R2 영구 저장. 실패는 흡수 (메인 플로우 무영향).

    LLM 격리 (history_injector 와 동일 정책) — DB / prompt 에 raw 노출 X.
    R2 만 보존, 메타분석 시 fetch.
    """
    if not raw_text:
        return None
    key = r2_client.user_photo_key(
        user_id, f"pi_reports/{report_id}/v{version}/{kind}_raw.json",
    )
    payload = json.dumps(
        {"raw": raw_text, "kind": kind, "report_id": report_id, "version": version},
        ensure_ascii=False,
    )
    try:
        r2_client.put_bytes(
            key, payload.encode("utf-8"), content_type="application/json",
        )
    except Exception:
        logger.exception("PI %s raw R2 put failed", kind)
        return None
    return key


# ─────────────────────────────────────────────
#  9 컴포넌트 조립 (3-3-3)
# ─────────────────────────────────────────────

def _assemble_9_components(
    *,
    sonnet_face_structure: dict,
    sonnet_skin_analysis: dict,
    haiku_cover: dict,
    haiku_type_reference: dict,
    haiku_gap_analysis: dict,
    haiku_action_plan: dict,
    coord_3axis: VisualCoordinate,
    matched_celebs: list[dict],
    matched_types: list[dict],
    matched_trends: list[dict],
    aspiration_vector: Optional[dict] = None,
) -> dict:
    """9 컴포넌트 3-3-3 dict 조립.

    raw 강 (3): coordinate_map / face_structure / celeb_reference
    vault 강 (3): cover / type_reference / gap_analysis
    trend 강 (3): skin_analysis / hair_recommendation / action_plan

    각 컴포넌트 = {weight, mode, content}
      weight: "raw" | "vault" | "trend"
      mode:   "preview" | "teaser" | "lock"
        preview: 결제 전 풀 노출 (cover / celeb_reference)
        teaser:  결제 전 첫 줄 + blur (face_structure / type_reference / gap_analysis / skin_analysis)
        lock:    결제 후만 노출 (coordinate_map / hair_recommendation / action_plan)
    """
    components = {
        # ── raw 강 (3) ─────────────────────────
        "coordinate_map": {
            "weight": "raw",
            "mode": "lock",
            "content": {
                "current_coords": {
                    "shape": coord_3axis.shape,
                    "volume": coord_3axis.volume,
                    "age": coord_3axis.age,
                },
                "aspiration_coords": aspiration_vector,
                "trend_overlay": [
                    {
                        "trend_id": t.get("trend_id"),
                        "title": t.get("title"),
                        "compatible_coordinates": t.get("compatible_coordinates"),
                    }
                    for t in (matched_trends or [])[:5]
                    if isinstance(t, dict) and t.get("compatible_coordinates")
                ],
            },
        },
        "face_structure": {
            "weight": "raw",
            "mode": "teaser",
            "content": sonnet_face_structure,
        },
        "celeb_reference": {
            "weight": "raw",
            "mode": "preview",
            "content": {
                "matched_celebs": matched_celebs[:3],
            },
        },
        # ── vault 강 (3) ────────────────────────
        "cover": {
            "weight": "vault",
            "mode": "preview",
            "content": haiku_cover,
        },
        "type_reference": {
            "weight": "vault",
            "mode": "teaser",
            "content": haiku_type_reference,
        },
        "gap_analysis": {
            "weight": "vault",
            "mode": "teaser",
            "content": haiku_gap_analysis,
        },
        # ── trend 강 (3) ────────────────────────
        "skin_analysis": {
            "weight": "trend",
            "mode": "teaser",
            "content": sonnet_skin_analysis,
        },
        "hair_recommendation": {
            "weight": "trend",
            "mode": "lock",
            "content": _hair_recommendation_from_action(
                haiku_action_plan, matched_trends,
            ),
        },
        "action_plan": {
            "weight": "trend",
            "mode": "lock",
            "content": haiku_action_plan,
        },
    }
    return components


def _hair_recommendation_from_action(
    haiku_action_plan: dict,
    matched_trends: list[dict],
) -> dict:
    """action_plan 의 hair 영역 + matched_trends 의 styling_method 카테고리 결합.

    PI-C 가 별도 hair_recommendation schema 정의 시 이 함수 deprecated.
    """
    primary_action = haiku_action_plan.get("primary_action", "")
    primary_why = haiku_action_plan.get("primary_why", "")
    primary_how = haiku_action_plan.get("primary_how", "")

    styling_trends = [
        t for t in (matched_trends or [])
        if isinstance(t, dict) and t.get("category") == "styling_method"
    ][:3]

    return {
        "primary_action": primary_action,
        "primary_why": primary_why,
        "primary_how": primary_how,
        "styling_trends": [
            {
                "trend_id": t.get("trend_id"),
                "title": t.get("title"),
                "score_label": t.get("score_label"),
                "source": t.get("source"),
                "action_hints": (t.get("action_hints") or [])[:3],
            }
            for t in styling_trends
        ],
    }


# ─────────────────────────────────────────────
#  boundary_message (PI v1)
# ─────────────────────────────────────────────

def _compose_pi_v1_boundary(profile: UserTasteProfile, version: int) -> str:
    """PI v1 — 9 컴포넌트 mode 분기 안내. 리포트체."""
    strength = profile.strength_score
    if version == 1:
        return (
            "첫 PI 리포트예요. 미리보기 영역 두 컴포넌트는 무료로 보세요. "
            f"나머지 일곱 컴포넌트는 결제 후 풀 노출이에요. "
            f"(데이터 풍부도 {strength:.0%})"
        )
    return (
        f"버전 {version} 재생성 결과예요. "
        f"이전 버전 대비 데이터 풍부도가 {strength:.0%} 가 됐어요. "
        "갱신된 좌표 기준으로 재해석한 결과예요."
    )


# ─────────────────────────────────────────────
#  DB persist v1 (확장 — JSONB 에 components + raw_keys)
# ─────────────────────────────────────────────

def _persist_report_v1(
    db,
    report: PIReport,
    *,
    components: dict,
    raw_keys: dict,
) -> None:
    """pi_reports INSERT — report_data JSONB 에 components + r2_raw_keys 합쳐서 저장.

    PI-D alembic versioned schema (20260501_pi_reports_versioned) 적용 후 동작.
    raw text 는 R2 만 보관 (LLM 격리). DB JSONB 에는 r2 key 만 저장.
    """
    full_data = report.model_dump(mode="json")
    full_data["components"] = components
    full_data["r2_raw_keys"] = raw_keys
    full_data["pi_v1_spec"] = True   # 신/구 함수 구분 플래그

    try:
        db.execute(
            text(
                "INSERT INTO pi_reports "
                "  (report_id, user_id, version, is_current, unlocked_at, "
                "   report_data, created_at, updated_at) "
                "VALUES (:rid, :uid, :ver, TRUE, :ua, CAST(:rd AS jsonb), "
                "        :ca, :ca)"
            ),
            {
                "rid": report.report_id,
                "uid": report.user_id,
                "ver": report.version,
                "ua": report.generated_at,
                "rd": json.dumps(
                    full_data, ensure_ascii=False, default=str,
                ),
                "ca": report.generated_at,
            },
        )
    except Exception:
        logger.exception(
            "PI v1 report INSERT failed: user=%s version=%d",
            report.user_id, report.version,
        )
        raise PIEngineError("persist v1 failed")


# ─────────────────────────────────────────────
#  user_history.pi_history append (강화 루프 trajectory)
# ─────────────────────────────────────────────
#
# PI-B 정합 (schemas/user_history.py:118-141 PiHistoryEntry):
#   report_id / version / created_at / matched_type / cluster_label /
#   coord_3axis / top_celeb_name / top_celeb_similarity /
#   top_hair_name / top_action_text
#
# 호출 시그니처: services.user_history.append_history(
#     db, user_id=..., category="pi_history", entry=PiHistoryEntry(...)
# )
# trajectory_events 자동 누적 (services/user_history.py:103-111).


@lru_cache(maxsize=1)
def _load_cluster_labels_index() -> dict:
    """data/cluster_labels.json — type_id → cluster label_kr 역인덱스 cache.

    matched_types[0].type_id 로 클러스터 라벨 추출 (PiHistoryEntry.cluster_label 채움).
    파일 부재 / 파싱 실패 시 빈 dict — append 흐름 무영향.
    """
    path = (
        Path(__file__).resolve().parent.parent / "data" / "cluster_labels.json"
    )
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        logger.exception("cluster_labels.json load failed")
        return {}

    type_to_label: dict[str, str] = {}
    clusters = data.get("clusters") if isinstance(data, dict) else None
    if isinstance(clusters, list):
        for cluster in clusters:
            if not isinstance(cluster, dict):
                continue
            label_kr = cluster.get("label_kr") or cluster.get("id")
            members = cluster.get("members") or []
            if not (isinstance(label_kr, str) and isinstance(members, list)):
                continue
            for member in members:
                if isinstance(member, str):
                    type_to_label[member] = label_kr
    return type_to_label


def _resolve_cluster_label(type_id: Optional[str]) -> Optional[str]:
    """matched_types[0].type_id → cluster_labels.json 의 label_kr ('쿨 갓데스' 등)."""
    if not type_id:
        return None
    return _load_cluster_labels_index().get(type_id)


def _append_pi_history_v1(
    db,
    *,
    user_id: str,
    report: PIReport,
    components: dict,
    matched_celebs: list[dict],
    matched_types: list[dict],
) -> None:
    """user_history.pi_history append (PiHistoryEntry 시그니처 정합).

    schemas.user_history.PiHistoryEntry 10 필드 매핑:
      report_id          ← report.report_id
      version            ← report.version
      created_at         ← report.generated_at
      matched_type       ← components.type_reference.matched_label
      cluster_label      ← _resolve_cluster_label(matched_types[0].type_id)
      coord_3axis        ← components.coordinate_map.current_coords
      top_celeb_name     ← matched_celebs[0].celeb_name
      top_celeb_similarity ← matched_celebs[0].similarity
      top_hair_name      ← components.hair_recommendation.styling_trends[0].title
                           (없으면 components.hair_recommendation.primary_action)
      top_action_text    ← components.action_plan.primary_action

    trajectory_events 자동 누적 (services/user_history.py 의 _build_trajectory_event
    가 entry.coord_3axis 추출). raw text 노출 X — LLM 격리 방어.
    BackgroundTask wrap 권장 (PI-D routes 영역). PI-A 는 직접 호출.
    """
    try:
        from services.user_history import append_history
        from schemas.user_history import PiHistoryEntry
    except Exception:
        logger.warning(
            "user_history / PiHistoryEntry unavailable — skip pi_history append"
        )
        return

    type_ref_content = (
        components.get("type_reference", {}).get("content", {}) or {}
    )
    coord_content = (
        components.get("coordinate_map", {}).get("content", {}) or {}
    )
    action_content = (
        components.get("action_plan", {}).get("content", {}) or {}
    )
    hair_content = (
        components.get("hair_recommendation", {}).get("content", {}) or {}
    )

    # matched_type — type_reference.matched_label
    matched_type_label = type_ref_content.get("matched_label") or None

    # cluster_label — matched_types[0].type_id → cluster_labels.json 매핑
    top_type_id: Optional[str] = None
    if matched_types and isinstance(matched_types[0], dict):
        tid = matched_types[0].get("type_id")
        if isinstance(tid, str):
            top_type_id = tid
    cluster_label_kr = _resolve_cluster_label(top_type_id)

    # coord_3axis — current_coords {shape, volume, age}
    raw_coords = coord_content.get("current_coords")
    coord_3axis: Optional[dict[str, float]] = None
    if isinstance(raw_coords, dict):
        try:
            coord_3axis = {
                "shape": float(raw_coords.get("shape", 0.5)),
                "volume": float(raw_coords.get("volume", 0.5)),
                "age": float(raw_coords.get("age", 0.5)),
            }
        except (TypeError, ValueError):
            coord_3axis = None

    # top_celeb — matched_celebs[0]
    top_celeb_name: Optional[str] = None
    top_celeb_similarity: Optional[float] = None
    if matched_celebs and isinstance(matched_celebs[0], dict):
        cname = matched_celebs[0].get("celeb_name")
        if isinstance(cname, str) and cname.strip():
            top_celeb_name = cname.strip()
        sim = matched_celebs[0].get("similarity")
        if isinstance(sim, (int, float)):
            top_celeb_similarity = float(sim)

    # top_hair — hair_recommendation.styling_trends[0].title 또는 primary_action
    top_hair_name: Optional[str] = None
    styling_trends = hair_content.get("styling_trends") or []
    if isinstance(styling_trends, list) and styling_trends:
        first = styling_trends[0]
        if isinstance(first, dict):
            title = first.get("title")
            if isinstance(title, str) and title.strip():
                top_hair_name = title.strip()
    if not top_hair_name:
        primary_action_hair = hair_content.get("primary_action")
        if isinstance(primary_action_hair, str) and primary_action_hair.strip():
            top_hair_name = primary_action_hair.strip()

    # top_action — action_plan.primary_action
    top_action_text: Optional[str] = None
    primary_action = action_content.get("primary_action")
    if isinstance(primary_action, str) and primary_action.strip():
        top_action_text = primary_action.strip()

    try:
        entry = PiHistoryEntry(
            report_id=report.report_id,
            version=report.version,
            created_at=report.generated_at,
            matched_type=matched_type_label,
            cluster_label=cluster_label_kr,
            coord_3axis=coord_3axis,
            top_celeb_name=top_celeb_name,
            top_celeb_similarity=top_celeb_similarity,
            top_hair_name=top_hair_name,
            top_action_text=top_action_text,
        )
    except Exception:
        logger.exception(
            "PiHistoryEntry construct failed: user=%s report=%s",
            user_id, report.report_id,
        )
        return

    try:
        ok = append_history(
            db, user_id=user_id, category="pi_history", entry=entry,
        )
        if not ok:
            logger.warning(
                "pi_history append returned False user=%s report=%s",
                user_id, report.report_id,
            )
    except Exception:
        logger.exception("pi_history append failed: user=%s", user_id)


# ─────────────────────────────────────────────
#  ★ PI v1 main entry ★
# ─────────────────────────────────────────────

def generate_pi_report_v1(
    db,
    *,
    user_id: str,
    baseline_photo_r2_key: str,
    # PI-B inject (anchor matching + face features + 좌표)
    face_features: dict,
    coord_3axis: VisualCoordinate,
    matched_celebs: list[dict],
    matched_types: list[dict],
    # PI-C inject (KB 매칭 + methodology)
    matched_trends: list[dict],
    methodology_reasons: list[dict],
    force_new_version: bool = False,
) -> PIReport:
    """PI v1 — 정면 raw 1장 + vault 5/5 + 9 컴포넌트 3-3-3.

    Args:
      db: SQLAlchemy session (caller commit)
      user_id: 대상 유저
      baseline_photo_r2_key: 정면 raw R2 key (PI-D 가 routes 에서 업로드 후 전달)
      face_features: MediaPipe 17 메트릭 (PI-B inject)
      coord_3axis: 3축 좌표 0-1 외부 스케일 (PI-B inject, P0 해결 후 실 768d projector)
      matched_celebs: CLIP top-3 셀럽 (PI-B inject)
      matched_types: CLIP top-3 type (PI-B inject)
      matched_trends: KB 매칭 결과 (PI-C inject)
      methodology_reasons: hair_rules + action_spec reason list (PI-C inject)
      force_new_version: True 면 is_current 아카이브 후 신 version 생성

    Returns:
      PIReport — JSONB report_data 안에 9 컴포넌트 dict + r2_raw_keys 포함

    Raises:
      PIEngineError — vault 없음 / Sonnet 실 실패 / DB 저장 실패
    """
    if db is None:
        raise PIEngineError("db unavailable")

    # 0. PI-B/PI-C inject 데이터 sanitize — 얼굴 미감지/매칭 실패 graceful degradation.
    # PI-A inject 인터페이스 spec 은 non-Optional 이지만 PI-B 가 face 분석 실패 시
    # None 반환 가능. 운영 unblock + 빈 데이터로 fallback narrative 생성.
    if coord_3axis is None:
        from services.coordinate_system import neutral_coordinate
        coord_3axis = neutral_coordinate()
        logger.warning(
            "PI-B coord_3axis is None — neutral fallback (user=%s, face 미감지 의심)",
            user_id,
        )
    if face_features is None:
        face_features = {}
    if matched_celebs is None:
        matched_celebs = []
    if matched_types is None:
        matched_types = []
    if matched_trends is None:
        matched_trends = []
    if methodology_reasons is None:
        methodology_reasons = []

    # 0-b. 기존 is_current 확인 (force 아닌 경우)
    if not force_new_version:
        existing = _load_current_report(db, user_id)
        if existing is not None:
            return existing

    # 1. Vault load + profile + history (강화 루프)
    vault = load_vault(db, user_id)
    if vault is None:
        raise PIEngineError(f"vault not found for user={user_id}")
    profile = vault.get_user_taste_profile()

    user_name = getattr(vault.basic_info, "name", None)
    raw_gender = getattr(vault.basic_info, "gender", None)
    gender = raw_gender if raw_gender in ("female", "male") else "female"

    verdict_history = _extract_verdict_history_top(vault, n=3)
    best_shot_history = _extract_best_shot_history_top(vault, n=2)
    aspiration_history = _extract_aspiration_history_top(vault, n=2)

    aspiration_vector_dump = (
        profile.aspiration_vector.model_dump(mode="json")
        if profile.aspiration_vector else None
    )

    # 2. 신 version + report_id 발급 + 기존 is_current 아카이브
    new_version = _next_version_for_user(db, user_id)
    _archive_prior_current(db, user_id)
    report_id = _generate_report_id()

    # 3. Sonnet Vision — face_structure + skin_analysis (객관)
    sonnet_result = _sonnet_pi_face_analysis(
        baseline_photo_r2_key=baseline_photo_r2_key,
        face_features=face_features,
        matched_types=matched_types,
        matched_celebs=matched_celebs,
        gender=gender,
    )
    sonnet_raw_text = sonnet_result.pop("_raw", "")
    sonnet_raw_key = _persist_pi_raw(
        user_id=user_id,
        report_id=report_id,
        version=new_version,
        kind="sonnet",
        raw_text=sonnet_raw_text,
    )
    sonnet_face_structure = sonnet_result.get("face_structure") or {}
    sonnet_skin_analysis = sonnet_result.get("skin_analysis") or {}

    # 4. Haiku narrative — cover/type_ref/gap/action (자연어 4)
    haiku_result = _haiku_pi_narrative(
        user_name=user_name,
        profile=profile,
        coord_3axis=coord_3axis,
        face_structure=sonnet_face_structure,
        skin_analysis=sonnet_skin_analysis,
        matched_types=matched_types,
        matched_celebs=matched_celebs,
        matched_trends=matched_trends,
        methodology_reasons=methodology_reasons,
        verdict_history=verdict_history,
        best_shot_history=best_shot_history,
        aspiration_history=aspiration_history,
    )
    haiku_raw_text = haiku_result.pop("_raw", "")
    haiku_raw_key = _persist_pi_raw(
        user_id=user_id,
        report_id=report_id,
        version=new_version,
        kind="haiku",
        raw_text=haiku_raw_text,
    )

    haiku_cover = haiku_result.get("cover") or {}
    haiku_type_reference = haiku_result.get("type_reference") or {}
    haiku_gap_analysis = haiku_result.get("gap_analysis") or {}
    haiku_action_plan = haiku_result.get("action_plan") or {}

    # 5. 9 컴포넌트 조립 (PI-C 9 컴포넌트 schema 정합)
    components = _assemble_9_components(
        sonnet_face_structure=sonnet_face_structure,
        sonnet_skin_analysis=sonnet_skin_analysis,
        haiku_cover=haiku_cover,
        haiku_type_reference=haiku_type_reference,
        haiku_gap_analysis=haiku_gap_analysis,
        haiku_action_plan=haiku_action_plan,
        coord_3axis=coord_3axis,
        matched_celebs=matched_celebs,
        matched_types=matched_types,
        matched_trends=matched_trends,
        aspiration_vector=aspiration_vector_dump,
    )

    # 6. PI 전용 validator (PI-D 영역 — 호출 가정만)
    try:
        from services.sia_validators_pi import (   # type: ignore
            validate_pi_content,
        )
        validate_pi_content(components)
    except ImportError:
        logger.debug(
            "sia_validators_pi not yet available — skip validation (PI-D pending)"
        )
    except Exception as e:
        logger.warning(
            "PI validator hard-reject — fallback narrative used: %s", e,
        )

    # 7. SiaWriter PI 전용 overall message
    writer = get_sia_writer()
    try:
        sia_overall = writer.generate_pi_overall(   # type: ignore[attr-defined]
            profile=profile,
            components=components,
            user_name=user_name,
        )
    except AttributeError:
        # generate_pi_overall 미구현 — generate_overall_message 폴백
        sia_overall = writer.generate_overall_message(
            profile=profile,
            context={"product": "pi", "version": new_version},
            user_name=user_name,
        )

    # 8. PIReport 조립
    user_phrases = profile.user_original_phrases or []
    sources = PIReportSources(
        feed_photo_count=0,                  # v1 = IG 25장 모델 미사용
        ig_analysis_present=False,
        conversation_field_count=_count_filled_fields(vault),
        user_original_phrases_count=len(user_phrases),
        aspiration_history_count=getattr(
            vault, "aspiration_count", len(aspiration_history),
        ),
        best_shot_history_count=getattr(
            vault, "best_shot_count", len(best_shot_history),
        ),
        vault_strength_score=profile.strength_score,
        selected_from_count=1,               # 정면 raw 1장
        public_count=2,                      # cover + celeb_reference (preview 무료)
        locked_count=7,                      # 나머지 7
    )

    now = datetime.now(timezone.utc)
    report = PIReport(
        report_id=report_id,
        user_id=user_id,
        version=new_version,
        is_current=True,
        generated_at=now,
        public_photos=[],                    # v1 = 컴포넌트 dict 사용 (사진 list 미사용)
        locked_photos=[],
        user_taste_profile_snapshot=profile.model_dump(mode="json"),
        user_summary=haiku_cover.get("headline", ""),
        needs_statement=haiku_gap_analysis.get("primary_direction", ""),
        user_original_phrases=user_phrases,
        sia_overall_message=sia_overall,
        boundary_message=_compose_pi_v1_boundary(profile, version=new_version),
        matched_trend_ids=[
            t.get("trend_id") for t in matched_trends
            if isinstance(t, dict) and t.get("trend_id")
        ],
        matched_methodology_ids=[
            m.get("rule_id") for m in methodology_reasons
            if isinstance(m, dict) and m.get("rule_id")
        ],
        matched_reference_ids=[
            c.get("celeb_name") for c in matched_celebs
            if isinstance(c, dict) and c.get("celeb_name")
        ],
        data_sources_used=sources,
    )

    # 9. DB persist (v1 확장 — JSONB 에 components + raw_keys)
    raw_keys = {"sonnet": sonnet_raw_key, "haiku": haiku_raw_key}
    _persist_report_v1(db, report, components=components, raw_keys=raw_keys)

    # 10. user_history.pi_history append + trajectory_events 자동 누적
    # PI-B 정합 — PiHistoryEntry 시그니처 (matched_celebs/types 추가 inject)
    _append_pi_history_v1(
        db,
        user_id=user_id,
        report=report,
        components=components,
        matched_celebs=matched_celebs,
        matched_types=matched_types,
    )

    return report
