"""PI 전용 KB 매칭 어댑터 — Phase I PI-C.

CLAUDE.md §4.5 / §5.1 정의.

기존 `services/knowledge_matcher.match_trends_for_user` 를 카테고리 분류 후처리로
감싼다. PI 어댑터들이 각 컴포넌트 (skin / hair / coordinate_map / action_plan) 에
맞는 트렌드만 골라쓰도록 분류된 결과를 반환.

분류 기준 (schemas.knowledge.Category):
- styling_method  → hair_recommendation / action_plan source
- color_palette   → skin_analysis trend_palette_match
- mood            → action_plan / cover narrative tone
- silhouette      → coordinate_map overlay / action_plan
- 기타 (makeup_method / grooming_method / celeb_reference) 는 sources 만 채움.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from schemas.knowledge import Gender, MatchedTrend
from schemas.user_taste import UserTasteProfile
from services.knowledge_matcher import match_trends_for_user


# ─────────────────────────────────────────────
#  Result container
# ─────────────────────────────────────────────

@dataclass
class KbMatchResult:
    """PI 전용 KB 매칭 결과 — 카테고리별 분류 + sources 인용 리스트.

    각 카테고리는 score 내림차순으로 per_category_limit 까지.
    sources 는 trend_id 또는 detailed_guide 메타에서 추출한 출처 라벨.
    """
    styling_method: list[MatchedTrend] = field(default_factory=list)
    color_palette: list[MatchedTrend] = field(default_factory=list)
    mood: list[MatchedTrend] = field(default_factory=list)
    silhouette: list[MatchedTrend] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def match_for_pi(
    profile: UserTasteProfile,
    gender: Gender,
    season: Optional[str] = None,
    *,
    per_category_limit: int = 3,
    overall_limit: int = 12,
) -> KbMatchResult:
    """유저 좌표 기반 트렌드 매칭 + 카테고리 분류.

    Args:
        profile: UserTasteProfile (current_position 사용)
        gender: female | male — KB 디렉토리 분기
        season: "2026_spring" 등. None 이면 시즌 무관.
        per_category_limit: 카테고리당 최대 개수.
        overall_limit: 1차 매칭 풀 크기.

    Returns:
        KbMatchResult — 4 카테고리 + sources.
    """
    pool = match_trends_for_user(
        profile,
        gender,
        season=season,
        limit=overall_limit,
    )

    # match_trends_for_user 는 score 내림차순 정렬 보장.
    by_category: dict[str, list[MatchedTrend]] = {
        "styling_method": [],
        "color_palette": [],
        "mood": [],
        "silhouette": [],
    }
    sources: list[str] = []
    seen_sources: set[str] = set()

    for matched in pool:
        cat = matched.trend.category
        bucket = by_category.get(cat)
        if bucket is not None and len(bucket) < per_category_limit:
            bucket.append(matched)

        # 출처 인용 — detailed_guide 안 [score: ... / 라벨] 프리픽스 또는 trend_id 자체.
        src_label = _extract_source_label(matched)
        if src_label and src_label not in seen_sources:
            seen_sources.add(src_label)
            sources.append(src_label)

    return KbMatchResult(
        styling_method=by_category["styling_method"],
        color_palette=by_category["color_palette"],
        mood=by_category["mood"],
        silhouette=by_category["silhouette"],
        sources=sources,
    )


def _extract_source_label(matched: MatchedTrend) -> str:
    """detailed_guide 또는 trend_id 에서 인용 라벨 추출.

    detailed_guide 안에 `[score: ... / 라벨]` 프리픽스가 있으면 라벨만,
    없으면 trend_id 그대로.
    """
    guide = matched.trend.detailed_guide or ""
    # 프리픽스 패턴: 줄 첫 줄에 "[score: -0.8 / ↘ 하락]" 등
    first_line = guide.lstrip().splitlines()[0] if guide.strip() else ""
    if first_line.startswith("[") and "]" in first_line:
        return first_line.split("]", 1)[0] + "]"
    return matched.trend.trend_id
