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


import re as _re

# raw 수치 패턴 — face_interpretation 해석문 필터용
RAW_NUMBER_PATTERNS = [
    r"\d+(\.\d+)?°",           # 93.7°
    r"\d+(\.\d+)?도",          # 101.5도 (한글 '도')
    r"\d+(\.\d+)?%",           # 87%
    r"0\.\d{2,}",              # 0.644, 0.872 (word boundary 제거 — 더 공격적)
    r"1\.\d{2,}",              # 1.366
    r"\d{2,}\.\d+",            # 93.7, 101.5 등 2자리 이상 소수
]


def contains_raw_metric(text: str) -> bool:
    """해석문에 raw 수치가 포함되어 있는지 검사"""
    return any(_re.search(p, text) for p in RAW_NUMBER_PATTERNS)


def sanitize_interpretation(text: str) -> str:
    """해석문에서 raw 수치 + 잔해 패턴을 제거하고 문장을 정리"""
    # 수치 제거 (contains_raw_metric 체크 없이 항상 실행 — 잔해도 처리)
    # "101.5도의 턱선" → "턱선"
    text = _re.sub(r"\d+(\.\d+)?도의?\s*", "", text)
    # "93.7°의 턱선" → "턱선"
    text = _re.sub(r"\d+(\.\d+)?°의?\s*", "", text)
    # "0.872의 황금비" → "황금비"
    text = _re.sub(r"\d+\.\d+의\s*", "", text)
    # 남은 소수점 숫자 (문장 내)
    text = _re.sub(r"\s*\d+\.\d+\s*", " ", text)
    # 남은 "101도" 등
    text = _re.sub(r"\d+도", "", text)
    # 문두 잔해 패턴 (#1: sanitize 잔해)
    text = _re.sub(r"^(각도로|비율로|돌출도로|근접도로|점수로|종횡비로)\s*", "", text)
    text = _re.sub(r"^로\s+", "", text)
    # 정리
    text = _re.sub(r"\s{2,}", " ", text).strip()
    text = _re.sub(r"^[의는이가을를에서로]\s+", "", text)
    # 빈 괄호 제거
    text = _re.sub(r"\(\s*\)", "", text)
    text = _re.sub(r"\s{2,}", " ", text).strip()
    return text


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
#  SCUT-FBP5500 AF 2000장, InsightFace 실측 (2026-04-08)
# ─────────────────────────────────────────────

FACE_STATS = {
    "jaw_angle":             {"mean": 102.92, "std": 10.70},
    "eye_tilt":              {"mean": 2.30,   "std": 2.81},
    "face_length_ratio":     {"mean": 1.227,  "std": 0.052},
    "symmetry_score":        {"mean": 0.919,  "std": 0.084},
    "golden_ratio_score":    {"mean": 0.794,  "std": 0.046},
    "cheekbone_prominence":  {"mean": 0.628,  "std": 0.088},
    "lip_fullness":          {"mean": 0.062,  "std": 0.040},
    "eye_width_ratio":       {"mean": 0.193,  "std": 0.014},
    "brow_arch":             {"mean": 0.031,  "std": 0.004},
    "eye_ratio":             {"mean": 0.343,  "std": 0.049},
    "forehead_ratio":        {"mean": 0.412,  "std": 0.044},
    "philtrum_ratio":        {"mean": 0.264,  "std": 0.051},
    "nose_bridge_height":    {"mean": 0.518,  "std": 0.039},
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

# #9: zone 이름 한글화 매핑
ZONE_NAME_KR = {
    "overall": "전체 베이스", "cheek_apple": "볼 사과존", "lip": "입술",
    "under_eye": "눈 밑", "jawline": "턱선", "forehead": "이마",
    "forehead_center": "이마 중앙", "eye_line": "아이라인", "brow": "눈썹",
    "brow_tail": "눈썹 끝", "brow_arch": "눈썹 아치", "outer_eye": "눈꼬리",
    "eye_crease": "눈두덩", "nose_bridge": "콧대", "nose_tip": "코끝",
    "mid_cheek": "볼 중앙", "cheekbone": "광대", "temple": "관자놀이",
    "lip_center": "입술 중앙", "lip_corner": "입꼬리",
}

# #4: subtone 라벨 ("웜톤·보통" → "웜 소프트")
SUBTONE_MAP = {
    ("웜톤", "밝은 편"): ("웜 라이트", "따뜻하고 밝은 톤"),
    ("웜톤", "보통"): ("웜 소프트", "따뜻하고 차분한 톤"),
    ("웜톤", "어두운 편"): ("웜 딥", "따뜻하고 깊은 톤"),
    ("쿨톤", "밝은 편"): ("쿨 라이트", "차갑고 밝은 톤"),
    ("쿨톤", "보통"): ("쿨 소프트", "차갑고 차분한 톤"),
    ("쿨톤", "어두운 편"): ("쿨 딥", "차갑고 깊은 톤"),
    ("뉴트럴", "밝은 편"): ("뉴트럴 라이트", "중성적이고 밝은 톤"),
    ("뉴트럴", "보통"): ("뉴트럴 소프트", "중성적이고 차분한 톤"),
    ("뉴트럴", "어두운 편"): ("뉴트럴 딥", "중성적이고 깊은 톤"),
}


def get_subtone_label(tone_kr: str, brightness_label: str) -> tuple[str, str]:
    """(subtone 이름, 설명) 반환."""
    return SUBTONE_MAP.get((tone_kr, brightness_label), (f"{tone_kr} {brightness_label}", ""))


# #5: metric context 라벨 생성 (무단위 비율은 자연어로)
def _get_context_label(key: str, value: float, percentile: int) -> str:
    """percentile 기반 자연어 라벨 — 숫자 대신 이것만 표시."""
    tone = percentile_to_tone_kr(percentile)
    LABEL_MAP = {
        "jaw_angle": {True: f"{round(value, 1)}\u00B0"},  # 각도는 숫자 OK
        "eye_tilt": {True: f"{round(value, 1)}\u00B0"},
    }
    if key in LABEL_MAP:
        return LABEL_MAP[key][True]
    return tone


# 얼굴형 한국어 매핑
FACE_SHAPE_KR = {
    "oval": "타원형",
    "round": "둥근형",
    "square": "각진형",
    "heart": "하트형",
    "oblong": "긴형",
}

# gap recommendation 템플릿
GAP_RECOMMENDATION_TEMPLATES = {
    "structure": {
        "increase": "구조 축에서는 좀 더 선명하고 또렷한 윤곽을 만드는 방향이 핵심이에요.",
        "decrease": "구조 축에서는 라인을 부드럽게 풀어주는 방향이 핵심이에요.",
    },
    "impression": {
        "increase": "인상 축에서는 눈매와 이목구비를 또렷하게 살리는 방향이 중요해요.",
        "decrease": "인상 축에서는 눈매와 라인을 부드럽게 풀어주는 방향이 중요해요.",
    },
    "maturity": {
        "increase": "성숙도 축에서는 세련되고 성숙한 분위기를 더하는 방향이에요.",
        "decrease": "성숙도 축에서는 어려 보이고 생기 있는 느낌을 더하는 방향이 잘 맞아요.",
    },
    "intensity": {
        "increase": "존재감 축에서는 존재감 있고 임팩트 있는 표현이 포인트예요.",
        "decrease": "존재감 축에서는 자연스럽고 힘을 뺀 표현이 포인트예요.",
    },
}


# type_reference styling_tips 방향별 테이블
DIRECTION_STYLING_TIPS = {
    ("structure", "decrease"): "각진 라인을 부드럽게 감싸는 쉐딩이 효과적이에요.",
    ("structure", "increase"): "윤곽을 또렷하게 잡아주는 하이라이트가 효과적이에요.",
    ("impression", "decrease"): "눈매와 눈썹 라인을 둥글게 잡아주면 인상이 부드러워져요.",
    ("impression", "increase"): "눈꼬리와 눈썹 끝을 살려주면 인상이 선명해져요.",
    ("maturity", "decrease"): "볼과 눈 아래에 생기를 더하면 어려 보이는 효과가 있어요.",
    ("maturity", "increase"): "음영을 깊게 주면 세련되고 성숙한 분위기가 나요.",
    ("intensity", "decrease"): "전체적으로 힘을 빼고 자연스럽게 마무리하는 게 좋아요.",
    ("intensity", "increase"): "포인트 부위를 과감하게 강조하면 존재감이 살아요.",
}


def build_type_styling_tips(type_label: str, primary_axis: str, delta: float, top_zones: list[str]) -> list[str]:
    tips = []
    tips.append(f"{type_label} 유형의 장점을 살리면서 변화를 주는 게 포인트예요.")
    direction = "decrease" if delta < 0 else "increase"
    key = (primary_axis, direction)
    if key in DIRECTION_STYLING_TIPS:
        tips.append(DIRECTION_STYLING_TIPS[key])
    if top_zones:
        zone_str = ", ".join(top_zones[:2])
        tips.append(f"특히 {zone_str} 부분에 집중하면 변화가 빠르게 느껴져요.")
    return tips


def build_gap_recommendation(axis: str, delta: float) -> str:
    direction = "decrease" if delta < 0 else "increase"
    return GAP_RECOMMENDATION_TEMPLATES.get(axis, {}).get(
        direction,
        "이 방향으로 스타일링을 조정하면 원하는 이미지에 가까워질 수 있어요."
    )


def _postposition(word: str, with_batchim: str, without_batchim: str) -> str:
    """한국어 조사 자동 선택 (받침 유무 기반)"""
    if not word:
        return with_batchim
    last_char = ord(word[-1])
    if 0xAC00 <= last_char <= 0xD7A3:
        has_batchim = (last_char - 0xAC00) % 28 != 0
        return with_batchim if has_batchim else without_batchim
    return with_batchim


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
    """주어진 수치의 백분위를 정규분포 기반으로 계산한다. 5~95 clamp."""
    stats = FACE_STATS.get(key)
    if stats is None or stats["std"] == 0:
        return 50
    raw_p = norm.cdf(value, loc=stats["mean"], scale=stats["std"]) * 100
    return max(5, min(95, int(round(raw_p))))


def percentile_to_tone_kr(p: int) -> str:
    """percentile → 서술 어휘. interpretation 생성 시 입력으로 사용."""
    if p <= 10:  return "매우 낮은 편"
    if p <= 25:  return "낮은 편"
    if p <= 40:  return "다소 낮은 편"
    if p <= 60:  return "보통 수준"
    if p <= 75:  return "다소 높은 편"
    if p <= 90:  return "높은 편"
    return "매우 높은 편"


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
        if percentile >= 60:
            return f"상위 {100 - percentile}% \u2014 균형 잡힌 구조"
        elif percentile <= 25:
            return f"하위 {percentile}% \u2014 비대칭이 있는 편"
        else:
            return "보통 수준"
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
# SCUT-FBP5500 AF InsightFace 실측 기반 (p5~p95 범위)
METRIC_RANGES = {
    "jaw_angle": {
        "label": "턱 각도", "unit": "\u00B0",
        "min_value": 85, "max_value": 125,
        "min_label": "날카로운", "max_label": "둥근",
    },
    "face_length_ratio": {
        "label": "얼굴 종횡비", "unit": "",
        "min_value": 1.1, "max_value": 1.35,
        "min_label": "넓은", "max_label": "긴",
    },
    "symmetry_score": {
        "label": "좌우 대칭도", "unit": "",
        "min_value": 0.6, "max_value": 1.0,
        "min_label": "비대칭", "max_label": "대칭",
    },
    "golden_ratio_score": {
        "label": "황금비 근접도", "unit": "",
        "min_value": 0.65, "max_value": 0.9,
        "min_label": "낮음", "max_label": "황금비",
    },
    "cheekbone_prominence": {
        "label": "광대 돌출도", "unit": "",
        "min_value": 0.4, "max_value": 0.85,
        "min_label": "평면", "max_label": "돌출",
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

        # #7: context에서 "상위X%", "하위X%" 제거
        context = _re.sub(r"상위 \d+%\s*[—\-]\s*", "", context)
        context = _re.sub(r"하위 \d+%\s*[—\-]\s*", "", context)
        context = context.strip()

        # #5: show_numeric_value (각도 단위만 숫자 표시) + context_label
        show_numeric = key in ("jaw_angle", "eye_tilt")
        context_label = _get_context_label(key, float(value), pct)

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
            "show_numeric_value": show_numeric,
            "context_label": context_label,
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

    # #4-2: 헤더에서 raw 숫자 대신 자연어
    sym_val = face_features.get("symmetry_score", 0)
    sym_pct = _percentile("symmetry_score", float(sym_val)) if sym_val else 50
    sym_label = percentile_to_tone_kr(sym_pct)
    gr_val = face_features.get("golden_ratio_score", 0)
    gr_pct = _percentile("golden_ratio_score", float(gr_val)) if gr_val else 50
    gr_label = percentile_to_tone_kr(gr_pct)

    return {
        "id": "face_structure",
        "locked": False,
        "content": {
            "face_type": face_type,
            "face_length_ratio": face_features.get("face_length_ratio", 0),
            "jaw_angle": face_features.get("jaw_angle", 0),
            "symmetry_label": f"대칭 {sym_label}",
            "golden_ratio_label": f"황금비 {gr_label}",
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

    # #4: subtone 라벨 ("웜톤·보통" → "웜 소프트")
    subtone_name, subtone_desc = get_subtone_label(tone_kr, brightness_label)

    return {
        "id": "skin_analysis",
        "locked": True,
        "unlock_level": "standard",
        "teaser": {"headline": subtone_name},
        "content": {
            "tone": tone_kr,
            "subtone": subtone_name,
            "subtone_description": subtone_desc,
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
        overall = "전체적인 얼굴 구조의 조합이 만드는 인상을 분석했습니다."

    # sanitize: 해석문에서 raw 수치 제거
    overall = sanitize_interpretation(overall)
    for fi_item in feature_items:
        fi_item["interpretation"] = sanitize_interpretation(fi_item["interpretation"])
    harmony = sanitize_interpretation(harmony) if harmony else harmony
    distinctive = [sanitize_interpretation(p) for p in distinctive] if distinctive else distinctive

    return {
        "id": "face_interpretation",
        "locked": True,
        "unlock_level": "standard",
        "teaser": {"headline": "얼굴 심층 해석"},
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

    # #6: 축 이름 대신 방향을 직접 서술
    primary_shift_kr = gap.get("primary_shift_kr", "")
    secondary_shift_kr = gap.get("secondary_shift_kr", "")
    primary_neg = AXIS_LABELS.get(primary_dir, {}).get("neg", "")
    primary_pos = AXIS_LABELS.get(primary_dir, {}).get("pos", "")
    # "가장 큰 변화는 볼드함을 빼고 자연스럽게 가는 거예요"
    gap_summary = f"가장 큰 변화는 더 {primary_shift_kr} 방향으로 가는 거예요."
    if secondary_shift_kr and secondary_dir != primary_dir:
        gap_summary += f" 그리고 전체적으로 더 {secondary_shift_kr} 느낌으로요."

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

        recommendation = build_gap_recommendation(axis_name, delta_val)

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
            # z축 필드 예약 (다음 스프린트)
            "trend_coordinates": None,
            "gap_to_trend": None,
            "blend_weights": None,
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

    # #8: priority 한글 라벨 + % 제거 + #9: zone 한글화
    PRIORITY_LABEL_KR = {"HIGH": "핵심 포인트", "MEDIUM": "추가하면 좋은 포인트", "LOW": "보너스"}

    category_map: dict[str, dict] = {}
    for item in llm_items:
        cat_raw = item.get("category", "기타")
        cat = ZONE_NAME_KR.get(cat_raw, cat_raw)  # zone 한글화
        priority = item.get("priority", "MEDIUM").upper()
        rec_text = item.get("recommendation", "")

        if cat not in category_map:
            category_map[cat] = {
                "category": cat,
                "priority": PRIORITY_LABEL_KR.get(priority, priority),
                "recommendations": [],
            }

        category_map[cat]["recommendations"].append({
            "action": rec_text,
            "expected_effect": f"더 {gap.get('primary_shift_kr', '')} 느낌으로",
        })

    items = list(category_map.values())

    # 폴백: LLM이 빈 결과를 줬을 때 기본 카테고리 생성
    if not items:
        shift_kr = gap.get("primary_shift_kr", "")
        items = [
            {
                "category": "메이크업",
                "priority": "핵심 포인트",
                "recommendations": [{"action": "메이크업으로 전체 인상을 조정해보세요.", "expected_effect": f"더 {shift_kr} 느낌으로"}],
            },
            {
                "category": "헤어",
                "priority": "핵심 포인트",
                "recommendations": [{"action": "헤어 스타일링으로 분위기를 바꿔보세요.", "expected_effect": f"더 {shift_kr} 느낌으로"}],
            },
            {
                "category": "스타일링",
                "priority": "추가하면 좋은 포인트",
                "recommendations": [{"action": "전체 스타일링 방향을 맞춰보세요.", "expected_effect": "전체 조화"}],
            },
        ]

    # 티저용 카테고리 요약
    teaser_categories = [item["category"] for item in items[:3]]

    return {
        "id": "action_plan",
        "locked": True,
        "unlock_level": "full",
        "teaser": {"categories": teaser_categories},
        "content": {
            "items": items,
        },
    }


def _build_type_reference(similar_types: list[dict], report_content: dict, gap: dict = None) -> dict:
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

    # styling_tips deterministic 폴백
    if not styling_tips and gap:
        gap_vector = gap.get("vector", {})
        primary_dir = gap.get("primary_direction", "structure")
        primary_delta = gap_vector.get(primary_dir, 0)
        action_items = _safe_get(report_content, "action_items", [])
        top_zones = [item.get("category", "") for item in action_items[:2]]
        styling_tips = build_type_styling_tips(type_name, primary_dir, primary_delta, top_zones)

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


def _build_trend_context(report_content: dict, user_name: str = "", action_spec=None) -> dict:
    """trend_context 섹션 -- full 잠금. LLM 출력 무시, 항상 deterministic."""
    top_zones = []
    if action_spec and hasattr(action_spec, 'recommended_actions'):
        top_zones = [ZONE_NAME_KR.get(a.zone, a.zone) for a in action_spec.recommended_actions[:2]]
    # fallback: action_spec 없으면 report_content에서 추출
    if not top_zones:
        action_items = _safe_get(report_content, "action_items", [])
        if isinstance(action_items, list):
            top_zones = [ZONE_NAME_KR.get(item.get("category", ""), item.get("category", "")) for item in action_items[:2]]
    zone_str = ", ".join(top_zones) if top_zones else "주요 포인트"
    name = user_name or "고객"
    trends = [{
        "title": "적용 가이드",
        "description": (
            f"{name}님의 리포트에서 가장 변화가 큰 포인트는 "
            f"{zone_str} 부분이에요. "
            f"하나씩 순서대로 적용해보면서 자신에게 맞는 강도를 찾아보세요. "
            f"처음엔 가볍게 시작하고, 익숙해지면 점차 강도를 올리는 게 자연스러워요."
        ),
    }]

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
        _build_type_reference(similar_types, report_content, gap=gap),
        _build_trend_context(report_content, user_name=user_name),
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
