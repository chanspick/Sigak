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
