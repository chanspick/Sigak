"""
SIGAK Report Formatter -- 파이프라인 출력 -> 프론트엔드 ReportData 변환

파이프라인의 CV/LLM 분석 결과를 프론트엔드가 기대하는
ReportData JSON 구조로 변환하는 브릿지 모듈.

프론트엔드 기대 구조: sigak-web/lib/types/report.ts (ReportData)
"""
import json
import math
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.stats import norm


def _sanitize(obj):
    """numpy 타입을 Python 네이티브 타입으로 변환 (JSON 직렬화용)."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif hasattr(obj, 'item'):
        # np.float32, np.float64, np.int32, np.int64 등 모든 numpy 스칼라
        return obj.item()
    return obj


# ─────────────────────────────────────────────
#  한국 여성 얼굴 통계 (백분위 계산용)
#  실 DB 없으므로 논문/경험 기반 근사치 사용
# ─────────────────────────────────────────────

FACE_STATS = {
    "jaw_angle":             {"mean": 124.0,  "std": 8.0},
    "eye_tilt":              {"mean": 1.5,    "std": 2.5},
    "face_length_ratio":     {"mean": 1.35,   "std": 0.1},
    "symmetry_score":        {"mean": 0.88,   "std": 0.05},
    "golden_ratio_score":    {"mean": 0.72,   "std": 0.08},
    "cheekbone_prominence":  {"mean": 0.3,    "std": 0.12},
    "lip_fullness":          {"mean": 0.045,  "std": 0.01},
    "eye_width_ratio":       {"mean": 0.24,   "std": 0.03},
    "brow_arch":             {"mean": 0.015,  "std": 0.005},
}

# 피부톤별 추천/비추천 컬러
SKIN_COLOR_MAP = {
    "warm": {
        "recommended": ["코랄", "피치", "웜베이지", "테라코타"],
        "avoid": ["블루베이스 핑크", "쿨그레이", "라벤더"],
    },
    "cool": {
        "recommended": ["로즈", "라벤더", "쿨핑크", "베리"],
        "avoid": ["오렌지", "테라코타", "골드"],
    },
    "neutral": {
        "recommended": ["누드", "소프트핑크", "베이지", "모브"],
        "avoid": ["극강 오렌지", "극강 블루핑크"],
    },
}

# 얼굴형 한국어 매핑
FACE_SHAPE_KR = {
    "oval": "타원형",
    "round": "둥근형",
    "square": "각진형",
    "heart": "하트형",
    "oblong": "긴형",
}

# 축 라벨 (coordinate.py AXES와 동일)
AXIS_LABELS = {
    "structure":  {"name_kr": "구조",   "neg": "부드러운", "pos": "날카로운"},
    "impression": {"name_kr": "인상",   "neg": "부드러운", "pos": "선명한"},
    "maturity":   {"name_kr": "성숙도", "neg": "프레시",   "pos": "성숙"},
    "intensity":  {"name_kr": "존재감", "neg": "내추럴",   "pos": "볼드"},
}


# ─────────────────────────────────────────────
#  유틸리티
# ─────────────────────────────────────────────

def _percentile(key: str, value: float) -> int:
    """주어진 수치의 백분위를 정규분포 기반으로 계산한다."""
    stats = FACE_STATS.get(key)
    if stats is None or stats["std"] == 0:
        return 50
    pct = norm.cdf(value, loc=stats["mean"], scale=stats["std"]) * 100
    return int(round(max(1, min(99, pct))))


def _gap_difficulty(magnitude: float) -> str:
    """갭 크기에 따른 난이도 라벨을 반환한다."""
    if magnitude < 0.3:
        return "작은 변화"
    elif magnitude <= 0.7:
        return "중간 난이도"
    else:
        return "큰 변화"


def _axis_difficulty(delta: float) -> str:
    """개별 축 델타에 따른 난이도 라벨."""
    abs_d = abs(delta)
    if abs_d < 0.2:
        return "작은 변화"
    elif abs_d <= 0.5:
        return "중간 변화"
    else:
        return "큰 변화"


def _get_axis_label(axis: str, score: float) -> str:
    """축 점수에 따른 극성 라벨을 반환한다."""
    labels = AXIS_LABELS.get(axis, {})
    if score < -0.3:
        return labels.get("neg", "")
    elif score > 0.3:
        return labels.get("pos", "")
    else:
        return "중립"


def _safe_get(d: dict, key: str, default=None):
    """dict에서 안전하게 값을 가져온다."""
    if d is None:
        return default
    return d.get(key, default)


def _build_metric_context(key: str, value: float, percentile: int) -> str:
    """메트릭 컨텍스트 문자열을 생성한다."""
    stats = FACE_STATS.get(key)
    if stats is None:
        return ""

    mean = stats["mean"]
    diff = value - mean

    if key == "jaw_angle":
        direction = "넓은 편" if diff > 0 else "좁은 편"
        return f"평균({mean}\u00B0) 대비 {direction} \u2014 {'부드러운 라인' if diff > 0 else '날카로운 라인'}"
    elif key == "face_length_ratio":
        if 1.3 <= value <= 1.5:
            return "표준 타원형 범위(1.3-1.5)"
        elif value < 1.3:
            return "넓은 얼굴형"
        else:
            return "긴 얼굴형"
    elif key == "symmetry_score":
        rank = 100 - percentile
        return f"상위 {rank}% \u2014 {'균형 잡힌 구조' if percentile >= 60 else '보통 수준'}"
    elif key == "golden_ratio_score":
        return "조화로운 비율" if value >= 0.7 else "보통 수준"
    elif key == "cheekbone_prominence":
        if value > 0.4:
            return "돌출된 편"
        elif value < 0.2:
            return "평면적인 편"
        else:
            return "보통 수준"
    elif key == "eye_tilt":
        if value > 2.0:
            return f"평균보다 올라간 편"
        elif value < -1.0:
            return "처진 눈꼬리"
        else:
            return "보통 수준"
    elif key == "lip_fullness":
        if value > 0.05:
            return "풍성한 편"
        elif value < 0.035:
            return "얇은 편"
        else:
            return "중간 볼륨"
    elif key == "brow_arch":
        if value > 0.018:
            return "아치가 높은 편"
        elif value < 0.01:
            return "일자에 가까운 편"
        else:
            return "보통 아치"
    elif key == "eye_width_ratio":
        if value > 0.26:
            return "큰 눈"
        elif value < 0.22:
            return "작은 눈"
        else:
            return "보통 크기"

    return ""


# ─────────────────────────────────────────────
#  메트릭 빌더 (face_structure 섹션용)
# ─────────────────────────────────────────────

# 메트릭별 표시 범위 설정
METRIC_RANGES = {
    "jaw_angle": {
        "label": "턱 각도", "unit": "\u00B0",
        "min_value": 110, "max_value": 150,
        "min_label": "날카로운 110\u00B0", "max_label": "둥근 150\u00B0",
    },
    "face_length_ratio": {
        "label": "얼굴 종횡비", "unit": "",
        "min_value": 1.1, "max_value": 1.6,
        "min_label": "넓은 1.1", "max_label": "긴 1.6",
    },
    "symmetry_score": {
        "label": "좌우 대칭도", "unit": "",
        "min_value": 0.7, "max_value": 1.0,
        "min_label": "비대칭 0.7", "max_label": "대칭 1.0",
    },
    "golden_ratio_score": {
        "label": "황금비 근접도", "unit": "",
        "min_value": 0.5, "max_value": 1.0,
        "min_label": "낮음 0.5", "max_label": "황금비 1.0",
    },
    "cheekbone_prominence": {
        "label": "광대 돌출도", "unit": "",
        "min_value": 0, "max_value": 0.8,
        "min_label": "평면 0", "max_label": "돌출 0.8",
    },
}


def _build_face_metrics(features: dict) -> list[dict]:
    """face_structure 섹션의 metrics 배열을 생성한다."""
    metrics = []
    for key, config in METRIC_RANGES.items():
        value = features.get(key)
        if value is None:
            continue

        pct = _percentile(key, value)
        context = _build_metric_context(key, value, pct)

        metrics.append({
            "key": key,
            "label": config["label"],
            "value": round(value, 3) if isinstance(value, float) else value,
            "unit": config["unit"],
            "percentile": pct,
            "context": context,
            "min_value": config["min_value"],
            "max_value": config["max_value"],
            "min_label": config["min_label"],
            "max_label": config["max_label"],
        })

    return metrics


# ─────────────────────────────────────────────
#  섹션 빌더들
# ─────────────────────────────────────────────

def _build_cover(user_name: str, tier: str) -> dict:
    """cover 섹션."""
    return {
        "id": "cover",
        "locked": False,
        "content": {
            "title": "시각 리포트",
            "user_name": user_name,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "tier": tier,
        },
    }


def _build_executive_summary(report_content: dict) -> dict:
    """executive_summary 섹션."""
    summary = _safe_get(report_content, "executive_summary", "")
    if not summary:
        summary = "분석이 완료되었습니다. 상세 결과를 확인해주세요."

    return {
        "id": "executive_summary",
        "locked": False,
        "content": {
            "summary": summary,
        },
    }


def _build_face_structure(face_features: dict) -> dict:
    """face_structure 섹션 -- 무료 공개 구간."""
    face_type_raw = face_features.get("face_shape", "oval")
    face_type = FACE_SHAPE_KR.get(face_type_raw, face_type_raw)

    return {
        "id": "face_structure",
        "locked": False,
        "content": {
            "face_type": face_type,
            "face_length_ratio": face_features.get("face_length_ratio", 0),
            "jaw_angle": face_features.get("jaw_angle", 0),
            "symmetry_score": face_features.get("symmetry_score", 0),
            "golden_ratio_score": face_features.get("golden_ratio_score", 0),
            "metrics": _build_face_metrics(face_features),
        },
    }


def _build_skin_analysis(face_features: dict) -> dict:
    """skin_analysis 섹션 -- standard 잠금."""
    tone = face_features.get("skin_tone", "neutral")
    brightness = face_features.get("skin_brightness", 0.5)
    warmth = face_features.get("skin_warmth_score", 0.0)

    # 밝기 라벨
    if brightness > 0.65:
        brightness_label = "밝은 편"
    elif brightness > 0.45:
        brightness_label = "보통"
    else:
        brightness_label = "어두운 편"

    # 톤 한국어
    tone_kr_map = {"warm": "웜톤", "cool": "쿨톤", "neutral": "뉴트럴"}
    tone_kr = tone_kr_map.get(tone, tone)

    color_info = SKIN_COLOR_MAP.get(tone, SKIN_COLOR_MAP["neutral"])

    return {
        "id": "skin_analysis",
        "locked": True,
        "unlock_level": "standard",
        "teaser": {"headline": f"{tone_kr} \u00B7 {brightness_label}"},
        "content": {
            "tone": tone_kr,
            "brightness": brightness_label,
            "warmth_score": round(warmth, 2),
            "recommended_colors": color_info["recommended"],
            "avoid_colors": color_info["avoid"],
        },
    }


def _build_face_interpretation(
    face_features: dict,
    face_interpretation: dict,
) -> dict:
    """face_interpretation 섹션 -- standard 잠금.

    LLM 해석 결과를 프론트엔드 구조로 변환한다.
    LLM이 빈 결과를 줬으면 수치 기반 템플릿으로 폴백.
    """
    # LLM 결과에서 가져오기
    overall = _safe_get(face_interpretation, "overall_impression", "")
    raw_features = _safe_get(face_interpretation, "feature_interpretations", [])
    harmony = _safe_get(face_interpretation, "harmony_note", "")
    distinctive = _safe_get(face_interpretation, "distinctive_points", [])

    # LLM feature_key → 실제 face_features 키 매핑
    # LLM이 "눈", "코" 같은 통합 라벨을 반환할 수 있으므로
    FEATURE_KEY_MAP = {
        # LLM이 만들 수 있는 다양한 키/라벨 → 실제 face_features 키
        "eye": "eye_tilt", "눈": "eye_tilt", "eyes": "eye_tilt",
        "eye_shape": "eye_tilt", "눈매": "eye_tilt", "눈꼬리": "eye_tilt",
        "eye_tilt": "eye_tilt", "eye_width": "eye_width_ratio",
        "nose": "nose_length_ratio", "코": "nose_length_ratio",
        "nose_proportion": "nose_length_ratio", "코 비율": "nose_length_ratio",
        "nose_length_ratio": "nose_length_ratio", "nose_bridge_height": "nose_bridge_height",
        "lip": "lip_fullness", "입술": "lip_fullness", "lips": "lip_fullness",
        "lip_fullness": "lip_fullness",
        "symmetry": "symmetry_score", "대칭": "symmetry_score",
        "symmetry_score": "symmetry_score",
        "비율과 대칭": "symmetry_score", "비율": "face_length_ratio",
        "face_ratio": "face_length_ratio", "얼굴 비율": "face_length_ratio",
        "face_length_ratio": "face_length_ratio",
        "forehead": "forehead_ratio", "이마": "forehead_ratio",
        "forehead_ratio": "forehead_ratio",
        "brow": "brow_arch", "눈썹": "brow_arch", "brow_arch": "brow_arch",
        "cheekbone": "cheekbone_prominence", "광대": "cheekbone_prominence",
        "cheekbone_prominence": "cheekbone_prominence",
        "jaw": "jaw_angle", "턱": "jaw_angle", "턱선": "jaw_angle",
        "jaw_angle": "jaw_angle",
        "golden_ratio": "golden_ratio_score", "황금비": "golden_ratio_score",
        "golden_ratio_score": "golden_ratio_score",
        "skin_tone": "skin_brightness", "피부톤": "skin_brightness",
        "skin": "skin_brightness", "피부": "skin_brightness",
    }

    UNIT_MAP = {"jaw_angle": "\u00B0", "eye_tilt": "\u00B0"}
    LABEL_MAP = {
        "jaw_angle": ("날카로운", "둥근"),
        "eye_tilt": ("처진 -5\u00B0", "올라간 +8\u00B0"),
        "lip_fullness": ("얇은", "풍성한"),
        "brow_arch": ("일자", "아치"),
        "symmetry_score": ("비대칭", "대칭"),
        "golden_ratio_score": ("낮음", "황금비"),
        "cheekbone_prominence": ("평면", "돌출"),
        "nose_length_ratio": ("짧은", "긴"),
        "forehead_ratio": ("좁은", "넓은"),
        "eye_width_ratio": ("작은", "큰"),
    }

    # LLM feature_interpretations -> 프론트엔드 형식으로 변환
    feature_items = []
    for fi in raw_features:
        feature_key = fi.get("feature", "")
        label = fi.get("label", "")
        interp = fi.get("interpretation", "")

        # feature_key가 face_features에 없으면 매핑 테이블에서 찾기
        resolved_key = feature_key
        if feature_key not in face_features:
            resolved_key = FEATURE_KEY_MAP.get(feature_key, "")
            if not resolved_key:
                resolved_key = FEATURE_KEY_MAP.get(label, "")

        value = face_features.get(resolved_key)
        if value is not None:
            pct = _percentile(resolved_key, value)
            unit = UNIT_MAP.get(resolved_key, "")
            min_label, max_label = LABEL_MAP.get(resolved_key, ("낮음", "높음"))

            rank = 100 - pct
            range_label = f"상위 {rank}%" if pct > 50 else f"하위 {pct}%"

            feature_items.append({
                "feature": resolved_key,
                "label": label,
                "value": round(float(value), 3),
                "unit": unit,
                "percentile": pct,
                "range_label": range_label,
                "interpretation": interp,
                "min_label": min_label,
                "max_label": max_label,
            })
        else:
            # 수치 매핑 실패 — 텍스트만 전달하되 기본값 세팅 (NaN 방지)
            feature_items.append({
                "feature": feature_key,
                "label": label,
                "value": 0,
                "unit": "",
                "percentile": 50,
                "range_label": "",
                "interpretation": interp,
                "min_label": "",
                "max_label": "",
            })

    # 폴백: LLM이 빈 결과를 줬을 때
    if not overall:
        jaw = face_features.get("jaw_angle", 0)
        eye_t = face_features.get("eye_tilt", 0)
        overall = (
            f"턱 각도 {jaw}\u00B0와 눈꼬리 기울기 {eye_t:+.1f}\u00B0의 조합이 "
            "만드는 인상을 분석했습니다."
        )

    return {
        "id": "face_interpretation",
        "locked": True,
        "unlock_level": "standard",
        "teaser": {"headline": "수치 기반 얼굴 심층 해석"},
        "content": {
            "overall_impression": overall,
            "feature_interpretations": feature_items,
            "harmony_note": harmony,
            "distinctive_points": distinctive,
        },
    }


def _build_gap_analysis(
    current_coords: dict,
    aspiration_coords: dict,
    gap: dict,
    similar_types: list[dict],
    aspiration_interpretation: dict,
    report_content: dict,
) -> dict:
    """gap_analysis 섹션 -- standard 잠금."""
    magnitude = gap.get("magnitude", 0)
    difficulty = _gap_difficulty(magnitude)
    gap_vector = gap.get("vector", {})

    # 현재 유형: 가장 유사한 유형에서 가져오기
    current_type = "알 수 없음"
    current_type_id = 0
    if similar_types and len(similar_types) > 0:
        current_type = similar_types[0].get("name_kr", "알 수 없음")
        current_type_id = similar_types[0].get("type_id", 0)

    # 추구 유형: LLM 해석에서 가져오기
    aspiration_type = _safe_get(aspiration_interpretation, "reference_base", "")
    aspiration_type_id = 0

    # 갭 요약 생성
    primary_dir = gap.get("primary_direction", "")
    primary_kr = gap.get("primary_shift_kr", "")
    secondary_dir = gap.get("secondary_direction", "")

    primary_delta = abs(gap_vector.get(primary_dir, 0))
    secondary_delta = abs(gap_vector.get(secondary_dir, 0))

    primary_label = AXIS_LABELS.get(primary_dir, {}).get("name_kr", primary_dir)
    secondary_label = AXIS_LABELS.get(secondary_dir, {}).get("name_kr", secondary_dir)
    gap_summary = (
        f"주요 변화 방향은 {primary_label}이며, "
        f"{secondary_label}이 보조 방향입니다."
    )

    # direction_items 생성
    direction_items = []
    sorted_axes = sorted(gap_vector.items(), key=lambda x: abs(x[1]), reverse=True)

    for axis_name, delta_val in sorted_axes:
        if abs(delta_val) < 0.05:
            continue  # 무시할 수 있는 차이

        ax_labels = AXIS_LABELS.get(axis_name, {})
        from_score = current_coords.get(axis_name, 0)
        to_score = aspiration_coords.get(axis_name, 0)
        from_label = _get_axis_label(axis_name, from_score)
        to_label = _get_axis_label(axis_name, to_score)

        # 축별 방향 추천 텍스트 생성 (LLM 단일 content 재사용 → 중복 버그 수정)
        direction_word = ax_labels.get("pos", "") if delta_val > 0 else ax_labels.get("neg", "")
        recommendation = (
            f"{ax_labels.get('name_kr', axis_name)} 방향에서 "
            f"{'더 ' + direction_word if direction_word else '조정이'} 필요한 구간입니다."
        )

        direction_items.append({
            "axis": axis_name,
            "label": ax_labels.get("name_kr", axis_name),
            "from_score": round(from_score, 2),
            "to_score": round(to_score, 2),
            "delta": round(abs(delta_val), 2),
            "from_label": from_label,
            "to_label": to_label,
            "difficulty": _axis_difficulty(delta_val),
            "recommendation": recommendation,
        })

    return {
        "id": "gap_analysis",
        "locked": True,
        "unlock_level": "standard",
        "teaser": {"headline": f"{current_type} \u2192 {aspiration_type or '추구미'}"},
        "content": {
            "current_type": current_type,
            "current_type_id": current_type_id,
            "aspiration_type": aspiration_type or "추구미",
            "aspiration_type_id": aspiration_type_id,
            "current_coordinates": {k: round(v, 2) for k, v in current_coords.items()},
            "aspiration_coordinates": {k: round(v, 2) for k, v in aspiration_coords.items()},
            "gap_magnitude": round(magnitude, 2),
            "gap_difficulty": difficulty,
            "gap_summary": gap_summary,
            "direction_items": direction_items,
        },
    }


def _build_action_plan(
    gap: dict,
    face_features: dict,
    report_content: dict,
) -> dict:
    """action_plan 섹션 -- full 잠금.

    LLM의 action_items를 프론트엔드 구조로 변환하고,
    실제 수치 기반 delta_contribution을 추정한다.
    """
    gap_vector = gap.get("vector", {})
    magnitude = gap.get("magnitude", 0)

    # LLM action_items 가져오기
    llm_items = _safe_get(report_content, "action_items", [])

    # 카테고리별 그룹핑
    category_map: dict[str, dict] = {}
    for item in llm_items:
        cat = item.get("category", "기타")
        priority = item.get("priority", "MEDIUM").upper()
        rec_text = item.get("recommendation", "")

        if cat not in category_map:
            category_map[cat] = {
                "category": cat,
                "priority": priority,
                "target_axis": gap.get("primary_direction", "maturity"),
                "target_delta": round(abs(gap_vector.get(
                    gap.get("primary_direction", "maturity"), 0
                )), 2),
                "recommendations": [],
            }

        # delta_contribution 추정: 전체 갭을 카테고리/추천 수로 비례 배분
        est_contribution = round(magnitude * 0.15, 2) if magnitude > 0 else 0.1

        category_map[cat]["recommendations"].append({
            "action": rec_text,
            "expected_effect": f"{gap.get('primary_shift_kr', '')} 방향 이동",
            "delta_contribution": est_contribution,
        })

    items = list(category_map.values())

    # 폴백: LLM이 빈 결과를 줬을 때 기본 카테고리 생성
    if not items:
        primary_axis = gap.get("primary_direction", "maturity")
        primary_delta = abs(gap_vector.get(primary_axis, 0))
        items = [
            {
                "category": "메이크업",
                "priority": "HIGH",
                "target_axis": primary_axis,
                "target_delta": round(primary_delta, 2),
                "recommendations": [
                    {
                        "action": "갭 분석 기반 메이크업 조정 필요",
                        "expected_effect": f"{AXIS_LABELS.get(primary_axis, {}).get('name_kr', '')} 축 이동",
                        "delta_contribution": round(primary_delta * 0.3, 2),
                    },
                ],
            },
            {
                "category": "헤어",
                "priority": "HIGH",
                "target_axis": primary_axis,
                "target_delta": round(primary_delta, 2),
                "recommendations": [
                    {
                        "action": "갭 분석 기반 헤어 스타일 조정 필요",
                        "expected_effect": f"{AXIS_LABELS.get(primary_axis, {}).get('name_kr', '')} 축 이동",
                        "delta_contribution": round(primary_delta * 0.2, 2),
                    },
                ],
            },
            {
                "category": "스타일링",
                "priority": "MEDIUM",
                "target_axis": gap.get("secondary_direction", "intensity"),
                "target_delta": round(abs(gap_vector.get(
                    gap.get("secondary_direction", "intensity"), 0
                )), 2),
                "recommendations": [
                    {
                        "action": "갭 분석 기반 스타일링 조정 필요",
                        "expected_effect": "보조축 이동",
                        "delta_contribution": 0.1,
                    },
                ],
            },
        ]

    # 티저용 카테고리 요약
    teaser_categories = [
        f"{item['category']} {item['priority']}" for item in items[:3]
    ]

    return {
        "id": "action_plan",
        "locked": True,
        "unlock_level": "full",
        "teaser": {"categories": teaser_categories},
        "content": {
            "items": items,
        },
    }


def _build_type_reference(similar_types: list[dict], report_content: dict) -> dict:
    """type_reference 섹션 -- full 잠금."""
    if not similar_types:
        return {
            "id": "type_reference",
            "locked": True,
            "unlock_level": "full",
            "teaser": {"headline": "유형 분석 완료"},
            "content": {
                "type_name": "분석 중",
                "type_id": 0,
                "similarity": 0,
                "reasons": [],
                "styling_tips": [],
                "runner_ups": [],
            },
        }

    primary = similar_types[0]
    type_name = primary.get("name_kr", "알 수 없음")
    type_id = primary.get("type_id", 0)
    similarity_pct = primary.get("similarity_pct", 0)

    # LLM 리포트에서 유형 비교 정보 추출
    llm_similar = _safe_get(report_content, "similar_types", [])
    reasons = []
    styling_tips = []
    if llm_similar:
        first_llm = llm_similar[0] if isinstance(llm_similar, list) and llm_similar else {}
        reasons = first_llm.get("reason", "").split(", ") if isinstance(first_llm.get("reason"), str) else []
        if not reasons:
            reasons = [first_llm.get("reason", "")] if first_llm.get("reason") else []
        styling_insight = first_llm.get("styling_insight", "")
        if styling_insight:
            styling_tips.append(styling_insight)

    # 폴백 이유
    if not reasons:
        reasons = [f"{type_name} 유형과 구조적 유사성"]

    # runner_ups
    runner_ups = []
    for rt in similar_types[1:3]:
        runner_ups.append({
            "type_name": rt.get("name_kr", ""),
            "type_id": rt.get("type_id", 0),
            "similarity": rt.get("similarity_pct", 0),
        })

    return {
        "id": "type_reference",
        "locked": True,
        "unlock_level": "full",
        "teaser": {"headline": f"'{type_name}' 유형과 {similarity_pct}% 유사"},
        "content": {
            "type_name": type_name,
            "type_id": type_id,
            "similarity": similarity_pct,
            "reasons": reasons,
            "styling_tips": styling_tips,
            "runner_ups": runner_ups,
        },
    }


def _build_trend_context(report_content: dict) -> dict:
    """trend_context 섹션 -- full 잠금."""
    trend_text = _safe_get(report_content, "trend_context", "")
    trends = []
    if trend_text:
        trends.append({
            "title": "2026 S/S 트렌드",
            "description": trend_text,
        })
    else:
        # 기본 트렌드
        trends.append({
            "title": "2026 S/S 트렌드",
            "description": "글로우 스킨, 내추럴 브로우, 소프트 코랄 립",
        })

    return {
        "id": "trend_context",
        "locked": True,
        "unlock_level": "full",
        "teaser": None,
        "content": {
            "trends": trends,
        },
    }


# ─────────────────────────────────────────────
#  메인 포매터
# ─────────────────────────────────────────────

def format_report_for_frontend(
    user_id: str,
    user_name: str,
    tier: str,
    gender: str,
    face_features: dict,
    current_coords: dict,
    aspiration_coords: dict,
    gap: dict,
    similar_types: list[dict],
    face_interpretation: dict,
    report_content: dict,
    aspiration_interpretation: dict,
) -> dict:
    """
    파이프라인 분석 결과를 프론트엔드 ReportData 구조로 변환한다.

    이 함수는 모든 파이프라인 출력을 받아서
    sigak-web/lib/types/report.ts의 ReportData 인터페이스에
    정확히 맞는 JSON dict를 반환한다.

    Args:
        user_id: 유저 고유 ID
        user_name: 유저 이름
        tier: 진단 티어 (basic, creator, wedding)
        gender: 성별 (female, male)
        face_features: face.py의 FaceFeatures.to_dict() 결과
        current_coords: 현재 미감 4축 좌표
        aspiration_coords: 추구미 4축 좌표
        gap: compute_gap() 결과
        similar_types: find_similar_types() 결과
        face_interpretation: interpret_face_structure() LLM 결과
        report_content: generate_report() LLM 결과
        aspiration_interpretation: interpret_interview() LLM 결과

    Returns:
        프론트엔드 ReportData 구조에 맞는 dict
    """
    report_id = f"report_{user_id[:8]}"

    # v2 report_content → v1 포맷 브릿지 (generate_report v2 호환)
    if "summary" in report_content and "executive_summary" not in report_content:
        report_content["executive_summary"] = report_content["summary"]
    if "action_tips" in report_content and "action_items" not in report_content:
        report_content["action_items"] = [
            {
                "category": tip.get("zone", ""),
                "recommendation": tip.get("description", tip.get("title", "")),
                "priority": "HIGH" if i < 2 else "MEDIUM",
            }
            for i, tip in enumerate(report_content.get("action_tips", []))
        ]
    if "closing" in report_content and "trend_context" not in report_content:
        report_content["trend_context"] = report_content.get("closing", "")

    # 각 섹션 빌드
    sections = [
        _build_cover(user_name, tier),
        _build_executive_summary(report_content),
        _build_face_structure(face_features),
        _build_skin_analysis(face_features),
        _build_face_interpretation(face_features, face_interpretation),
        _build_gap_analysis(
            current_coords, aspiration_coords, gap,
            similar_types, aspiration_interpretation, report_content,
        ),
        _build_action_plan(gap, face_features, report_content),
        _build_type_reference(similar_types, report_content),
        _build_trend_context(report_content),
    ]

    result = {
        "id": report_id,
        "user_name": user_name,
        "access_level": "free",
        "pending_level": None,
        "sections": sections,
        "paywall": {
            "standard": {
                "price": 5000,
                "label": "\u20A95,000 잠금 해제",
                "method": "manual",
            },
            "full": {
                "price": 15000,
                "label": "+\u20A915,000 잠금 해제",
                "total_note": "이전 결제 포함 총 \u20A920,000",
                "method": "manual",
            },
        },
        "payment_account": {
            "bank": "카카오뱅크",
            "number": "3333-00-0000000",
            "holder": "홍한진(시각)",
            "kakao_link": "kakaotalk://send?",
        },
    }

    # numpy 타입 → Python 네이티브 변환 (FastAPI JSON 직렬화용)
    return _sanitize(result)
