"""
SIGAK Face Comparison Engine

유저 얼굴 특징과 앵커 셀럽 얼굴 특징을 비교하여
구체적인 유사점/차이점을 산출한다.

기존 face.py의 MediaPipe 랜드마크 기반 특징을 활용하며,
similarity.py의 top-K 결과와 결합하여 리포트에 주입한다.

Usage:
    from pipeline.face_comparison import compare_with_anchor, build_comparison_narrative

    result = compare_with_anchor(user_features, anchor_key="suzy", gender="female")
    narrative = build_comparison_narrative(result)
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────
#  특징별 메타데이터 — 축 매핑 + 한국어 라벨 + 비교 기준
# ─────────────────────────────────────────────

FEATURE_META = {
    "jaw_angle": {
        "label": "턱선 각도",
        "unit": "°",
        "axis": "structure",
        "direction_map": {
            "lower": ("sharper", "더 날카로움", -1),   # 값이 낮으면 sharp
            "higher": ("softer", "더 부드러움", +1),    # 값이 높으면 soft
        },
        "similarity_threshold": 3.0,    # 이 이내면 "유사"
        "significance_threshold": 5.0,  # 이 이상이면 "유의미한 차이"
        "description_similar": "턱선 라인이 비슷한 형태입니다",
        "description_template": "턱선이 {celeb}보다 {direction}",
    },
    "cheekbone_prominence": {
        "label": "광대 돌출도",
        "unit": "",
        "axis": "structure",
        "direction_map": {
            "lower": ("flatter", "더 평평함", +1),
            "higher": ("prominent", "더 돌출됨", -1),
        },
        "similarity_threshold": 0.05,
        "significance_threshold": 0.1,
        "description_similar": "광대 볼륨감이 유사합니다",
        "description_template": "광대가 {celeb}보다 {direction}",
    },
    "eye_ratio": {
        "label": "눈 비율 (가로:세로)",
        "unit": "",
        "axis": "impression",
        "direction_map": {
            "lower": ("rounder", "더 둥근 눈", -1),     # warm 방향
            "higher": ("elongated", "더 길쭉한 눈", +1), # cool 방향
        },
        "similarity_threshold": 0.03,
        "significance_threshold": 0.06,
        "description_similar": "눈의 가로세로 비율이 유사합니다",
        "description_template": "눈매가 {celeb}보다 {direction}",
    },
    "eye_tilt": {
        "label": "눈매 기울기",
        "unit": "°",
        "axis": "impression",
        "direction_map": {
            "lower": ("downward", "더 처진 눈매", -1),   # warm
            "higher": ("upward", "더 올라간 눈매", +1),   # cool
        },
        "similarity_threshold": 1.5,
        "significance_threshold": 3.0,
        "description_similar": "눈매 각도가 유사합니다",
        "description_template": "눈꼬리가 {celeb}보다 {direction}",
    },
    "lip_fullness": {
        "label": "입술 볼륨",
        "unit": "",
        "axis": "intensity",
        "direction_map": {
            "lower": ("thinner", "더 얇은 입술", -1),    # natural
            "higher": ("fuller", "더 풍성한 입술", +1),   # bold
        },
        "similarity_threshold": 0.03,
        "significance_threshold": 0.06,
        "description_similar": "입술 두께감이 비슷합니다",
        "description_template": "입술이 {celeb}보다 {direction}",
    },
    "face_length_ratio": {
        "label": "얼굴 종횡비",
        "unit": "",
        "axis": "structure",
        "direction_map": {
            "lower": ("wider", "더 넓은 얼굴형", +1),     # soft
            "higher": ("longer", "더 긴 얼굴형", -1),     # sharp
        },
        "similarity_threshold": 0.04,
        "significance_threshold": 0.08,
        "description_similar": "얼굴 종횡비가 유사합니다",
        "description_template": "얼굴형이 {celeb}보다 {direction}",
    },
    "nose_bridge_height": {
        "label": "코 높이",
        "unit": "",
        "axis": "structure",
        "direction_map": {
            "lower": ("flatter", "더 낮은 코", +1),
            "higher": ("higher", "더 높은 코", -1),
        },
        "similarity_threshold": 0.03,
        "significance_threshold": 0.06,
        "description_similar": "코 높이가 비슷합니다",
        "description_template": "콧대가 {celeb}보다 {direction}",
    },
    "brow_arch": {
        "label": "눈썹 아치",
        "unit": "",
        "axis": "impression",
        "direction_map": {
            "lower": ("straighter", "더 일자형 눈썹", -1),  # warm/natural
            "higher": ("arched", "더 아치형 눈썹", +1),     # cool/bold
        },
        "similarity_threshold": 0.02,
        "significance_threshold": 0.05,
        "description_similar": "눈썹 형태가 유사합니다",
        "description_template": "눈썹이 {celeb}보다 {direction}",
    },
    "philtrum_ratio": {
        "label": "인중 비율",
        "unit": "",
        "axis": "maturity",
        "direction_map": {
            "lower": ("shorter", "더 짧은 인중", -1),    # fresh
            "higher": ("longer", "더 긴 인중", +1),      # mature
        },
        "similarity_threshold": 0.02,
        "significance_threshold": 0.04,
        "description_similar": "인중 길이가 비슷합니다",
        "description_template": "인중이 {celeb}보다 {direction}",
    },
    "forehead_ratio": {
        "label": "이마 비율",
        "unit": "",
        "axis": "maturity",
        "direction_map": {
            "lower": ("smaller", "더 좁은 이마", +1),     # mature
            "higher": ("larger", "더 넓은 이마", -1),     # fresh
        },
        "similarity_threshold": 0.03,
        "significance_threshold": 0.06,
        "description_similar": "이마 비율이 유사합니다",
        "description_template": "이마가 {celeb}보다 {direction}",
    },
}

# 축별 가중치 — 특정 특징이 해당 축에 미치는 영향력
AXIS_FEATURE_WEIGHTS = {
    "structure":  {"jaw_angle": 0.3, "cheekbone_prominence": 0.2, "face_length_ratio": 0.25, "nose_bridge_height": 0.25},
    "impression": {"eye_ratio": 0.3, "eye_tilt": 0.35, "brow_arch": 0.35},
    "maturity":   {"philtrum_ratio": 0.5, "forehead_ratio": 0.5},
    "intensity":  {"lip_fullness": 0.5, "brow_arch": 0.25, "cheekbone_prominence": 0.25},
}


# ─────────────────────────────────────────────
#  앵커 특징 캐시 관리
# ─────────────────────────────────────────────

_FEATURES_CACHE_PATH = Path(__file__).parent.parent / "data" / "type_features_cache.json"
_features_cache: dict | None = None


def load_anchor_features() -> dict:
    """앵커 셀럽의 사전 계산된 얼굴 특징을 로드한다."""
    global _features_cache
    if _features_cache is not None:
        return _features_cache

    if _FEATURES_CACHE_PATH.exists():
        with open(_FEATURES_CACHE_PATH, encoding="utf-8") as f:
            _features_cache = json.load(f)
        return _features_cache

    _features_cache = {}
    return _features_cache


def save_anchor_features(features_dict: dict) -> None:
    """앵커 셀럽 얼굴 특징을 JSON 캐시에 저장한다."""
    global _features_cache
    _features_cache = features_dict
    _FEATURES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_FEATURES_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(features_dict, f, ensure_ascii=False, indent=2)


def compute_and_cache_anchor_features(gender: str = "female") -> dict:
    """
    앵커 사진에서 얼굴 특징을 추출하여 캐시에 저장한다.
    embed_anchors.py 실행 후 1회 호출하면 된다.

    Returns:
        {anchor_key: {feature_name: average_value, ...}, ...}
    """
    # lazy import — face.py 의존성
    from pipeline.face import analyze_face
    import cv2
    import numpy as np

    anchors_dir = Path(__file__).parent.parent / "data" / "anchors" / gender
    if not anchors_dir.exists():
        return {}

    SUPPORTED = {".jpg", ".jpeg", ".png"}
    result = {}

    for celeb_dir in sorted(anchors_dir.iterdir()):
        if not celeb_dir.is_dir():
            continue
        celeb_key = celeb_dir.name
        all_features = []

        for img_path in sorted(celeb_dir.iterdir()):
            if img_path.suffix.lower() not in SUPPORTED:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            try:
                # analyze_face는 bytes를 받아 FaceFeatures를 반환
                img_bytes = cv2.imencode(".jpg", img)[1].tobytes()
                face_result = analyze_face(img_bytes)
                if face_result is not None:
                    all_features.append(face_result.to_dict())
            except Exception:
                continue

        if not all_features:
            continue

        # 3장 평균
        avg = {}
        all_keys = set()
        for feat in all_features:
            all_keys.update(feat.keys())
        for key in all_keys:
            values = [f[key] for f in all_features if key in f and isinstance(f[key], (int, float))]
            if values:
                avg[key] = sum(values) / len(values)

        result[celeb_key] = avg

    save_anchor_features(result)
    return result


# ─────────────────────────────────────────────
#  핵심: 유저 ↔ 앵커 비교
# ─────────────────────────────────────────────

def compare_with_anchor(
    user_features: dict,
    anchor_key: str,
    gender: str = "female",
) -> dict:
    """
    유저 얼굴 특징과 특정 앵커의 얼굴 특징을 비교한다.

    Args:
        user_features: face.py에서 추출한 유저 특징 dict
        anchor_key: type_anchors.json의 키 (예: "type_1")
        gender: "female" 또는 "male"

    Returns:
        {
            "anchor": str,
            "similarities": [...],
            "differences": [...],
            "axis_impacts": {"structure": float, "impression": float, ...},
            "narrative_prompt": str,
        }
    """
    cache = load_anchor_features()
    anchor_features = cache.get(anchor_key, {})

    if not anchor_features:
        return {
            "anchor": anchor_key,
            "similarities": [],
            "differences": [],
            "axis_impacts": {},
            "narrative_prompt": f"[{anchor_key}] 앵커 특징 데이터 없음 — 캐시 생성 필요",
        }

    # 앵커 이름 한국어 조회
    anchors_path = Path(__file__).parent.parent / "data" / "type_anchors.json"
    anchor_name_kr = anchor_key
    if anchors_path.exists():
        with open(anchors_path, encoding="utf-8") as f:
            anchors_data = json.load(f)
        anchor_info = anchors_data.get("anchors", {}).get(anchor_key, {})
        anchor_name_kr = anchor_info.get("name_kr", anchor_key)

    similarities = []
    differences = []
    axis_impacts = {"structure": 0.0, "impression": 0.0, "maturity": 0.0, "intensity": 0.0}

    for feat_key, meta in FEATURE_META.items():
        user_val = user_features.get(feat_key)
        anchor_val = anchor_features.get(feat_key)

        if user_val is None or anchor_val is None:
            continue
        if not isinstance(user_val, (int, float)) or not isinstance(anchor_val, (int, float)):
            continue

        raw_delta = user_val - anchor_val
        abs_delta = abs(raw_delta)

        # 퍼센트 차이 (0 방지)
        base = abs(anchor_val) if abs(anchor_val) > 0.001 else 1.0
        delta_pct = round((raw_delta / base) * 100, 1)

        entry = {
            "feature": feat_key,
            "label": meta["label"],
            "user": round(user_val, 4),
            "anchor": round(anchor_val, 4),
            "delta": round(raw_delta, 4),
            "delta_pct": delta_pct,
            "unit": meta["unit"],
        }

        if abs_delta <= meta["similarity_threshold"]:
            # 유사한 특징
            entry["description"] = meta["description_similar"]
            similarities.append(entry)
        elif abs_delta >= meta["significance_threshold"]:
            # 유의미한 차이
            direction_key = "higher" if raw_delta > 0 else "lower"
            direction_info = meta["direction_map"].get(direction_key, ("", "", 0))
            entry["direction_en"] = direction_info[0]
            entry["direction_kr"] = direction_info[1]
            entry["axis"] = meta["axis"]

            # 축 영향도 계산
            axis_sign = direction_info[2]
            axis = meta["axis"]
            weight = AXIS_FEATURE_WEIGHTS.get(axis, {}).get(feat_key, 0.1)
            # 영향도 = 부호 × 가중치 × 정규화된 차이
            normalized_delta = min(abs_delta / (meta["significance_threshold"] * 3), 1.0)
            impact = round(axis_sign * weight * normalized_delta, 3)
            entry["axis_impact"] = impact
            axis_impacts[axis] = round(axis_impacts[axis] + impact, 3)

            entry["description"] = meta["description_template"].format(
                celeb=anchor_name_kr,
                direction=direction_info[1],
            )
            differences.append(entry)
        else:
            # 경계 영역 — 약한 유사점으로 분류
            entry["description"] = meta["description_similar"]
            similarities.append(entry)

    # 차이점을 축 영향도 순으로 정렬
    differences.sort(key=lambda x: abs(x.get("axis_impact", 0)), reverse=True)

    # 내러티브 프롬프트 생성
    narrative = _build_narrative_prompt(anchor_name_kr, similarities, differences, axis_impacts)

    return {
        "anchor": anchor_key,
        "anchor_name_kr": anchor_name_kr,
        "similarities": similarities,
        "differences": differences,
        "axis_impacts": axis_impacts,
        "narrative_prompt": narrative,
    }


def compare_with_top_anchors(
    user_features: dict,
    similar_celebs: list[dict],
    gender: str = "female",
    max_compare: int = 3,
) -> list[dict]:
    """
    similarity.py의 top-K 결과와 결합하여, 상위 앵커들과 비교한다.

    Args:
        user_features: face.py 추출 결과
        similar_celebs: similarity.py의 find_similar_celebs() 결과
        gender: 성별
        max_compare: 비교할 앵커 수

    Returns:
        [compare_with_anchor 결과, ...]
    """
    results = []
    for celeb in similar_celebs[:max_compare]:
        key = celeb.get("key") or celeb.get("anchor_key", "")
        if not key:
            continue
        comp = compare_with_anchor(user_features, key, gender)
        comp["similarity_pct"] = celeb.get("similarity_pct", 0)
        comp["similarity_mode"] = celeb.get("mode", "unknown")
        results.append(comp)
    return results


# ─────────────────────────────────────────────
#  LLM 프롬프트용 내러티브 생성
# ─────────────────────────────────────────────

def _build_narrative_prompt(
    anchor_name: str,
    similarities: list[dict],
    differences: list[dict],
    axis_impacts: dict,
) -> str:
    """비교 결과를 LLM 프롬프트 삽입용 문자열로 변환."""
    lines = [f"[유저 ↔ {anchor_name} 핀포인트 비교]"]

    if similarities:
        lines.append("  유사한 점:")
        for s in similarities[:3]:
            lines.append(f"    • {s['label']}: {s['description']} (유저 {s['user']}{s['unit']} / {anchor_name} {s['anchor']}{s['unit']})")

    if differences:
        lines.append("  차이점:")
        for d in differences[:4]:
            impact_str = f"→ {d['axis']} 축 영향 {d['axis_impact']:+.2f}" if "axis_impact" in d else ""
            lines.append(f"    • {d['label']}: {d['description']} ({d['delta_pct']:+.1f}%) {impact_str}")

    # 축별 종합 영향
    significant_axes = [(ax, val) for ax, val in axis_impacts.items() if abs(val) >= 0.05]
    if significant_axes:
        significant_axes.sort(key=lambda x: abs(x[1]), reverse=True)
        impact_parts = []
        for ax, val in significant_axes:
            direction = "+" if val > 0 else "-"
            impact_parts.append(f"{ax} {direction}{abs(val):.2f}")
        lines.append(f"  축별 종합: {', '.join(impact_parts)}")

    lines.append(f"  → 리포트에 위 비교 데이터를 자연스러운 한국어로 서술해주세요.")
    return "\n".join(lines)


def format_comparison_for_report(
    comparisons: list[dict],
    tier: str = "full",
) -> str:
    """
    비교 결과를 리포트 프론트엔드용 LLM 프롬프트에 삽입할 문자열로 포매팅.
    tier에 따라 노출 범위를 제한한다.
    """
    if not comparisons:
        return "[핀포인트 비교] 데이터 없음"

    parts = []
    for comp in comparisons:
        name = comp.get("anchor_name_kr", comp.get("anchor", "?"))
        sim = comp.get("similarity_pct", 0)
        parts.append(f"\n--- {name}와 비교 (유사도 {sim}%) ---")

        if tier in ("standard", "full", "creator", "wedding"):
            # 유사점 (standard 이상)
            for s in comp.get("similarities", [])[:2]:
                parts.append(f"  [유사] {s['label']}: {s['description']}")

        if tier in ("full", "creator", "wedding"):
            # 차이점 (full 이상)
            for d in comp.get("differences", [])[:4]:
                parts.append(f"  [차이] {d['label']}: {d['description']} ({d['delta_pct']:+.1f}%)")

            # 축 영향
            impacts = comp.get("axis_impacts", {})
            sig = [(a, v) for a, v in impacts.items() if abs(v) >= 0.05]
            if sig:
                sig.sort(key=lambda x: abs(x[1]), reverse=True)
                parts.append(f"  [축영향] {', '.join(f'{a}:{v:+.2f}' for a, v in sig)}")

    return "\n".join(parts)