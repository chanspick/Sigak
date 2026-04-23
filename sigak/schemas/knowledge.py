"""Knowledge Base 스키마 (Phase G6).

CLAUDE.md §4.5 — 외부 큐레이션 지식 (트렌드 / 방법론 / 레퍼런스).
사람 큐레이션 기반. AI 자동 생성 X.

파일 레이아웃:
  services/knowledge_base/
    trends/{female,male}/{season}.yaml
    methodology/{female,male}/{topic}.yaml
    references/{female,male}_celebs/{celeb}.yaml
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Gender = Literal["female", "male"]
Category = Literal[
    "color_palette",
    "silhouette",
    "mood",
    "makeup_method",
    "grooming_method",
    "styling_method",
    "celeb_reference",
]


class CoordinateRange(BaseModel):
    """compatible_coordinates — 축별 [min, max] 구간. 유저 좌표가 이 안에 들어오면 매칭."""
    model_config = ConfigDict(extra="ignore")

    shape: tuple[float, float] = (0.0, 1.0)
    volume: tuple[float, float] = (0.0, 1.0)
    age: tuple[float, float] = (0.0, 1.0)


class TrendItem(BaseModel):
    """services/knowledge_base/trends/{gender}/{season}.yaml 의 엔트리 1개."""
    model_config = ConfigDict(extra="ignore")

    trend_id: str
    season: str                                 # "2026_spring" 등
    gender: Gender
    category: Category
    title: str
    compatible_coordinates: CoordinateRange
    action_hints: list[str] = Field(default_factory=list)
    detailed_guide: Optional[str] = None


class MethodologyItem(BaseModel):
    """services/knowledge_base/methodology/{gender}/{topic}.yaml 의 엔트리."""
    model_config = ConfigDict(extra="ignore")

    method_id: str
    gender: Gender
    topic: str                                  # "makeup_basics" / "grooming" 등
    title: str
    compatible_coordinates: CoordinateRange
    steps: list[str] = Field(default_factory=list)
    caveats: Optional[str] = None


class ReferenceItem(BaseModel):
    """services/knowledge_base/references/{gender}_celebs/*.yaml 엔트리."""
    model_config = ConfigDict(extra="ignore")

    reference_id: str
    gender: Gender
    name_display: str                           # 유저 노출명
    position: CoordinateRange                   # 그 사람의 좌표 구간
    note: Optional[str] = None


class MatchedTrend(BaseModel):
    """KnowledgeMatcher 반환 값 — 매칭 점수 + 원본 엔트리."""
    model_config = ConfigDict(extra="ignore")

    trend: TrendItem
    score: float                                # 0.0~1.0 (높을수록 유저 좌표와 가까움)
    distance: float                             # 유저 좌표 vs compatible 구간 중심 거리
