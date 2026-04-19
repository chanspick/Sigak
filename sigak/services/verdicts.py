"""Scoring and tier assignment helpers (MVP v1.2 Phase C).

Pure functions — no DB, no LLM. Route layer calls these after running
``compute_coordinates`` per photo and resolving the ``chugumi_target`` from
``interview_interpretation``.
"""
import math
from typing import Iterable


AXES = ("shape", "volume", "age")


def coord_distance(a: dict, b: dict) -> float:
    """Euclidean distance in the 3-axis [-1, +1] cube. Missing axes treated
    as 0 (neutral) so malformed inputs degrade rather than crash."""
    return math.sqrt(
        sum((float(a.get(k, 0)) - float(b.get(k, 0))) ** 2 for k in AXES)
    )


def score_photo(photo_coords: dict, target_coords: dict) -> float:
    """Higher is better. Range: ~0.22 (max distance ~3.46) to 1.0 (exact match).

    We use 1 / (1 + d) rather than raw -d so the scores sit in [0, 1] without
    having to renormalize. Frontend can display or hide — we only rely on the
    ordering for tier assignment.
    """
    d = coord_distance(photo_coords, target_coords)
    return 1.0 / (1.0 + d)


def assign_tiers(ranked_photos: list[dict]) -> dict[str, list[dict]]:
    """Split a score-descending list into gold/silver/bronze tiers per brief
    section (1위 GOLD, 2-4위 SILVER, 5-9위 BRONZE). Photos beyond rank 9 are
    dropped — the UX only shows 9 cells.

    Input photos are returned as-is in the output lists (no copy), so callers
    can mutate them freely if needed.
    """
    tiers: dict[str, list[dict]] = {"gold": [], "silver": [], "bronze": []}
    for i, photo in enumerate(ranked_photos):
        if i == 0:
            tiers["gold"].append(photo)
        elif i < 4:
            tiers["silver"].append(photo)
        elif i < 9:
            tiers["bronze"].append(photo)
        # i >= 9 dropped
    return tiers


def axis_delta(photo_coords: dict, target_coords: dict) -> dict:
    """Per-axis signed difference. Useful for pro_data silver/bronze readings
    to explain *which axis* the photo drifted on."""
    return {
        k: round(float(photo_coords.get(k, 0)) - float(target_coords.get(k, 0)), 3)
        for k in AXES
    }
