"""Aspiration engine — IG 경로 (Phase J3).

유저가 입력한 제3자 IG 핸들을 Apify 로 수집 + Vision 분석 + 본인과 gap 비교.

본인 IG (user_profiles.ig_feed_cache) 에 영향 없음. user 는 읽기 전용.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from schemas.aspiration import (
    AspirationAnalysis,
    AspirationNumbers,
    AspirationRecommendation,
    TargetType,
)
from schemas.user_profile import IgFeedCache, IgFeedAnalysis, IgLatestPost
from schemas.user_taste import UserTasteProfile
from services.aspiration_common import (
    derive_coordinate_from_analysis,
    generate_analysis_id,
    is_blocked,
    match_trends_for_aspiration_direction,
    materialize_pairs_to_r2,
    select_photo_pairs,
)
from services.aspiration_engine_sonnet import (
    AspirationV2Error,
    PhotoInput as SonnetPhotoInput,
    build_aspiration_v2_fallback,
    compose_aspiration_v2,
)
from services.coordinate_system import VisualCoordinate, neutral_coordinate
from services.ig_feed_analyzer import analyze_ig_feed
from services.ig_scraper import (
    _build_full_cache,   # 내부 재사용 — PII scrub + Vision 포함
    _call_apify_actor,
    _normalize_handle,
)
from services.knowledge_matcher import match_trends_for_user
from config import get_settings


logger = logging.getLogger(__name__)


AspirationRunStatus = Literal[
    "completed",
    "failed_blocked",
    "failed_private",
    "failed_scrape",
    "failed_skipped",
]


class AspirationRunResult:
    """엔진 반환값 — 라우트가 status + analysis + narrative 해석.

    Phase J5 — narrative:
      sia_writer.generate_aspiration_overall() 결과 dict.
      raw_haiku_response / matched_trends_used / action_hints / gap_summary 보존.
      route 가 persist_analysis(extra_result_data=narrative) 로 휘발 방지.
    """

    def __init__(
        self,
        status: AspirationRunStatus,
        analysis: Optional[AspirationAnalysis] = None,
        error_detail: Optional[str] = None,
        narrative: Optional[dict] = None,
    ):
        self.status = status
        self.analysis = analysis
        self.error_detail = error_detail
        self.narrative = narrative


# ─────────────────────────────────────────────
#  Main entry
# ─────────────────────────────────────────────

def run_aspiration_ig(
    db,
    *,
    user_id: str,
    user_gender: Optional[str],
    user_coordinate: Optional[VisualCoordinate],
    target_handle_raw: str,
    user_posts: Optional[list[IgLatestPost]] = None,
    profile: Optional[UserTasteProfile] = None,
    user_name: Optional[str] = None,
    user_analysis_snapshot: Optional[dict] = None,
    history_context: str = "",
) -> AspirationRunResult:
    """제3자 IG 핸들 → AspirationAnalysis + narrative.

    Args:
      db: SQLAlchemy session. blocklist 체크 용.
      user_id: 본인 user id (result row 소유자)
      user_gender: KnowledgeBase 매칭에 필요
      user_coordinate: 본인 current_position (None 이면 neutral 사용)
      target_handle_raw: "@yuni" / "yuni" 등
      user_posts: 본인 IG posts (vault.ig_feed_cache.latest_posts).
                  photo_pairs 좌측 채움. None/[] 면 페어 생성 불가.
      profile: UserTasteProfile snapshot — 5 필드 풀 활용 (Phase J5).
               None 이면 user_coordinate 만 들어간 minimal profile 합성.
      user_name: Sia narrative 호명용 (basic_info.name).

    Returns:
      AspirationRunResult — analysis + narrative (raw 보존).
    """
    handle = _normalize_handle(target_handle_raw)
    if not handle:
        return AspirationRunResult("failed_skipped", error_detail="empty handle")

    # 1. 블록리스트 체크
    if is_blocked(db, target_type="ig", target_identifier=handle):
        return AspirationRunResult("failed_blocked")

    settings = get_settings()
    if not settings.ig_enabled:
        # feature flag 꺼져있으면 skip
        return AspirationRunResult("failed_skipped", error_detail="ig_enabled=false")
    if not settings.apify_api_key:
        return AspirationRunResult("failed_scrape", error_detail="apify_api_key missing")

    # 2. Apify 수집 (본인 스크레이퍼 재사용, user_profiles 미건드림)
    try:
        raw_items = _call_apify_actor(
            handle=handle,
            api_key=settings.apify_api_key,
            actor_id=settings.apify_actor_id,
            timeout=settings.ig_fetch_timeout,
        )
    except Exception as e:
        logger.exception("Apify call failed for aspiration target=%s", handle)
        return AspirationRunResult("failed_scrape", error_detail=str(e))

    if not raw_items:
        return AspirationRunResult("failed_scrape", error_detail="apify returned 0 items")

    profile_raw = raw_items[0]
    # 3. 비공개 계정 차단
    if bool(profile_raw.get("private", False)) or bool(profile_raw.get("is_private", False)):
        return AspirationRunResult("failed_private")

    # 4. 공개 계정 — cache build (Vision 포함). 이 cache 는 user 에 저장 X (메모리만).
    # v1.5: vision_raw 함께 받아 추구미 R2 디렉터리에 분리 저장 (LLM 격리).
    target_cache, target_vision_raw = _build_full_cache(profile_raw, posts_raw=raw_items)
    target_analysis = target_cache.analysis
    if target_analysis is None:
        # Vision 실패 — coordinate 산출 불가. degrade 로 진행할지 실패할지 정책 결정.
        # 추구미 분석의 핵심이 좌표 비교이므로 실패로 처리.
        return AspirationRunResult(
            "failed_scrape",
            error_detail="target vision analysis unavailable (CDN 만료 or Sonnet 오류)",
        )

    # 5. 좌표 산출 + gap
    target_coord = derive_coordinate_from_analysis(target_analysis)
    user_coord = user_coordinate or neutral_coordinate()
    gap = user_coord.gap_vector(target_coord)

    # 6. Photo pairs (vault 본인 IG 사진 + 추구미 사진 1:1 인덱스 매칭)
    user_posts_effective: list[IgLatestPost] = list(user_posts or [])
    pairs = select_photo_pairs(
        user_posts=user_posts_effective,
        target_posts=target_cache.latest_posts or [],
        gap=gap,
        max_pairs=5,
    )

    # 7. Knowledge Base 매칭 — 카테고리 다양성 강제 (mood / silhouette / color
    #    / styling_method spirit 다 흘러가도록). diversify_by_category=True default.
    effective_profile = _ensure_profile(profile, user_id, user_coord)
    gender_norm = user_gender if user_gender in ("female", "male") else "female"
    matched_trends_objs = match_trends_for_user(
        effective_profile,
        gender=gender_norm,   # type: ignore[arg-type]
        season=None,
        limit=5,
    )
    matched_trend_ids = [m.trend.trend_id for m in matched_trends_objs]

    # 8. Sonnet 4.6 cross-analysis — Verdict v2 패턴 차용. 단일 호출에 풀
    #    컨텍스트 (taste_profile + KB + history + latest_pi + analysis 양쪽).
    target_snapshot_dump = target_analysis.model_dump(mode="json")
    user_photo_inputs: list[SonnetPhotoInput] = [
        {"url": p.display_url} for p in user_posts_effective if p.display_url
    ][:5]
    target_photo_inputs: list[SonnetPhotoInput] = [
        {"url": p.display_url}
        for p in (target_cache.latest_posts or []) if p.display_url
    ][:5]

    try:
        sonnet_result = compose_aspiration_v2(
            user_id=user_id,
            user_name=user_name,
            user_photos=user_photo_inputs,
            target_photos=target_photo_inputs,
            target_display_name=f"@{handle}",
            target_type="ig",
            gap_vector_dump=gap.model_dump(mode="json"),
            user_analysis_snapshot=user_analysis_snapshot,
            target_analysis_snapshot=target_snapshot_dump,
            taste_profile=effective_profile,
            matched_trends=matched_trends_objs,
            history_context=history_context,
        )
    except AspirationV2Error:
        logger.exception(
            "aspiration v2 sonnet failed user=%s handle=%s — fallback dict",
            user_id, handle,
        )
        sonnet_result = build_aspiration_v2_fallback(
            user_name=user_name,
            target_display_name=f"@{handle}",
            gap_vector_dump=gap.model_dump(mode="json"),
            pair_n=len(pairs),
        )

    # 8-b. pair_comment 채움 (Sonnet 결과 → PhotoPair)
    pair_comments = sonnet_result.get("photo_pair_comments") or []
    for i in range(len(pairs)):
        if i < len(pair_comments) and pair_comments[i]:
            pairs[i] = pairs[i].model_copy(update={
                "pair_comment": pair_comments[i],
            })

    # 9. R2 materialization — IG CDN TTL 대비 영구 저장 (analysis_id 먼저 발급)
    analysis_id = generate_analysis_id()
    pairs_persisted, r2_target_dir = materialize_pairs_to_r2(
        pairs, user_id=user_id, analysis_id=analysis_id,
    )

    # 9-b. v1.5 — Apify raw + Vision raw R2 분리 저장 (LLM 격리)
    from services.aspiration_common import (
        materialize_apify_raw_to_r2, materialize_vision_raw_to_r2,
    )
    r2_apify_raw_key = materialize_apify_raw_to_r2(
        list(raw_items),
        user_id=user_id, analysis_id=analysis_id,
    )
    r2_vision_raw_key = materialize_vision_raw_to_r2(
        target_vision_raw, user_id=user_id, analysis_id=analysis_id,
    )

    # 9-c. matched_trends 분석 시점 스냅샷 (KB 변경 시 행동지침 보존)
    from services.aspiration_engine_pinterest import (
        _hydrate_matched_trends_snapshot,
    )
    matched_trends_snapshot = _hydrate_matched_trends_snapshot(
        matched_trend_ids,
        profile=effective_profile,
        gap_vector=gap,
        user_name=user_name,
    )

    # 10. v2 신규 필드 — recommendation / numbers (Sonnet JSON 매핑)
    rec_dump = sonnet_result.get("recommendation") or {}
    recommendation = None
    if isinstance(rec_dump, dict) and rec_dump.get("style_direction"):
        try:
            recommendation = AspirationRecommendation(
                style_direction=str(rec_dump.get("style_direction") or ""),
                next_action=str(rec_dump.get("next_action") or ""),
                why=str(rec_dump.get("why") or ""),
            )
        except Exception:
            logger.warning("recommendation parse failed user=%s", user_id)

    numbers_dump = sonnet_result.get("numbers") or {}
    numbers = None
    if isinstance(numbers_dump, dict):
        try:
            primary_axis_raw = str(numbers_dump.get("primary_axis") or "shape")
            if primary_axis_raw not in ("shape", "volume", "age"):
                primary_axis_raw = gap.primary_axis
            alignment_raw = str(numbers_dump.get("alignment") or "보통")
            if alignment_raw not in ("근접", "보통", "상충"):
                alignment_raw = "보통"
            numbers = AspirationNumbers(
                primary_axis=primary_axis_raw,   # type: ignore[arg-type]
                primary_delta=float(numbers_dump.get("primary_delta") or 0.0),
                alignment=alignment_raw,         # type: ignore[arg-type]
            )
        except Exception:
            logger.warning("numbers parse failed user=%s", user_id)

    # 11. AspirationAnalysis 조립 (v2 새 필드 포함)
    analysis = AspirationAnalysis(
        analysis_id=analysis_id,
        user_id=user_id,
        target_type="ig",
        target_identifier=handle,
        target_display_name=f"@{handle}",
        created_at=datetime.now(timezone.utc),
        user_coordinate=user_coord,
        target_coordinate=target_coord,
        gap_vector=gap,
        gap_narrative=str(sonnet_result.get("gap_narrative") or gap.narrative()),
        photo_pairs=pairs_persisted,
        best_fit_pair_index=sonnet_result.get("best_fit_pair_index"),
        hook_line=str(sonnet_result.get("hook_line") or "") or None,
        sia_overall_message=str(
            sonnet_result.get("sia_overall_message") or ""
        ),
        recommendation=recommendation,
        numbers=numbers,
        matched_trend_ids=matched_trend_ids,
        target_analysis_snapshot=target_snapshot_dump,
        images_captured_count=sum(
            1 for p in (target_cache.latest_posts or []) if p.display_url
        ),
        r2_target_dir=r2_target_dir,
        r2_apify_raw_key=r2_apify_raw_key,
        r2_vision_raw_key=r2_vision_raw_key,
        matched_trends_snapshot=matched_trends_snapshot,
    )

    # narrative 휘발 방지 — raw_sonnet_response + 분석 시점 vault 메타 보존
    narrative_persisted = {
        "raw_sonnet_response": sonnet_result.get("raw_sonnet_response") or "",
        "user_original_phrases_at_time": list(
            effective_profile.user_original_phrases
        ),
        "strength_score_at_time": effective_profile.strength_score,
        "matched_trends_used": [
            m.trend.trend_id for m in matched_trends_objs
        ],
    }

    return AspirationRunResult(
        "completed",
        analysis=analysis,
        narrative=narrative_persisted,
    )


def _ensure_profile(
    profile: Optional[UserTasteProfile],
    user_id: str,
    user_coordinate: VisualCoordinate,
) -> UserTasteProfile:
    """profile 이 None 이면 좌표만 들어간 minimal profile 합성 (회귀 가드).

    Day 1 유저 / 호출자 미흘림 케이스 fallback. 5 필드 중 current_position 만
    채워지고 나머지는 default — narrative 가 strength_score 0 으로 인식.
    """
    if profile is not None:
        return profile
    return UserTasteProfile(
        user_id=user_id,
        snapshot_at=datetime.now(timezone.utc),
        current_position=user_coordinate,
    )
