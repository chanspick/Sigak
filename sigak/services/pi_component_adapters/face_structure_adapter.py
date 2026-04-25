"""Face Structure 어댑터 — Phase I PI-C.

face_features dict + type_features_cache + matched_type_id → 5-7 메트릭 +
한국어 descriptor + harmony_note + distinctive_points.
순수 함수.
"""
from __future__ import annotations

from typing import Any

from schemas.pi_report import FaceStructureContent, FaceStructureMetric


# 메트릭 키 → 한국어 descriptor 생성 룰
# 각 룰: (label, lo_threshold, mid_descriptor, hi_descriptor, lo_descriptor)
_METRIC_LABELS: dict[str, dict[str, Any]] = {
    "face_length_ratio": {
        "label": "얼굴 종횡비",
        "lo": 1.0,
        "hi": 1.25,
        "lo_desc": "가로가 긴 편",
        "mid_desc": "균형 잡힌 비율",
        "hi_desc": "세로가 긴 편",
    },
    "jaw_angle": {
        "label": "턱 각도",
        "lo": 105,
        "hi": 130,
        "lo_desc": "각진 턱",
        "mid_desc": "부드러운 턱선",
        "hi_desc": "둥근 턱선",
    },
    "cheekbone_prominence": {
        "label": "광대 발달",
        "lo": 0.4,
        "hi": 0.65,
        "lo_desc": "광대 낮음",
        "mid_desc": "광대 적당함",
        "hi_desc": "광대 도드라짐",
    },
    "eye_width_ratio": {
        "label": "눈 너비 비율",
        "lo": 0.18,
        "hi": 0.22,
        "lo_desc": "눈 작은 편",
        "mid_desc": "눈 균형",
        "hi_desc": "눈 큰 편",
    },
    "eye_ratio": {
        "label": "눈 가로세로 비율",
        "lo": 0.30,
        "hi": 0.35,
        "lo_desc": "긴 눈매",
        "mid_desc": "균형 눈매",
        "hi_desc": "큰 눈매",
    },
    "lip_fullness": {
        "label": "입술 두께",
        "lo": 0.09,
        "hi": 0.12,
        "lo_desc": "얇은 입술",
        "mid_desc": "균형 입술",
        "hi_desc": "도톰한 입술",
    },
    "forehead_ratio": {
        "label": "이마 비율",
        "lo": 0.30,
        "hi": 0.42,
        "lo_desc": "짧은 이마",
        "mid_desc": "균형 이마",
        "hi_desc": "넓은 이마",
    },
    "philtrum_ratio": {
        "label": "인중 길이",
        "lo": 0.20,
        "hi": 0.27,
        "lo_desc": "짧은 인중",
        "mid_desc": "균형 인중",
        "hi_desc": "긴 인중",
    },
    "nose_length_ratio": {
        "label": "코 길이 비율",
        "lo": 0.13,
        "hi": 0.16,
        "lo_desc": "짧은 코",
        "mid_desc": "균형 코",
        "hi_desc": "긴 코",
    },
}

# 우선순위 — 5-7개 선택 시 이 순서대로
_METRIC_PRIORITY = [
    "face_length_ratio",
    "jaw_angle",
    "cheekbone_prominence",
    "eye_width_ratio",
    "eye_ratio",
    "lip_fullness",
    "forehead_ratio",
]


def build_face_structure(
    face_features: dict | None,
    type_features_cache: dict | None,
    matched_type_id: str = "",
) -> FaceStructureContent:
    """face_features 에서 5-7 메트릭을 골라 한국어 descriptor 부여.

    type_features_cache 와 비교 — 매칭 type 의 특징과 일치하면 harmony,
    벗어나면 distinctive_point.
    """
    safe_features = face_features if isinstance(face_features, dict) else {}
    safe_cache = type_features_cache if isinstance(type_features_cache, dict) else {}

    metrics: list[FaceStructureMetric] = []
    for key in _METRIC_PRIORITY:
        v = safe_features.get(key)
        if not isinstance(v, (int, float)):
            continue
        rule = _METRIC_LABELS[key]
        descriptor = _classify_metric(float(v), rule)
        metrics.append(
            FaceStructureMetric(
                name=rule["label"],
                value=round(float(v), 3),
                descriptor=descriptor,
            )
        )
        if len(metrics) >= 7:
            break

    if not metrics:
        # Day 1 fallback — 빈 face_features.
        return FaceStructureContent(
            metrics=[],
            harmony_note="얼굴 구조 데이터가 아직 없어요. PI 정면 사진 업로드 후 다시 분석해 주세요.",
            distinctive_points=[],
        )

    # harmony_note + distinctive_points: 매칭 type cache 와 비교
    type_cache = safe_cache.get(matched_type_id) if matched_type_id else None
    harmony_note, distinctive = _compose_harmony(metrics, safe_features, type_cache)

    return FaceStructureContent(
        metrics=metrics[:7] if len(metrics) > 7 else metrics,
        harmony_note=harmony_note,
        distinctive_points=distinctive[:3],
    )


def _classify_metric(value: float, rule: dict[str, Any]) -> str:
    if value < float(rule["lo"]):
        return str(rule["lo_desc"])
    if value > float(rule["hi"]):
        return str(rule["hi_desc"])
    return str(rule["mid_desc"])


def _compose_harmony(
    metrics: list[FaceStructureMetric],
    face_features: dict,
    type_cache: dict | None,
) -> tuple[str, list[str]]:
    """매칭 type cache 와 비교 — descriptor 일치/불일치 분리."""
    if not type_cache or not isinstance(type_cache, dict):
        # type 매칭 없음 → metrics 자체 결로 harmony.
        descriptors = [m.descriptor for m in metrics[:3]]
        return (
            f"전체적으로 {' · '.join(descriptors)} 결이 모여 있어요.",
            [m.descriptor for m in metrics[3:6]],
        )

    distinctive: list[str] = []
    aligned: list[str] = []
    for key in _METRIC_PRIORITY:
        v = face_features.get(key)
        cache_v = type_cache.get(key)
        if not isinstance(v, (int, float)) or not isinstance(cache_v, (int, float)):
            continue
        rule = _METRIC_LABELS[key]
        delta = abs(float(v) - float(cache_v))
        # 작은 차이 = aligned, 큰 차이 = distinctive
        threshold = (float(rule["hi"]) - float(rule["lo"])) * 0.5
        if delta < threshold:
            aligned.append(rule["label"])
        else:
            distinctive.append(f"{rule['label']}이(가) 매칭 type 과 다른 결")

    if aligned:
        harmony_note = (
            f"매칭 type 과 {', '.join(aligned[:3])} 쪽 결이 가깝게 모여 있어요."
        )
    else:
        harmony_note = "매칭 type 과는 거리가 있는 부분이 많아요. distinctive 한 결이에요."

    return harmony_note, distinctive
