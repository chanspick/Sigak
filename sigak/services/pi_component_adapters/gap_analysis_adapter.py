"""Gap Analysis 어댑터 — Phase I PI-C.

essence (current_position) ↔ aspiration_coord narrative.
- aspiration 있음: GapVector.narrative() 활용
- aspiration 없음: essence 단독 결 narrative
- vault_phrases echo 합성

순수 함수. Day 1 fallback 안전 (모든 인풋 None 가능).
"""
from __future__ import annotations

from typing import Optional

from schemas.pi_report import AxisCoord, GapAnalysisContent
from services.coordinate_system import AXES, VisualCoordinate


_NARRATIVE_MAX_CHARS = 150
_AXIS_NEUTRAL_LO = 0.4
_AXIS_NEUTRAL_HI = 0.6


def build_gap_analysis(
    coord: VisualCoordinate,
    aspiration_coord: Optional[VisualCoordinate] = None,
    vault_phrases: Optional[list[str]] = None,
) -> GapAnalysisContent:
    """essence + aspiration → GapAnalysisContent.

    Args:
        coord: current_position. UserTasteProfile 에서 로드.
        aspiration_coord: 추구미 분석 결과. 없으면 essence 단독 narrative.
        vault_phrases: 유저 발화 원어 모음. 비어있어도 OK.
    """
    safe_phrases = [p for p in (vault_phrases or []) if isinstance(p, str) and p.strip()]

    essence = AxisCoord(shape=coord.shape, volume=coord.volume, age=coord.age)

    if aspiration_coord is not None:
        aspiration = AxisCoord(
            shape=aspiration_coord.shape,
            volume=aspiration_coord.volume,
            age=aspiration_coord.age,
        )
        gap_vec = coord.gap_vector(aspiration_coord)
        narrative = gap_vec.narrative()
        if safe_phrases:
            echo_str = " · ".join(f"\"{p}\"" for p in safe_phrases[:2])
            narrative = f"{narrative} 본인이 자주 쓴 말 — {echo_str}."
    else:
        aspiration = None
        narrative = _essence_only_narrative(coord)
        if safe_phrases:
            echo_str = " · ".join(f"\"{p}\"" for p in safe_phrases[:2])
            narrative = f"{narrative} {echo_str} 결로 시작합니다."

    if len(narrative) > _NARRATIVE_MAX_CHARS:
        narrative = narrative[: _NARRATIVE_MAX_CHARS - 1].rstrip() + "…"

    return GapAnalysisContent(
        essence_coord=essence,
        aspiration_coord=aspiration,
        gap_narrative=narrative,
        vault_phrase_echo=safe_phrases[:3],
    )


def _essence_only_narrative(coord: VisualCoordinate) -> str:
    """aspiration 없을 때 essence 결만으로 narrative.

    각 축이 중립(0.4~0.6) 밖이면 short label 추출. 모두 중립이면 균형 안내.
    """
    parts: list[str] = []
    for axis_name in ("shape", "volume", "age"):
        v = float(getattr(coord, axis_name))
        info = AXES[axis_name]
        if v < _AXIS_NEUTRAL_LO:
            parts.append(info.negative_short)
        elif v > _AXIS_NEUTRAL_HI:
            parts.append(info.positive_short)

    if not parts:
        return (
            "지금은 모든 축이 균형점에 가까워요. "
            "추구미 분석으로 이동 방향을 좁혀 봅시다."
        )
    return (
        f"지금 결은 {' · '.join(parts)} 쪽으로 모여 있어요. "
        "추구미 분석으로 가고 싶은 방향을 정해 봅시다."
    )
