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
from services.aspiration_common import (
    compose_overall_message,
    derive_coordinate_from_analysis,
    generate_analysis_id,
    is_blocked,
    match_trends_for_aspiration_direction,
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
    """엔진 반환값 — 라우트가 status + analysis 해석."""

    def __init__(
        self,
        status: AspirationRunStatus,
        analysis: Optional[AspirationAnalysis] = None,
        error_detail: Optional[str] = None,
    ):
        self.status = status
        self.analysis = analysis
        self.error_detail = error_detail


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
) -> AspirationRunResult:
    """제3자 IG 핸들 → AspirationAnalysis.

    Args:
      db: SQLAlchemy session. blocklist 체크 용.
      user_id: 본인 user id (result row 소유자)
      user_gender: KnowledgeBase 매칭에 필요
      user_coordinate: 본인 current_position (None 이면 neutral 사용)
      target_handle_raw: "@yuni" / "yuni" 등

    Returns:
      AspirationRunResult — 상태별로 analysis 유무 다름.
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
    target_cache: IgFeedCache = _build_full_cache(profile_raw, posts_raw=raw_items)
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

    # 6. Photo pairs (MVP: 앞 N장 1:1)
    user_posts: list[IgLatestPost] = []   # 라우트가 현 유저 vault 에서 채움 (MVP)
    pairs = select_photo_pairs(
        user_posts=user_posts,
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

    # 8. Sia 종합 메시지 (stub writer — Phase H 이후 Haiku 기반 교체)
    overall = compose_overall_message(
        target_display_name=f"@{handle}",
        gap=gap,
        matched_trend_count=len(matched_trend_ids),
    )

    # 9. AspirationAnalysis 조립
    analysis = AspirationAnalysis(
        analysis_id=generate_analysis_id(),
        user_id=user_id,
        target_type="ig",
        target_identifier=handle,
        target_display_name=f"@{handle}",
        created_at=datetime.now(timezone.utc),
        user_coordinate=user_coord,
        target_coordinate=target_coord,
        gap_vector=gap,
        gap_narrative=gap.narrative(),
        photo_pairs=pairs,
        sia_overall_message=overall,
        matched_trend_ids=matched_trend_ids,
        target_analysis_snapshot=target_analysis.model_dump(mode="json"),
        images_captured_count=sum(
            1 for p in (target_cache.latest_posts or []) if p.display_url
        ),
        r2_target_dir=None,   # Phase I+ R2 파이프 연결 시점에 채움
    )
    return AspirationRunResult("completed", analysis=analysis)


def attach_user_photos(
    analysis: AspirationAnalysis,
    user_posts: list[IgLatestPost],
) -> AspirationAnalysis:
    """라우트가 본인 IG posts 를 넘겨 photo_pairs 채워 넣는 post-process helper.

    run_aspiration_ig 는 engine 레벨이라 본인 데이터를 모름. 라우트 layer 에서
    UserDataVault 로드 후 이 함수로 photo_pairs 완성.
    """
    from services.aspiration_common import select_photo_pairs as _select
    target_posts = []   # target 은 run_aspiration_ig 시점에 이미 소비됨.
    # 간단: user_posts 만 덧붙여서 기존 pair 의 user_photo 를 보강.
    new_pairs = []
    for i, pair in enumerate(analysis.photo_pairs):
        if i < len(user_posts) and user_posts[i].display_url:
            pair = pair.model_copy(update={
                "user_photo_url": user_posts[i].display_url or pair.user_photo_url,
            })
        new_pairs.append(pair)
    analysis.photo_pairs = new_pairs
    return analysis
