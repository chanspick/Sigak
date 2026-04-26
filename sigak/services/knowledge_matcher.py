"""KnowledgeMatcher — 유저 좌표 기반 트렌드/방법론 매칭 (Phase G7).

CLAUDE.md §4.6 정의.

매칭 로직:
- compatible_coordinates 구간 안에 유저 current_position 이 들어오면 기본 매칭.
- 구간에서 벗어난 경우에도 거리 기반 2차 후보로 허용 (너무 좁으면 매칭 0 방지).
- score = 1.0 - normalized_distance. 0.0~1.0.
- 정렬: score 내림차순.
"""
from __future__ import annotations

from typing import Optional

from schemas.knowledge import (
    CoordinateRange,
    Gender,
    MatchedTrend,
    TrendItem,
)
from schemas.user_taste import UserTasteProfile
from services.coordinate_system import VisualCoordinate, neutral_coordinate
from services.knowledge_base import load_trends


# 매칭 cutoff — 구간 밖이어도 거리 이 값 이하면 후보.
_FALLBACK_DISTANCE = 0.35


def match_trends_for_user(
    profile: UserTasteProfile,
    gender: Gender,
    season: Optional[str] = None,
    *,
    limit: int = 5,
    diversify_by_category: bool = True,
) -> list[MatchedTrend]:
    """유저 좌표 ↔ 트렌드 compatible_coordinates 매칭.

    Profile.current_position 이 None 이면 neutral(0.5,0.5,0.5) 사용.
    score 내림차순으로 상위 limit 반환.

    diversify_by_category=True (default):
      각 카테고리 최고 score 1개씩 round-robin 으로 먼저 채우고, 남은 slot 만
      글로벌 score 상위로 채움. female KB 28건 중 styling_method 가 21건 (75%)
      편중이라 limit=3~5 단순 정렬이면 헤어만 노출되는 문제 가드. mood /
      silhouette / color_palette 가 narrative 컨텍스트에 항상 살아남도록.
    diversify_by_category=False:
      기존 단순 score 정렬. 호환성 유지.
    """
    pos = profile.current_position or neutral_coordinate()
    trends = load_trends(gender=gender, season=season)

    scored: list[MatchedTrend] = []
    for trend in trends:
        distance = _distance_to_range(pos, trend.compatible_coordinates)
        # 구간 안 (distance == 0) 은 자동 채택. 밖이어도 fallback 이하면 후보.
        if distance > _FALLBACK_DISTANCE:
            continue
        score = max(0.0, 1.0 - distance / _FALLBACK_DISTANCE)
        scored.append(MatchedTrend(
            trend=trend,
            score=round(score, 3),
            distance=round(distance, 3),
        ))

    scored.sort(key=lambda m: m.score, reverse=True)

    if not diversify_by_category or len(scored) <= limit:
        return scored[:limit]

    # round 1: 각 카테고리 최고 score 1개씩 (카테고리 score 내림차순으로 순회).
    # round 2: 남은 slot 은 글로벌 score 상위에서 (이미 채택된 trend 제외).
    by_category: dict[str, list[MatchedTrend]] = {}
    for m in scored:
        cat = str(m.trend.category)
        by_category.setdefault(cat, []).append(m)

    sorted_categories = sorted(
        by_category.keys(),
        key=lambda c: by_category[c][0].score,
        reverse=True,
    )

    out: list[MatchedTrend] = []
    seen_ids: set[str] = set()

    for cat in sorted_categories:
        if len(out) >= limit:
            break
        m = by_category[cat][0]
        out.append(m)
        seen_ids.add(m.trend.trend_id)

    if len(out) < limit:
        for m in scored:
            if m.trend.trend_id in seen_ids:
                continue
            out.append(m)
            seen_ids.add(m.trend.trend_id)
            if len(out) >= limit:
                break

    out.sort(key=lambda m: m.score, reverse=True)
    return out


# ─────────────────────────────────────────────
#  Internal distance helpers
# ─────────────────────────────────────────────

def _distance_to_range(coord: VisualCoordinate, rng: CoordinateRange) -> float:
    """유저 좌표가 compatible_coordinates 구간 안이면 0, 밖이면 최단 거리.

    3축 각각에 대해 [min, max] 밖으로 벗어난 만큼의 Euclidean 거리.
    """
    dx = _axis_gap(coord.shape, rng.shape)
    dy = _axis_gap(coord.volume, rng.volume)
    dz = _axis_gap(coord.age, rng.age)
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _axis_gap(v: float, span: tuple[float, float]) -> float:
    lo, hi = span
    if v < lo:
        return lo - v
    if v > hi:
        return v - hi
    return 0.0
