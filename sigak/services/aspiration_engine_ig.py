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
    TargetType,
)
from schemas.user_profile import IgFeedCache, IgFeedAnalysis, IgLatestPost
from schemas.user_taste import UserTasteProfile
from services.aspiration_common import (
    compose_overall_message,
    derive_coordinate_from_analysis,
    generate_analysis_id,
    is_blocked,
    match_trends_for_aspiration_direction,
    materialize_pairs_to_r2,
    select_photo_pairs,
)
from services.coordinate_system import VisualCoordinate, neutral_coordinate
from services.ig_feed_analyzer import analyze_ig_feed
from services.ig_scraper import (
    _build_full_cache,   # 내부 재사용 — PII scrub + Vision 포함
    _call_apify_actor,
    _normalize_handle,
)
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

    # 7. Knowledge Base 매칭
    matched_trend_ids = match_trends_for_aspiration_direction(
        gap=gap,
        user_coord=user_coord,
        gender=user_gender or "female",
    )

    # 8. Sia 종합 narrative — Phase J5: Haiku + vault 5/5 + JSON dict
    effective_profile = _ensure_profile(profile, user_id, user_coord)
    target_snapshot_dump = target_analysis.model_dump(mode="json")
    narrative = compose_overall_message(
        target_display_name=f"@{handle}",
        gap_vector=gap,
        profile=effective_profile,
        target_analysis_snapshot=target_snapshot_dump,
        user_analysis_snapshot=user_analysis_snapshot,
        matched_trends=None,                 # routes 에서 KB hydrate (저장 후)
        user_name=user_name,
        photo_pairs=[p.model_dump() for p in pairs],
    )

    # 9. R2 materialization — IG CDN TTL 대비 영구 저장 (analysis_id 먼저 발급)
    analysis_id = generate_analysis_id()
    pairs_persisted, r2_target_dir = materialize_pairs_to_r2(
        pairs, user_id=user_id, analysis_id=analysis_id,
    )

    # 9-b. v1.5 — Apify raw + Vision raw R2 분리 저장 (LLM 격리, 추구미 IG 도 동일).
    # 본인 IG 피드 (ig_feed_cache.raw) 와 별개 영역. PII 격리 동일.
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

    # 9-c. 작업 9 — matched_trends 분석 시점 스냅샷 (KB 변경 시 행동지침 보존).
    # aspiration_engine_pinterest 에 정의된 함수 lazy import (순환 import 회피).
    from services.aspiration_engine_pinterest import (
        _hydrate_matched_trends_snapshot,
    )
    matched_trends_snapshot = _hydrate_matched_trends_snapshot(
        matched_trend_ids,
        profile=effective_profile,
        gap_vector=gap,
        user_name=user_name,
    )

    # 10. AspirationAnalysis 조립
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
        gap_narrative=(narrative.get("gap_summary") or gap.narrative()),
        photo_pairs=pairs_persisted,
        sia_overall_message=narrative["overall_message"],
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

    # narrative 에 분석 시점 vault 5 필드 메타 추가 (사용자 명령서 6-B)
    narrative_persisted = dict(narrative)
    narrative_persisted["user_original_phrases_at_time"] = list(
        effective_profile.user_original_phrases
    )
    narrative_persisted["strength_score_at_time"] = effective_profile.strength_score

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
