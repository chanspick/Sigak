"""
SIGAK 3-Axis Aesthetic Coordinate System

Axes:
  1. Shape  — Soft(-1) <-> Sharp(+1)   골격과 이목구비의 형태
  2. Volume — Subtle(-1) <-> Bold(+1)   이목구비의 크기와 볼륨
  3. Age    — Fresh(-1) <-> Mature(+1)  비율이 주는 나이 인상

All axis definitions loaded from sigak/data/axis_config.yaml (SSOT).
All observed ranges loaded from sigak/data/calibration_3axis.yaml.
"""
import math
import os
import yaml
from functools import lru_cache
from typing import Optional


# ─────────────────────────────────────────────
#  YAML Config Loading (cached)
# ─────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


@lru_cache(maxsize=1)
def _load_axis_config() -> dict:
    """Load axis definitions from axis_config.yaml. Cached after first load."""
    path = os.path.join(_DATA_DIR, "axis_config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def _load_calibration() -> dict:
    """Load calibration data from calibration_3axis.yaml. Cached after first load."""
    path = os.path.join(_DATA_DIR, "calibration_3axis.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ─────────────────────────────────────────────
#  Axis Label Access (Single Source of Truth)
#  All other files MUST use these functions.
# ─────────────────────────────────────────────

def get_axis_labels(axis_name: str) -> dict:
    """축 라벨 조회. 모든 파일의 유일한 라벨 소스."""
    config = _load_axis_config()
    ax = config.get("axes", {}).get(axis_name)
    if ax is None:
        return {"name_kr": axis_name, "low": "", "high": "", "low_en": "", "high_en": "", "description": ""}
    return {
        "name_kr": ax["name_kr"],
        "low": ax["low_kr"],
        "high": ax["high_kr"],
        "low_en": ax["low"],
        "high_en": ax["high"],
        "description": ax.get("description_kr", ""),
    }


def get_all_axis_labels() -> dict:
    """전체 축 라벨. 프론트에 내려줄 때 사용."""
    config = _load_axis_config()
    return {name: get_axis_labels(name) for name in config["axes"]}


def get_axis_names() -> list[str]:
    """현재 축 이름 목록 반환. ["shape", "volume", "age"]"""
    config = _load_axis_config()
    return list(config["axes"].keys())


# ─────────────────────────────────────────────
#  Common Helpers (kept from original)
# ─────────────────────────────────────────────

def _has_valid(features: dict, key: str) -> bool:
    """feature가 존재하고 None이 아닌지 확인"""
    return key in features and features[key] is not None


def _normalize(value: float, observed_range) -> float:
    """관측 범위 기반 정규화. 범위 밖 값은 clamp. -> [-1, 1]

    observed_range can be a tuple (lo, hi) or a list [lo, hi].
    """
    if isinstance(observed_range, (list, tuple)) and len(observed_range) == 2:
        lo, hi = observed_range
    else:
        return 0.0
    if hi <= lo:
        return 0.0
    value = min(max(value, lo), hi)
    return (value - lo) / (hi - lo) * 2 - 1


def _weighted_fallback(components: list[tuple[float, float]]) -> float:
    """
    사용 가능한 component만으로 가중 평균.
    feature 미존재 시 나머지로 가중치 자동 재분배.
    """
    if not components:
        return 0.0
    weight_sum = sum(w for _, w in components)
    score = sum(v * w for v, w in components) / weight_sum
    return max(-1.0, min(1.0, score))


# ─────────────────────────────────────────────
#  Coordinate Computation (YAML-driven)
# ─────────────────────────────────────────────

def compute_coordinates(
    structural_features: dict,
    clip_embedding=None,   # reserved for future CLIP integration
    projector=None,        # reserved for future CLIP integration
) -> dict[str, float]:
    """
    12개 피처 -> 3축 좌표 계산.
    각 피처는 calibration observed_ranges로 [-1, +1] 정규화 후 가중합.

    Returns: {"shape": 0.35, "volume": -0.22, "age": 0.1}
    """
    axis_config = _load_axis_config()
    cal = _load_calibration()
    obs_ranges = cal.get("observed_ranges", {})

    coords = {}
    for axis_name, axis_def in axis_config["axes"].items():
        components = []
        for feat_name, feat_def in axis_def["features"].items():
            raw = structural_features.get(feat_name)
            if raw is None:
                continue

            feat_range = obs_ranges.get(feat_name)
            if feat_range is None:
                continue

            normalized = _normalize(raw, feat_range)

            if feat_def["direction"] == "low_is_positive":
                normalized = -normalized

            components.append((normalized, feat_def["weight"]))

        coords[axis_name] = round(_weighted_fallback(components), 3)

    return coords


# ─────────────────────────────────────────────
#  Gap Computation
# ─────────────────────────────────────────────

def compute_gap(
    current_coords: dict[str, float],
    aspiration_coords: dict[str, float],
) -> dict:
    """
    현재 좌표와 추구미 좌표 간 gap 계산.

    Returns:
        {
            "vector": {"shape": 0.5, "volume": -0.3, "age": 0.8},
            "magnitude": 0.99,
            "primary_direction": "age",
            "primary_shift_kr": "성숙한",
            "secondary_direction": "shape",
            "secondary_shift_kr": "또렷한",
        }
    """
    axis_names = get_axis_names()

    # gap vector
    vector = {}
    for axis in axis_names:
        cur = current_coords.get(axis, 0.0)
        asp = aspiration_coords.get(axis, 0.0)
        vector[axis] = round(asp - cur, 3)

    # magnitude
    magnitude = math.sqrt(sum(v ** 2 for v in vector.values()))

    # sort by |delta| descending
    sorted_axes = sorted(vector.items(), key=lambda x: abs(x[1]), reverse=True)

    # primary direction
    primary_axis = sorted_axes[0][0]
    primary_delta = sorted_axes[0][1]
    primary_labels = get_axis_labels(primary_axis)
    primary_shift_kr = primary_labels["high"] if primary_delta > 0 else primary_labels["low"]

    # secondary direction
    secondary_axis = sorted_axes[1][0] if len(sorted_axes) > 1 else None
    secondary_shift_kr = ""
    if secondary_axis:
        secondary_delta = sorted_axes[1][1]
        secondary_labels = get_axis_labels(secondary_axis)
        secondary_shift_kr = secondary_labels["high"] if secondary_delta > 0 else secondary_labels["low"]

    return {
        "vector": vector,
        "magnitude": round(magnitude, 2),
        "primary_direction": primary_axis,
        "primary_shift_kr": primary_shift_kr,
        "secondary_direction": secondary_axis,
        "secondary_shift_kr": secondary_shift_kr,
    }
