"""Coordinate Map 어댑터 — Phase I PI-C.

유저 좌표 + 8 type 앵커 + silhouette trend overlay → CoordinateMapContent.

type_anchors.json 의 coords 는 내부 -1~+1 스케일. UI 노출은 외부 0~1 이므로
변환 후 AxisCoord 로 매핑. compatible_coordinates 는 외부 스케일 (schemas.knowledge
CoordinateRange 정의) 이므로 그대로 평균.

순수 함수.
"""
from __future__ import annotations

from typing import Optional

from schemas.pi_report import AxisCoord, CoordinateMapContent
from services.coordinate_system import VisualCoordinate


def build_coordinate_map(
    coord: VisualCoordinate,
    type_anchors_data: Optional[dict] = None,
    silhouette_trends: Optional[list] = None,
) -> CoordinateMapContent:
    """user 좌표 + 8 type 앵커 + silhouette 트렌드 overlay.

    Args:
        coord: 유저 current_position (외부 0~1).
        type_anchors_data: data/type_anchors.json 전체 dict.
        silhouette_trends: KbMatchResult.silhouette (list[MatchedTrend]).
    """
    user_coord = AxisCoord(shape=coord.shape, volume=coord.volume, age=coord.age)

    safe_anchors = type_anchors_data if isinstance(type_anchors_data, dict) else {}
    anchor_root = safe_anchors.get("anchors", {}) if isinstance(safe_anchors.get("anchors"), dict) else {}

    type_anchors: dict[str, AxisCoord] = {}
    for type_id, meta in anchor_root.items():
        if not isinstance(meta, dict):
            continue
        coords = meta.get("coords")
        if not isinstance(coords, dict):
            continue
        try:
            sx = float(coords.get("shape", 0.0))
            vx = float(coords.get("volume", 0.0))
            ax = float(coords.get("age", 0.0))
        except (TypeError, ValueError):
            continue
        type_anchors[str(type_id)] = AxisCoord(
            shape=_internal_to_external(sx),
            volume=_internal_to_external(vx),
            age=_internal_to_external(ax),
        )

    trend_overlay: list[dict] = []
    for matched in (silhouette_trends or []):
        try:
            rng = matched.trend.compatible_coordinates
            trend_id = matched.trend.trend_id
        except AttributeError:
            continue
        try:
            cs = (float(rng.shape[0]) + float(rng.shape[1])) / 2.0
            cv = (float(rng.volume[0]) + float(rng.volume[1])) / 2.0
            ca = (float(rng.age[0]) + float(rng.age[1])) / 2.0
        except (TypeError, ValueError, IndexError):
            continue
        trend_overlay.append({
            "trend_id": str(trend_id),
            "coord_center": {
                "shape": round(_clamp_external(cs), 3),
                "volume": round(_clamp_external(cv), 3),
                "age": round(_clamp_external(ca), 3),
            },
        })

    return CoordinateMapContent(
        user_coord=user_coord,
        type_anchors=type_anchors,
        trend_overlay=trend_overlay,
    )


def _internal_to_external(v: float) -> float:
    """내부 -1~+1 → 외부 0~1. clamp 포함."""
    clamped = max(-1.0, min(1.0, v))
    return (clamped + 1.0) / 2.0


def _clamp_external(v: float) -> float:
    return max(0.0, min(1.0, v))
