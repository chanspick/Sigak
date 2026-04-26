"""Aspiration 공통 헬퍼 — IG/Pinterest 경로 공유 (Phase J2).

책임 분리:
  aspiration_common (본 모듈):
    - coordinate 도출 (IgFeedAnalysis → VisualCoordinate)
    - gap vector 산출
    - photo pair 선택 (본인 10장 ↔ 대상 10장에서 3-5쌍)
    - blocklist DB 조회 + 저장
    - persist_analysis (aspiration_analyses INSERT)

  aspiration_engine_ig / aspiration_engine_pinterest:
    - Apify 호출 + AspirationAnalysis 조립 (common 을 consume)
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from schemas.aspiration import (
    AspirationAnalysis,
    BlocklistEntry,
    PhotoPair,
    TargetType,
)
from schemas.user_profile import IgFeedAnalysis, IgLatestPost
from services.coordinate_system import (
    GapVector,
    VisualCoordinate,
    neutral_coordinate,
)


# 축별 소비자 ux 라벨 — pair_axis_hint 등 사용자 노출 영역.
# 내부 용어 ("형태/부피/인상") 노출 차단. 결과/체감 중심.
_PAIR_HINT_BY_AXIS: dict[str, str] = {
    "shape": "윤곽의 결",
    "volume": "입체감의 결",
    "age": "분위기의 결",
}
from services.knowledge_base import load_trends
from services.knowledge_matcher import match_trends_for_user
from services.sia_writer import _render_taste_profile_slim, get_sia_writer
from schemas.user_taste import UserTasteProfile


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Coordinate derivation
# ─────────────────────────────────────────────

# tone_category → (shape delta, age delta) 대략 매핑.
# CLAUDE.md 확정에 따른 heuristic — 이후 Phase H에서 Haiku 재산출로 교체 가능.
_TONE_HEURISTICS: dict[str, tuple[float, float]] = {
    # (shape delta, age delta). volume 은 pose_frequency 에서 별도 산출.
    "쿨뮤트":  (+0.10, +0.05),   # 차분/정돈 → 살짝 샤프, 살짝 성숙
    "웜뮤트":  (-0.10, +0.05),   # 부드럽/따뜻 → 소프트, 살짝 성숙
    "쿨비비드": (+0.20, -0.05),   # 샤프 강조, 프레시
    "웜비비드": (-0.05, -0.15),   # 프레시 + 살짝 소프트
    "중성":    (+0.00, +0.00),   # 중립
}


def derive_coordinate_from_analysis(analysis: IgFeedAnalysis) -> VisualCoordinate:
    """IgFeedAnalysis → VisualCoordinate.

    heuristic:
      shape  ← tone_category + style_consistency (가중)
      volume ← pose_frequency 힌트
      age    ← tone_category + three_month_shift 영향

    이 함수는 MVP heuristic. Phase H 이후 Haiku 재산출 가능.
    """
    # tone 기반 baseline (0.5 중앙 + heuristic 편차)
    tone_shape_d, tone_age_d = _TONE_HEURISTICS.get(
        analysis.tone_category, (0.0, 0.0),
    )

    # style_consistency 가 높으면 tone 편차 증폭 (일관성 = 의도성)
    weight = 0.5 + min(max(analysis.style_consistency, 0.0), 1.0) * 0.5

    shape_raw = 0.5 + tone_shape_d * weight
    age_raw = 0.5 + tone_age_d * weight

    # pose_frequency 에서 volume 추정 (정면 > 측면 = 입체 작음)
    pose = analysis.pose_frequency or ""
    if "정면 > 측면" in pose:
        volume_raw = 0.45
    elif "측면 > 정면" in pose:
        volume_raw = 0.60
    else:
        volume_raw = 0.50

    return VisualCoordinate(
        shape=_clamp01(shape_raw),
        volume=_clamp01(volume_raw),
        age=_clamp01(age_raw),
    )


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


# ─────────────────────────────────────────────
#  Photo pair selection
# ─────────────────────────────────────────────

def select_photo_pairs(
    user_posts: list[IgLatestPost],
    target_posts: list[IgLatestPost],
    gap: GapVector,
    *,
    max_pairs: int = 5,
) -> list[PhotoPair]:
    """본인 × 대상 사진 1:1 인덱스 매칭 페어 (3-5쌍).

    v2 (Sonnet cross-analysis) — stub writer 호출 폐기. PhotoPair 는
    URL 만 채워진 빈 shell. ``aspiration_engine_sonnet.compose_aspiration_v2``
    결과의 ``photo_pair_comments[i]`` 가 호출자에서 ``pair_comment`` 에 채워짐.

    MVP 전략:
      - user_posts 에서 display_url 있는 것 중 앞 max_pairs 장
      - target_posts 에서 display_url 있는 것 중 앞 max_pairs 장
      - 1:1 인덱스 매칭

    가드 (v2.1):
      - vault.ig_feed_cache 오염 감지 — user_urls 와 target_urls 가 동일 set
        이면 페어 0 반환 + warning log (본인 IG 사진 자리에 추구미 사진 노출
        회귀 방지).
      - user_urls 와 target_urls 첫 prefix 같으면 (R2 / CDN 같은 도메인 의심)
        info log (정상 케이스도 있어 차단은 X).
    """
    user_urls = [p.display_url for p in user_posts if p.display_url][:max_pairs]
    target_urls = [p.display_url for p in target_posts if p.display_url][:max_pairs]

    logger.info(
        "select_photo_pairs: user_n=%d target_n=%d "
        "user_first=%r target_first=%r",
        len(user_urls), len(target_urls),
        user_urls[0][:80] if user_urls else None,
        target_urls[0][:80] if target_urls else None,
    )

    # 가드 1 — 동일 set 오염 (본인 vault 가 추구미 데이터로 채워진 케이스)
    if user_urls and target_urls and set(user_urls) == set(target_urls):
        logger.warning(
            "select_photo_pairs: user_urls == target_urls (vault contamination?). "
            "Returning empty pairs. user_first=%r",
            user_urls[0][:80],
        )
        return []

    n = min(len(user_urls), len(target_urls))
    if n < 1:
        logger.warning(
            "select_photo_pairs: insufficient pairs (user=%d target=%d) — "
            "returning empty. 본인 IG essentials 미완 또는 vault.latest_posts 비어있음 가능.",
            len(user_urls), len(target_urls),
        )
        return []

    pairs: list[PhotoPair] = []
    for i in range(n):
        # 가드 2 — 같은 페어 안에서 user == target URL 이면 skip (개별 페어 단위)
        if user_urls[i] == target_urls[i]:
            logger.warning(
                "select_photo_pairs: pair %d user==target URL — skipping. url=%r",
                i, user_urls[i][:80],
            )
            continue
        pairs.append(PhotoPair(
            user_photo_url=user_urls[i],
            target_photo_url=target_urls[i],
            pair_comment=None,
            pair_axis_hint=None,
        ))
    return pairs


# ─────────────────────────────────────────────
#  R2 materialization — 추구미 타깃 사진 영구 보존 (Track Aspiration STEP 3)
# ─────────────────────────────────────────────

def materialize_pairs_to_r2(
    pairs: list[PhotoPair],
    *,
    user_id: str,
    analysis_id: str,
) -> tuple[list[PhotoPair], Optional[str]]:
    """PhotoPair 의 target_photo_url 을 R2 에 영구 저장 + URL 교체.

    user_photo_url 은 vault.ig_feed_cache 의 기존 URL 그대로 유지 — STEP 2
    완료 후엔 이미 R2 URL, 미완이면 IG CDN URL (최종 전환 시 자동 정합).
    별도 aspiration_users/ 복사 없음 (비용 절감, 플랜 3.2 권장안).

    R2 key: user_media/{user_id}/aspiration_targets/{analysis_id}/photo_NN.jpg
    (r2_client.aspiration_target_photo_key 헬퍼 사용)

    Args:
      pairs: select_photo_pairs 결과.
      user_id: R2 key prefix 소유자.
      analysis_id: 분석 식별자.

    Returns:
      (업데이트된 pairs, r2_target_dir prefix 또는 None)
      개별 업로드 실패 시 해당 target URL 은 원본 유지. 전체 실패 시 None prefix.
    """
    if not pairs:
        return pairs, None

    import httpx
    from services import r2_client

    r2_dir_key = r2_client.aspiration_target_dir(user_id, analysis_id)

    updated: list[PhotoPair] = []
    with httpx.Client(timeout=8.0, follow_redirects=True) as client:
        for idx, pair in enumerate(pairs):
            target_url_new = _upload_target_to_r2(
                client, pair.target_photo_url,
                user_id=user_id, analysis_id=analysis_id, index=idx,
            )
            updated.append(pair.model_copy(update={
                # user_photo_url 유지 (vault 에서 온 R2 또는 CDN URL)
                "target_photo_url": target_url_new or pair.target_photo_url,
            }))

    return updated, r2_dir_key


def _upload_target_to_r2(
    http_client,
    src_url: str,
    *,
    user_id: str,
    analysis_id: str,
    index: int,
) -> Optional[str]:
    """단일 추구미 타깃 이미지 다운로드 → R2 저장 → public URL 반환.

    실패 시 None — caller 는 원본 URL 유지.
    """
    if not src_url:
        return None
    from services import r2_client

    key = r2_client.aspiration_target_photo_key(user_id, analysis_id, index)
    try:
        resp = http_client.get(src_url)
        resp.raise_for_status()
        content_type = (
            resp.headers.get("content-type", "image/jpeg")
            .split(";")[0]
            .strip()
            .lower()
        )
        if not content_type.startswith("image/"):
            content_type = "image/jpeg"
        r2_client.put_bytes(key, resp.content, content_type=content_type)
    except Exception:
        logger.exception("aspiration target R2 put failed: key=%s", key)
        return None

    return r2_client.public_url(key) or f"r2://{key}"


# ─────────────────────────────────────────────
#  v1.5 raw 영구 보존 헬퍼 — Apify raw + Vision raw
#
#  PII 정책 (이용약관 §11 Apify 재배포 룰 준수):
#  - raw_items 안의 pinner.username / instagram_data.username /
#    latest_comments[].text / 다른 유저 멘션 = PII.
#  - DB / LLM / SIGAK UI 절대 노출 금지.
#  - R2 보존만 OK (본인 보드 = 본인 동의 영역, 본인 IG = 본인 동의).
#  - 메타분석 시 R2 fetch 로만 활용.
# ─────────────────────────────────────────────

def materialize_apify_raw_to_r2(
    raw_items: list,
    *,
    user_id: str,
    analysis_id: str,
) -> Optional[str]:
    """Apify raw 응답 (list[dict]) 를 R2 apify_raw.json 으로 저장.

    Args:
      raw_items: Apify scraper 가 반환한 dict list (Pinterest pin 또는 IG post 전수).
      user_id: R2 key prefix 소유자.
      analysis_id: 분석 식별자.

    Returns:
      R2 public URL (성공) 또는 None (raw_items 빈값 or R2 업로드 실패).
      실패는 메인 플로우 무영향.
    """
    if not raw_items:
        return None
    from services import r2_client

    key = r2_client.aspiration_apify_raw_key(user_id, analysis_id)
    try:
        payload = json.dumps(
            {
                "items": raw_items,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "item_count": len(raw_items),
            },
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
        r2_client.put_bytes(key, payload, content_type="application/json")
    except Exception:
        logger.exception("apify_raw R2 put failed: key=%s", key)
        return None

    return r2_client.public_url(key) or f"r2://{key}"


def materialize_vision_raw_to_r2(
    vision_raw_text: Optional[str],
    *,
    user_id: str,
    analysis_id: str,
) -> Optional[str]:
    """Sonnet Vision raw response text 를 R2 vision_raw.json 으로 저장.

    Args:
      vision_raw_text: Sonnet Vision 응답 raw text (str). None 이면 저장 X.
      user_id: R2 key prefix 소유자.
      analysis_id: 분석 식별자.

    Returns:
      R2 public URL (성공) 또는 None.
    """
    if not vision_raw_text:
        return None
    from services import r2_client

    key = r2_client.aspiration_vision_raw_key(user_id, analysis_id)
    try:
        payload = json.dumps(
            {
                "raw": vision_raw_text,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "char_length": len(vision_raw_text),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        r2_client.put_bytes(key, payload, content_type="application/json")
    except Exception:
        logger.exception("vision_raw R2 put failed: key=%s", key)
        return None

    return r2_client.public_url(key) or f"r2://{key}"


def materialize_ig_vision_raw_to_r2(
    vision_raw_text: Optional[str],
    *,
    user_id: str,
    snapshot_ts: str,
) -> Optional[str]:
    """본인 IG essentials 의 Sonnet Vision raw 를 R2 ig_snapshots/{ts}/vision_raw.json 저장.

    추구미 영역과 별도 prefix — ig_snapshots 디렉터리 안. PII 격리 동일.
    """
    if not vision_raw_text:
        return None
    from services import r2_client

    key = r2_client.ig_snapshot_vision_raw_key(user_id, snapshot_ts)
    try:
        payload = json.dumps(
            {
                "raw": vision_raw_text,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "char_length": len(vision_raw_text),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        r2_client.put_bytes(key, payload, content_type="application/json")
    except Exception:
        logger.exception("ig_vision_raw R2 put failed: key=%s", key)
        return None

    return r2_client.public_url(key) or f"r2://{key}"


def extract_user_posts_from_vault(vault) -> list[IgLatestPost]:
    """vault.ig_feed_cache.latest_posts → IgLatestPost 리스트.

    essentials 단계 (ig_scraper.fetch_ig_profile) 에서 저장된 본인 IG 사진 메타.
    photo_pairs 좌측 채우는 데 사용. display_url 없는 항목은 제외.
    """
    if vault is None or not vault.ig_feed_cache:
        return []
    raw = vault.ig_feed_cache.get("latest_posts") or []
    out: list[IgLatestPost] = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        url = p.get("display_url")
        if not url:
            continue
        try:
            out.append(IgLatestPost(
                caption=p.get("caption") or "",
                display_url=url,
            ))
        except Exception:
            continue
    return out


# ─────────────────────────────────────────────
#  Blocklist (DB)
# ─────────────────────────────────────────────

def is_blocked(
    db,
    *,
    target_type: TargetType,
    target_identifier: str,
) -> bool:
    """aspiration_target_blocklist 조회. 차단이면 True.

    테이블 없으면 False (마이그레이션 전 dev 환경). 예외 삼킴.
    """
    try:
        row = db.execute(
            text(
                "SELECT 1 FROM aspiration_target_blocklist "
                "WHERE target_type = :t AND target_identifier = :id LIMIT 1"
            ),
            {"t": target_type, "id": target_identifier},
        ).first()
        return row is not None
    except Exception:
        logger.exception(
            "blocklist check failed — treating as unblocked (dev/migration 미적용?)"
        )
        return False


def add_to_blocklist(
    db,
    *,
    target_type: TargetType,
    target_identifier: str,
    reason: Optional[str] = None,
) -> None:
    """대상자 삭제 요청 처리. PK 충돌 시 idempotent."""
    db.execute(
        text(
            "INSERT INTO aspiration_target_blocklist "
            "  (target_type, target_identifier, blocked_at, reason) "
            "VALUES (:t, :id, NOW(), :r) "
            "ON CONFLICT (target_type, target_identifier) DO NOTHING"
        ),
        {"t": target_type, "id": target_identifier, "r": reason},
    )


# ─────────────────────────────────────────────
#  Persistence
# ─────────────────────────────────────────────

def persist_analysis(
    db,
    analysis: AspirationAnalysis,
    *,
    extra_result_data: Optional[dict] = None,
) -> None:
    """aspiration_analyses INSERT. Transaction ownership 은 caller.

    Phase J5 — extra_result_data:
      AspirationAnalysis.model_dump 외 보존할 추가 필드.
      (raw_haiku_response / raw_sonnet_vision_response / action_hints /
       matched_trends_used / strength_score_at_time / user_original_phrases_at_time …)
      dump 와 키 충돌 시 dump 가 우선 (안전망 — schema 필드 보존).
    """
    payload = analysis.model_dump(mode="json")
    if extra_result_data:
        for k, v in extra_result_data.items():
            if k not in payload:
                payload[k] = v
    db.execute(
        text(
            "INSERT INTO aspiration_analyses "
            "  (id, user_id, target_type, target_identifier, result_data, created_at) "
            "VALUES (:id, :uid, :t, :ti, CAST(:rd AS jsonb), :ca)"
        ),
        {
            "id": analysis.analysis_id,
            "uid": analysis.user_id,
            "t": analysis.target_type,
            "ti": analysis.target_identifier,
            "rd": json.dumps(payload, ensure_ascii=False, default=str),
            "ca": analysis.created_at,
        },
    )


def generate_analysis_id() -> str:
    return f"asp_{uuid.uuid4().hex[:24]}"


# ─────────────────────────────────────────────
#  Knowledge Base 매칭
# ─────────────────────────────────────────────

def match_trends_for_aspiration_direction(
    gap: GapVector,
    user_coord: VisualCoordinate,
    gender: str,
    *,
    season: Optional[str] = None,
    limit: int = 3,
) -> list[str]:
    """추구미 이동 방향에 맞는 트렌드 ID 반환.

    간단 heuristic: user_coord + gap 적용한 '도착 좌표' 기준으로 KnowledgeMatcher 조회.
    """
    target_coord = VisualCoordinate(
        shape=_clamp01(user_coord.shape + _axis_delta(gap, "shape")),
        volume=_clamp01(user_coord.volume + _axis_delta(gap, "volume")),
        age=_clamp01(user_coord.age + _axis_delta(gap, "age")),
    )
    # UserTasteProfile 에 target 좌표를 current_position 으로 넣어 매칭 재사용
    stub_profile = UserTasteProfile(
        user_id="__aspiration_target_stub__",
        snapshot_at=datetime.now(timezone.utc),
        current_position=target_coord,
    )
    matched = match_trends_for_user(
        stub_profile, gender=gender if gender in ("female", "male") else "female",
        season=season, limit=limit,
    )
    return [m.trend.trend_id for m in matched]


def _axis_delta(gap: GapVector, axis: str) -> float:
    if gap.primary_axis == axis:
        return gap.primary_delta
    if gap.secondary_axis == axis:
        return gap.secondary_delta
    if gap.tertiary_axis == axis:
        return gap.tertiary_delta
    return 0.0


# ─────────────────────────────────────────────
#  taste_profile slim helper (Phase J5 — vault 5/5)
# ─────────────────────────────────────────────

def _render_taste_profile_for_aspiration(profile: UserTasteProfile) -> dict:
    """Verdict v2 _render_taste_profile() 패턴 — 5 필드 dump + Phase I PI hint.

    sia_writer._render_taste_profile_slim 에 위임 (단일 진실 원천).
    Phase J5 — Aspiration narrative 가 vault 5 필드 (current_position /
    aspiration_vector / conversation_signals / user_original_phrases /
    strength_score) 풀 활용하기 위한 slim dump.

    Phase I Backward echo:
      - latest_pi.top_action_text → "pi_action_hint" 키로 명시 추가.
      - 상품명 직접 호명 금지 — "지난번 정밀 분석" 우회 표현.
      - None / 빈 latest_pi → 키 미추가 (첫 진입 회귀 0).
    """
    out = _render_taste_profile_slim(profile)
    if profile.latest_pi is not None:
        top_action = getattr(profile.latest_pi, "top_action_text", None)
        if top_action:
            out["pi_action_hint"] = (
                "지난번 정밀 분석에서 권장한 핵심 액션: "
                f"{top_action} — 추구미 갭 narrative 작성 시 이전 액션과의 "
                "정합/차이 자연스럽게 carry."
            )
    return out


# ─────────────────────────────────────────────
#  Overall message — Haiku Sia writer 어댑터
# ─────────────────────────────────────────────

def compose_overall_message(
    *,
    target_display_name: str,
    gap_vector: GapVector,
    profile: UserTasteProfile,
    target_analysis_snapshot: Optional[dict] = None,
    user_analysis_snapshot: Optional[dict] = None,
    matched_trends: Optional[list] = None,
    user_name: Optional[str] = None,
    photo_pairs: Optional[list[dict]] = None,
) -> dict:
    """추구미 비교 narrative — sia_writer.generate_aspiration_overall() 어댑터.

    Phase J5 — stub format 폐기. Haiku 호출 + vault 5/5 + JSON dict 반환.
    Phase J6 ux — user_analysis_snapshot 추가: 본인 IgFeedAnalysis dump 흘려
    LLM 이 양쪽 도출 근거 (tone/pose/consistency) 풀어쓰기 가능.

    반환 키:
      overall_message     str (5-7 문장 페르소나 B narrative)
      gap_summary         str (1-2 문장 갭 요약)
      action_hints        list[str] (3-5 개)
      raw_haiku_response  str (휘발 방지 — 원본 보존)
      matched_trends_used list (활용한 KB 트렌드 dump)
    """
    writer = get_sia_writer()
    return writer.generate_aspiration_overall(
        profile=profile,
        gap_vector=gap_vector,
        target_display_name=target_display_name,
        target_analysis_snapshot=target_analysis_snapshot,
        user_analysis_snapshot=user_analysis_snapshot,
        matched_trends=matched_trends,
        user_name=user_name,
        photo_pairs=photo_pairs,
    )
