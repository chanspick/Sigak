"""Hair Recommendation 어댑터 — Phase I PI-C.

services.pi_methodology.HairMethodologyEntry → HairRecommendation.
KbMatchResult.styling_method 트렌드 id 를 trend_match 로 합성.

순수 함수.
"""
from __future__ import annotations

from typing import Optional

from schemas.pi_report import HairRecommendation, HairRecommendationContent
from services.pi_methodology import HairMethodologyEntry


_REASON_MAX_CHARS = 120


def build_hair_recommendation(
    hair_methodology: Optional[list[HairMethodologyEntry]] = None,
    styling_trends: Optional[list] = None,
    *,
    limit: int = 5,
) -> HairRecommendationContent:
    """methodology hair entries → HairRecommendationContent.

    Args:
        hair_methodology: pi_methodology.derive_methodology().hair (sorted desc).
        styling_trends: KbMatchResult.styling_method (list[MatchedTrend]).
        limit: top N (3-5 권장).
    """
    styling_ids: list[str] = []
    for matched in (styling_trends or []):
        try:
            tid = matched.trend.trend_id
        except AttributeError:
            continue
        if tid and tid not in styling_ids:
            styling_ids.append(tid)

    top_hairs: list[HairRecommendation] = []
    for entry in (hair_methodology or [])[:limit]:
        reason = entry.reason or ""
        if len(reason) > _REASON_MAX_CHARS:
            reason = reason[: _REASON_MAX_CHARS - 1].rstrip() + "…"
        top_hairs.append(
            HairRecommendation(
                hair_id=entry.hair_id,
                hair_name=entry.hair_name,
                reason=reason,
                trend_match=styling_ids[:3],
                score=round(float(entry.score), 3),
            )
        )

    return HairRecommendationContent(top_hairs=top_hairs)
