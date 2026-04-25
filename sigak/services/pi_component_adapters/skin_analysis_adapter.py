"""Skin Analysis 어댑터 — Phase I PI-C.

services.pi_methodology.ColorMethodologyEntry → SkinAnalysisContent.
KbMatchResult.color_palette 의 trend_id 를 trend_palette_match 로 합성.

순수 함수.
"""
from __future__ import annotations

from typing import Optional

from schemas.pi_report import SkinAnalysisContent
from services.pi_methodology import ColorMethodologyEntry


def build_skin_analysis(
    color: ColorMethodologyEntry,
    color_palette_trends: Optional[list] = None,
) -> SkinAnalysisContent:
    """methodology color + KB color_palette → SkinAnalysisContent.

    Args:
        color: pi_methodology.derive_methodology().color.
        color_palette_trends: KbMatchResult.color_palette (list[MatchedTrend]).
    """
    trend_ids: list[str] = []
    for matched in (color_palette_trends or []):
        try:
            tid = matched.trend.trend_id
        except AttributeError:
            continue
        if tid and tid not in trend_ids:
            trend_ids.append(tid)

    return SkinAnalysisContent(
        best_colors=list(color.best),
        ok_colors=list(color.ok),
        avoid_colors=list(color.avoid),
        foundation_guide=color.foundation,
        lip_cheek_eye=dict(color.lip_cheek_eye),
        trend_palette_match=trend_ids,
    )
