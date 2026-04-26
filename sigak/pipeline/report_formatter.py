"""
SIGAK Report Formatter -- 파이프라인 출력 -> 프론트엔드 ReportData 변환

파이프라인의 CV/LLM 분석 결과를 프론트엔드가 기대하는
ReportData JSON 구조로 변환하는 브릿지 모듈.

프론트엔드 기대 구조: sigak-web/lib/types/report.ts (ReportData)
"""
import json
import math
from datetime import datetime
from pathlib import Path
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

# ============================================================
# SKIN TONE CLASSIFICATION SYSTEM v2
# undertone (warmth 기반) × chroma (C* 기반) = 6타입
# ============================================================

SKIN_TONE_THRESHOLDS = {
    "warmth_warm_min": 8.0,
    "warmth_cool_max": -3.0,
    "chroma_clear_min": 18.0,
}

SKIN_PALETTES = {
    "warm_clear": {
        "label": "웜 클리어",
        "description": "따뜻하고 선명한 톤이에요. 생기 있는 색이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "코랄 레드", "hex": "#FF6B5B", "usage": "립"},
            {"name": "오렌지 피치", "hex": "#FF8C42", "usage": "블러셔"},
            {"name": "골드 베이지", "hex": "#C8A96E", "usage": "베이스"},
            {"name": "아이보리", "hex": "#FFFFF0", "usage": "하이라이트"},
        ],
        "avoid": [
            {"name": "블루 핑크", "hex": "#FFB6C1"},
            {"name": "라벤더", "hex": "#B57EDC"},
            {"name": "애쉬 그레이", "hex": "#B2BEB5"},
        ],
        "avoid_reason": "차가운 계열이 얼굴에서 동떨어져 보여요.",
    },
    "warm_soft": {
        "label": "웜 소프트",
        "description": "따뜻하고 부드러운 톤이에요. 차분한 색이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "살몬 핑크", "hex": "#FA8072", "usage": "립"},
            {"name": "피치", "hex": "#FFCBA4", "usage": "블러셔"},
            {"name": "웜 베이지", "hex": "#C8AD7F", "usage": "베이스"},
            {"name": "테라코타", "hex": "#CC7351", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "블루베이스 핑크", "hex": "#FF69B4"},
            {"name": "쿨 그레이", "hex": "#8C92AC"},
            {"name": "네온 계열", "hex": "#39FF14"},
        ],
        "avoid_reason": "선명하거나 차가운 색이 피부를 칙칙하게 만들어요.",
    },
    "neutral_clear": {
        "label": "뉴트럴 클리어",
        "description": "중성적이고 선명한 톤이에요. 웜/쿨 양쪽 포인트 컬러가 다 어울려요.",
        "recommended": [
            {"name": "로즈", "hex": "#E75480", "usage": "립"},
            {"name": "소프트 레드", "hex": "#C74375", "usage": "블러셔"},
            {"name": "네이비", "hex": "#000080", "usage": "포인트"},
            {"name": "에메랄드", "hex": "#50C878", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "머스타드", "hex": "#FFDB58"},
            {"name": "올리브", "hex": "#808000"},
            {"name": "카키", "hex": "#BDB76B"},
        ],
        "avoid_reason": "탁한 중간톤이 피부의 선명함을 가려요.",
    },
    "neutral_soft": {
        "label": "뉴트럴 소프트",
        "description": "중성적이고 부드러운 톤이에요. 저채도 색이 편안하게 어울려요.",
        "recommended": [
            {"name": "모브 핑크", "hex": "#D4A0A0", "usage": "립"},
            {"name": "더스티 로즈", "hex": "#DCAE96", "usage": "블러셔"},
            {"name": "소프트 베이지", "hex": "#D2B48C", "usage": "베이스"},
            {"name": "세이지", "hex": "#B2AC88", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "비비드 오렌지", "hex": "#FF5F00"},
            {"name": "네온 핑크", "hex": "#FF6EC7"},
            {"name": "퓨어 블랙", "hex": "#000000"},
        ],
        "avoid_reason": "강한 색이 피부와 충돌해서 부담스러워 보여요.",
    },
    "cool_clear": {
        "label": "쿨 클리어",
        "description": "차갑고 선명한 톤이에요. 고대비 컬러가 얼굴을 살려줘요.",
        "recommended": [
            {"name": "버건디", "hex": "#800020", "usage": "립"},
            {"name": "로즈 핑크", "hex": "#FF007F", "usage": "블러셔"},
            {"name": "로열 블루", "hex": "#4169E1", "usage": "포인트"},
            {"name": "퓨어 화이트", "hex": "#FFFFFF", "usage": "하이라이트"},
        ],
        "avoid": [
            {"name": "카멜", "hex": "#C19A6B"},
            {"name": "골드", "hex": "#FFD700"},
            {"name": "테라코타", "hex": "#E2725B"},
        ],
        "avoid_reason": "따뜻한 계열이 피부에서 누렇게 떠 보여요.",
    },
    "cool_soft": {
        "label": "쿨 소프트",
        "description": "차갑고 부드러운 톤이에요. 은은한 쿨톤 색이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "라벤더 핑크", "hex": "#C4AEAD", "usage": "립"},
            {"name": "소프트 블루", "hex": "#87CEEB", "usage": "포인트"},
            {"name": "로즈 베이지", "hex": "#C4A882", "usage": "베이스"},
            {"name": "그레이시 핑크", "hex": "#D8BFD8", "usage": "블러셔"},
        ],
        "avoid": [
            {"name": "오렌지", "hex": "#FF8C00"},
            {"name": "옐로 골드", "hex": "#FFD700"},
            {"name": "웜 브라운", "hex": "#964B00"},
        ],
        "avoid_reason": "웜톤 계열이 피부톤과 분리되어 보여요.",
    },
}


def classify_skin_type(undertone: str, chroma: float) -> dict:
    """undertone (warm/cool/neutral) × chroma (clear/soft) → 6타입 팔레트 반환."""
    # undertone 유효성 검증
    if undertone not in ("warm", "cool", "neutral"):
        undertone = "neutral"
    # chroma NaN/None 방어
    if chroma is None or (isinstance(chroma, float) and math.isnan(chroma)):
        chroma = 0.0
    threshold = SKIN_TONE_THRESHOLDS["chroma_clear_min"]
    chroma_label = "clear" if chroma >= threshold else "soft"
    key = f"{undertone}_{chroma_label}"
    return SKIN_PALETTES.get(key, SKIN_PALETTES["neutral_soft"])


# zone 이름 한글화 매핑
ZONE_NAME_KR = {
    "overall": "전체 베이스", "cheek_apple": "볼 사과존", "lip": "입술",
    "under_eye": "눈 밑", "jawline": "턱선", "forehead": "이마",
    "forehead_center": "이마 중앙", "eye_line": "아이라인", "brow": "눈썹",
    "brow_tail": "눈썹 끝", "brow_arch": "눈썹", "outer_eye": "눈꼬리",
    "eye_crease": "눈두덩", "nose_bridge": "콧대", "nose_tip": "코끝",
    "mid_cheek": "볼 중앙", "cheekbone": "광대", "temple": "관자놀이",
    "lip_center": "입술 중앙", "lip_corner": "입꼬리",
    "lip_cupid": "입술 윤곽", "cheek_center": "볼",
}


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
    "inverted_triangle": "역삼각형",
    "diamond": "다이아몬드형",
}

# gap recommendation 템플릿
GAP_RECOMMENDATION_TEMPLATES = {
    "shape": {
        "increase": "골격에서는 좀 더 선명하고 또렷한 윤곽을 만드는 방향이 핵심이에요.",
        "decrease": "골격에서는 윤곽을 둥글고 부드럽게 풀어주는 방향이 핵심이에요.",
    },
    "volume": {
        "increase": "존재감에서는 이목구비를 임팩트 있고 또렷하게 강조하는 게 포인트예요.",
        "decrease": "존재감에서는 자연스럽고 힘을 뺀 표현이 포인트예요.",
    },
    "age": {
        "increase": "무드에서는 세련되고 성숙한 느낌을 더하는 방향이에요.",
        "decrease": "무드에서는 어려 보이고 생기 있는 느낌을 더하는 방향이 잘 맞아요.",
    },
}


# type_reference styling_tips 방향별 테이블
DIRECTION_STYLING_TIPS = {
    ("shape", "decrease"): "각진 라인을 부드럽게 감싸는 쉐딩이 효과적이에요.",
    ("shape", "increase"): "윤곽을 또렷하게 잡아주는 하이라이트가 효과적이에요.",
    ("volume", "decrease"): "전체적으로 힘을 빼고 자연스럽게 마무리하는 게 좋아요.",
    ("volume", "increase"): "포인트 부위를 과감하게 강조하면 존재감이 살아요.",
    ("age", "decrease"): "볼과 눈 아래에 생기를 더하면 어려 보이는 효과가 있어요.",
    ("age", "increase"): "음영을 깊게 주면 세련되고 성숙한 분위기가 나요.",
}


def build_type_styling_tips(type_label: str, primary_axis: str, delta: float, top_zones: list[str]) -> list[str]:
    tips = []
    tips.append(f"{type_label} 유형의 장점을 살리면서 변화를 주는 게 포인트예요.")
    direction = "decrease" if delta < 0 else "increase"
    key = (primary_axis, direction)
    if key in DIRECTION_STYLING_TIPS:
        tips.append(DIRECTION_STYLING_TIPS[key])
    if top_zones:
        zone_kr = [ZONE_NAME_KR.get(z, z) for z in top_zones[:2]]
        zone_str = ", ".join(zone_kr)
        tips.append(f"특히 {zone_str} 부분에 집중하면 변화가 빠르게 느껴져요.")
    return tips


def build_gap_recommendation(axis: str, delta: float) -> str:
    direction = "decrease" if delta < 0 else "increase"
    return GAP_RECOMMENDATION_TEMPLATES.get(axis, {}).get(
        direction,
        "이 방향으로 스타일링을 조정하면 원하는 이미지에 가까워져요."
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


# 축 라벨 — coordinate.py에서 import (SSOT)
# 소비자용 name_kr과 description은 여기서 오버라이드 (표시 전용)
from pipeline.coordinate import get_axis_labels as _get_raw_axis_labels, get_all_axis_labels

# 소비자용 오버라이드: coordinate.py의 라벨 + UI 표시용 name_kr/description
_AXIS_DISPLAY_OVERRIDES = {
    "shape": {
        "name_kr": "골격",
        "description": "턱선, 광대, 눈매가 만드는 골격의 형태",
    },
    "volume": {
        "name_kr": "존재감",
        "description": "이목구비의 선명도",
    },
    "age": {
        "name_kr": "무드",
        "description": "전체적인 분위기의 방향",
    },
}


def _get_axis_display(axis_name: str) -> dict:
    """coordinate.py 라벨 + 소비자용 오버라이드 병합."""
    base = _get_raw_axis_labels(axis_name)
    override = _AXIS_DISPLAY_OVERRIDES.get(axis_name, {})
    return {**base, **override}


# 빠른 접근용 (기존 AXIS_LABELS 호환)
AXIS_LABELS = {name: _get_axis_display(name) for name in ["shape", "volume", "age"]}


def get_position_label(axis: str, value: float) -> str:
    """축 값(-1~+1)을 자연어 위치 라벨로 변환. 슬라이더 현재/추구 라벨에 사용."""
    labels = AXIS_LABELS.get(axis, {})
    abs_val = abs(value)
    if abs_val < 0.15:
        return "중간"
    direction = labels.get("high", "") if value > 0 else labels.get("low", "")
    if abs_val < 0.35:
        return f"약간 {direction}"
    elif abs_val < 0.65:
        return direction
    else:
        return f"매우 {direction}"


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
    """축 점수에 따른 극성 라벨을 반환한다. get_position_label의 간략 버전."""
    return get_position_label(axis, score)


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

        # #5: show_numeric_value — 전부 숫자 숨김 (자연어 라벨만 표시)
        show_numeric = False
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


def _build_face_structure(face_features: dict, face_interpretation: Optional[dict] = None) -> dict:
    """face_structure 섹션 -- FREE 영역 + STANDARD 해석 데이터 통합.

    FREE 영역: 얼굴형, 대칭/황금비 라벨, 메트릭 분포 바
    STANDARD 영역: overall_impression, feature_interpretations, harmony_note, distinctive_points
    프론트엔드에서 locked prop에 따라 STANDARD 영역을 블러 처리한다.
    """
    face_type_raw = face_features.get("face_shape", "oval")
    face_type = FACE_SHAPE_KR.get(face_type_raw, face_type_raw)

    # #4-2: 헤더에서 raw 숫자 대신 자연어
    sym_val = face_features.get("symmetry_score", 0)
    sym_pct = _percentile("symmetry_score", float(sym_val)) if sym_val else 50
    sym_label = percentile_to_tone_kr(sym_pct)
    gr_val = face_features.get("golden_ratio_score", 0)
    gr_pct = _percentile("golden_ratio_score", float(gr_val)) if gr_val else 50
    gr_label = percentile_to_tone_kr(gr_pct)

    content: dict = {
        "face_type": face_type,
        "face_length_ratio": face_features.get("face_length_ratio", 0),
        "jaw_angle": face_features.get("jaw_angle", 0),
        "symmetry_label": f"대칭 {sym_label}",
        "golden_ratio_label": f"황금비 {gr_label}",
        "metrics": _build_face_metrics(face_features),
        "interpretation_unlock_level": "standard",
    }

    # STANDARD 영역: face_interpretation 데이터 병합
    # 빈 dict({})여도 _build_face_interpretation_data 내부에서 fallback 처리
    if face_interpretation and (
        face_interpretation.get("overall_impression")
        or face_interpretation.get("feature_interpretations")
    ):
        interp_data = _build_face_interpretation_data(face_features, face_interpretation)
        content.update(interp_data)
    elif face_features:
        # LLM이 빈 결과를 줘도 수치 기반 최소한의 interpretation 생성
        interp_data = _build_face_interpretation_data(face_features, {
            "overall_impression": "전체적인 얼굴 구조의 조합이 만드는 인상을 분석했습니다.",
            "feature_interpretations": [],
            "harmony_note": "",
            "distinctive_points": [],
        })
        content.update(interp_data)

    return {
        "id": "face_structure",
        "locked": False,
        "content": content,
    }


def _build_skin_analysis(face_features: dict) -> dict:
    """skin_analysis 섹션 -- standard 잠금. v3: 4계절 x 서브타입 (6타입 폴백)."""
    undertone = face_features.get("skin_tone", "neutral")
    chroma = face_features.get("skin_chroma", 0.0)
    warmth = face_features.get("skin_warmth_score", 0.0)
    brightness = face_features.get("skin_brightness", 0.5)
    hex_sample = face_features.get("skin_hex_sample", "#999999")
    personal_color = face_features.get("personal_color")

    # 4계절 데이터가 있으면 새 시스템 사용, 없으면 6타입 폴백
    if personal_color:
        from pipeline.personal_color import get_season_palette

        season = personal_color.get("season", "spring")
        subtype = personal_color.get("subtype", "light")
        label_kr = personal_color.get("label_kr", "")
        confidence = personal_color.get("confidence", 0.0)

        palette = get_season_palette(season, subtype)

        return {
            "id": "skin_analysis",
            "locked": True,
            "unlock_level": "standard",
            "teaser": {"headline": palette["label_kr"]},
            "content": {
                "tone": palette["label_kr"],
                "tone_description": palette["description"],
                "hex_sample": hex_sample,
                # 3단계 팔레트 (best / okay / avoid)
                "best_colors": palette.get("best_colors", []),
                "okay_colors": palette.get("okay_colors", []),
                "avoid_colors": palette.get("avoid_colors", []),
                # 하위호환: 기존 recommended/avoid 키 유지
                "recommended": palette.get("best_colors", palette.get("recommended", [])),
                "avoid": palette.get("avoid_colors", palette.get("avoid", [])),
                "avoid_reason": palette.get("avoid_reason", ""),
                # 헤어컬러 추천
                "hair_colors": palette.get("hair_colors", []),
                # 활용 가이드
                "season": season,
                "subtype": subtype,
                "lip_direction": palette.get("lip_direction", ""),
                "cheek_direction": palette.get("cheek_direction", ""),
                "eye_direction": palette.get("eye_direction", ""),
                "foundation_guide": palette.get("foundation_guide", ""),
                "confidence": confidence,
                "_undertone": undertone,
                "_chroma": round(chroma, 1),
                "_warmth": round(warmth, 1),
                "_brightness": round(brightness, 3),
            },
        }

    # 폴백: 기존 6타입 시스템
    skin_type = classify_skin_type(undertone, chroma)

    return {
        "id": "skin_analysis",
        "locked": True,
        "unlock_level": "standard",
        "teaser": {"headline": skin_type["label"]},
        "content": {
            "tone": skin_type["label"],
            "tone_description": skin_type["description"],
            "hex_sample": hex_sample,
            # 6타입 폴백은 best/okay 구분 없음 — recommended를 best로 매핑
            "best_colors": skin_type["recommended"],
            "okay_colors": [],
            "avoid_colors": skin_type["avoid"],
            "hair_colors": [],
            "recommended": skin_type["recommended"],
            "avoid": skin_type["avoid"],
            "avoid_reason": skin_type["avoid_reason"],
            "_undertone": undertone,
            "_chroma": round(chroma, 1),
            "_warmth": round(warmth, 1),
            "_brightness": round(brightness, 3),
        },
    }


def _build_face_interpretation_data(
    face_features: dict,
    face_interpretation: dict,
) -> dict:
    """face_interpretation 데이터를 content dict로 반환 (face_structure에 병합용).

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
        "eye_tilt": ("처진", "올라간"),
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

            show_numeric = False  # 전부 숫자 숨김
            context_label = _get_context_label(resolved_key, float(value), pct)

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
                "show_numeric_value": show_numeric,
                "context_label": context_label,
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
        "overall_impression": overall,
        "feature_interpretations": feature_items,
        "harmony_note": harmony,
        "distinctive_points": distinctive,
    }


def _get_trend_point() -> dict | None:
    """트렌드 방향 좌표를 산점도용 {x, y, size}로 변환."""
    try:
        from pipeline.trend_data import TREND_DIRECTION
        return {
            "x": TREND_DIRECTION.get("shape", 0),
            "y": TREND_DIRECTION.get("age", 0),
            "size": TREND_DIRECTION.get("volume", 0),
        }
    except ImportError:
        return None


def _build_gap_analysis(
    current_coords: dict,
    aspiration_coords: dict,
    gap: dict,
    similar_types: list[dict],
    aspiration_interpretation: dict,
    report_content: dict,
    aspiration_anchor: Optional[dict] = None,
) -> dict:
    """gap_analysis 섹션 -- standard 잠금."""
    magnitude = gap.get("magnitude", 0)
    gap_diff = _gap_difficulty(magnitude)
    gap_vector = gap.get("vector", {})

    # 현재 유형: 가장 유사한 유형에서 가져오기
    current_type = "알 수 없음"
    current_type_id = 0
    if similar_types and len(similar_types) > 0:
        current_type = similar_types[0].get("name_kr", "알 수 없음")
        current_type_id = similar_types[0].get("type_id", 0)

    # 추구 유형: 파이프라인 상류에서 확정된 앵커 사용 (문자열 매칭 불필요)
    if aspiration_anchor:
        aspiration_type = aspiration_anchor.get("name_kr", "")
        aspiration_type_id = aspiration_anchor.get("type_id", 0)
        aspiration_description = aspiration_anchor.get("description_kr", "")
    else:
        # fallback: LLM 해석에서 이름만 가져오기 (type_id 미확정)
        aspiration_type = _safe_get(aspiration_interpretation, "reference_base", "")
        aspiration_type_id = 0
        aspiration_description = ""

    # description_kr → bullet 리스트 분리
    aspiration_features: list[str] = []
    if aspiration_description:
        raw = aspiration_description.replace(". ", ", ")
        aspiration_features = [
            s.strip().rstrip(".") for s in raw.split(", ") if s.strip()
        ]

    # 갭 요약 생성 — AXIS_LABELS 기준 라벨 사용 (coordinate.py 라벨 무시)
    primary_dir = gap.get("primary_direction", "")
    secondary_dir = gap.get("secondary_direction", "")

    primary_delta_val = gap_vector.get(primary_dir, 0)
    secondary_delta_val = gap_vector.get(secondary_dir, 0)

    # AXIS_LABELS에서 방향 라벨 직접 조회 (SSOT)
    primary_ax = AXIS_LABELS.get(primary_dir, {})
    primary_shift_kr = primary_ax.get("high") if primary_delta_val > 0 else primary_ax.get("low", "")
    secondary_ax = AXIS_LABELS.get(secondary_dir, {})
    secondary_shift_kr = secondary_ax.get("high") if secondary_delta_val > 0 else secondary_ax.get("low", "")

    gap_summary = f"가장 큰 변화는 더 {primary_shift_kr} 방향으로 가는 거예요."
    if secondary_shift_kr and secondary_dir != primary_dir and abs(secondary_delta_val) > 0.1:
        gap_summary += f" 그리고 전체적으로 더 {secondary_shift_kr} 느낌으로요."

    # direction_items 생성
    direction_items = []
    sorted_axes = sorted(gap_vector.items(), key=lambda x: abs(x[1]), reverse=True)

    for axis_name, delta_val in sorted_axes:
        ax_labels = AXIS_LABELS.get(axis_name, {})
        from_score = max(-1.0, min(1.0, float(current_coords.get(axis_name, 0) or 0)))
        to_score = max(-1.0, min(1.0, float(aspiration_coords.get(axis_name, 0) or 0)))
        from_label = get_position_label(axis_name, from_score)

        # delta 작으면 "거의 일치", 아니면 목표 방향 명시
        if abs(delta_val) < 0.15:
            to_label = "거의 일치"
            axis_diff = "거의 일치"
            name_kr = ax_labels.get('name_kr', axis_name)
            recommendation = f"{name_kr}{_postposition(name_kr, '은', '는')} 현재와 추구미가 거의 같아요. 지금 방향 그대로 좋아요."
        else:
            # "중간" 대신 이동 방향으로 표시 (예: "프레시 방향으로")
            target_direction = ax_labels.get("high", "") if delta_val > 0 else ax_labels.get("low", "")
            to_label = f"{target_direction} 방향으로"
            axis_diff = _axis_difficulty(delta_val)
            recommendation = build_gap_recommendation(axis_name, delta_val)

        direction_items.append({
            "axis": axis_name,
            "label": ax_labels.get("name_kr", axis_name),
            "name_kr": ax_labels.get("name_kr", axis_name),
            "label_low": ax_labels.get("low", ""),
            "label_high": ax_labels.get("high", ""),
            "axis_description": ax_labels.get("description", ""),
            "from_score": round(from_score, 2),
            "to_score": round(to_score, 2),
            "delta": round(abs(delta_val), 2),
            "from_label": from_label,
            "to_label": to_label,
            "difficulty": axis_diff,
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
            "aspiration_description": aspiration_description,
            "aspiration_features": aspiration_features,
            "current_coordinates": {k: round(v, 2) for k, v in current_coords.items()},
            "aspiration_coordinates": {k: round(v, 2) for k, v in aspiration_coords.items()},
            "gap_magnitude": round(magnitude, 2),
            "gap_difficulty": gap_diff,
            "gap_summary": gap_summary,
            "direction_items": direction_items,
            # aesthetic_map -- 2D 시각화용 고정 좌표계
            "aesthetic_map": {
                "current": {
                    "x": round(float(current_coords.get("shape", 0)), 2),
                    "y": round(float(current_coords.get("age", 0)), 2),
                    "size": round(float(current_coords.get("volume", 0)), 2),
                },
                "aspiration": {
                    "x": round(float(aspiration_coords.get("shape", 0)), 2),
                    "y": round(float(aspiration_coords.get("age", 0)), 2),
                    "size": round(float(aspiration_coords.get("volume", 0)), 2),
                },
                "x_axis": _get_raw_axis_labels("shape"),
                "y_axis": _get_raw_axis_labels("age"),
                "size_axis": _get_raw_axis_labels("volume"),
                "quadrants": {
                    "top_left": "Soft Mature",
                    "top_right": "Sharp Mature",
                    "bottom_left": "Soft Fresh",
                    "bottom_right": "Sharp Fresh",
                },
                "description": "가로축은 골격의 형태, 세로축은 분위기의 방향이에요. 점이 클수록 이목구비 선명도가 높아요.",
            },
            # 트렌드 방향 좌표 (산점도 3번째 점)
            "trend": _get_trend_point(),
        },
    }


# ─────────────────────────────────────────────
#  헤어 레퍼런스 이미지 로더
# ─────────────────────────────────────────────

_HAIR_STYLES_PATH = Path(__file__).parent.parent / "data" / "hair_styles.json"
_hair_styles_cache: dict | None = None


def _load_hair_styles() -> dict:
    """hair_styles.json 로드 (캐시)."""
    global _hair_styles_cache
    if _hair_styles_cache is None:
        with open(_HAIR_STYLES_PATH, encoding="utf-8") as f:
            _hair_styles_cache = json.load(f)
    return _hair_styles_cache


def _build_hair_recommendation(
    gap: dict,
    report_content: dict,
    gender: str = "female",
) -> dict:
    """hair_recommendation 섹션 — ₩49K 잠금.

    AI 레퍼런스 이미지 기반 헤어 추천.
    파이널폼 v5: p7 TOP 3 조합 + p8~11 심화/AVOID.

    Gender-aware pool selection (2026-04-21 Phase B gap 5):
      - female: hair_styles.json 의 front_styles (8) + back_styles (13) 조합 pool
      - male:   hair_styles.json 의 male_styles (12) 단일 pool. build_hair_spec
                이 생성한 mono combo (back_id=None) 를 front 슬롯에만 채우고
                back=None 으로 반환. 프론트엔드는 back 이 None 이면 단일 style
                렌더링으로 처리.
    """
    styles = _load_hair_styles()

    # Gender 별 pool/catalog 결정 — silent female default 차단
    if gender == "male":
        male_list = styles.get("male_styles", [])
        pool = {s["id"]: s for s in male_list}
        catalog = {"male": list(pool.values())}
    else:
        front_styles = {s["id"]: s for s in styles.get("front_styles", [])}
        back_styles = {s["id"]: s for s in styles.get("back_styles", [])}
        # 통합 lookup pool (front + back id 가 유니크하므로 merge 가능)
        pool = {**front_styles, **back_styles}
        catalog = {
            "front": list(front_styles.values()),
            "back": list(back_styles.values()),
        }

    # LLM report_content에서 헤어 관련 데이터 추출
    hair_data = report_content.get("hair_recommendation", {})
    cheat_sheet = hair_data.get("cheat_sheet", "")
    raw_combos = hair_data.get("top_combos", [])
    raw_avoids = hair_data.get("avoid", [])

    # 스코어 정규화: raw score(1.0 초과 가능) → 0.80~0.99 범위로 매핑
    if raw_combos:
        raw_scores = [c.get("combined_score", 0) for c in raw_combos[:3]]
        max_raw = max(raw_scores) if raw_scores else 1.0
        min_raw = min(raw_scores) if len(raw_scores) > 1 else max_raw - 0.1
        score_range = max(max_raw - min_raw, 0.01)  # 0 나누기 방지

    # TOP 3 조합 빌드 — hair_spec 엔진 출력 직접 소비
    top_combos = []
    for combo in raw_combos[:3]:
        front_id = combo.get("front_id", "")
        back_id = combo.get("back_id")  # male: None / female: 문자열
        front = pool.get(front_id)
        # male mono combo: back_id=None → back=None. 프론트엔드는 None 체크로 분기.
        back = pool.get(back_id) if back_id else None

        # 스코어 정규화 (0.80~0.99)
        raw_s = combo.get("combined_score", 0)
        normalized = 0.80 + (raw_s - min_raw) / score_range * 0.19 if raw_combos else 0

        entry = {
            "rank": combo.get("rank", len(top_combos) + 1),
            "score": round(normalized, 2),
            "front": front,
            "back": back,
            "why": combo.get("why", ""),
            "axis_shift": combo.get("axis_shift", {}),
            "salon_instruction": combo.get("salon_instruction", ""),
            "trend": combo.get("trend"),
        }
        top_combos.append(entry)

    # AVOID 스타일 빌드 — gender 에 맞는 pool 에서만 조회 (다른 성별 id 섞임 방지)
    avoid_list = []
    for av in raw_avoids:
        style_id = av.get("style_id", "")
        style = pool.get(style_id)
        avoid_list.append({
            "style": style,
            "name_kr": av.get("name_kr", style["name_kr"] if style else ""),
            "reason": av.get("primary_reason") or av.get("reason", ""),
        })

    return {
        "id": "hair_recommendation",
        "locked": True,
        "unlock_level": "full",
        "teaser": {"headline": cheat_sheet[:60] + "..." if len(cheat_sheet) > 60 else cheat_sheet},
        "content": {
            "cheat_sheet": cheat_sheet,
            "top_combos": top_combos,
            "avoid": avoid_list,
            "catalog": catalog,
        },
    }


def _build_action_plan(
    gap: dict,
    face_features: dict,
    report_content: dict,
    gender: str = "female",
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

    # zone → 주요 기여 축 매핑 (어떤 축에 영향을 주는 zone인지)
    ZONE_AXIS_MAP = {
        "jawline": "shape", "cheekbone": "shape", "forehead": "shape",
        "under_eye": "shape", "brow": "shape", "brow_arch": "shape",
        "brow_tail": "shape", "eye_line": "shape", "outer_eye": "shape",
        "cheek_apple": "age", "mid_cheek": "age",
        "lip": "volume", "lip_center": "volume", "lip_corner": "volume",
        "nose_bridge": "volume", "nose_tip": "volume",
    }
    gap_vector = gap.get("vector", {})

    def _zone_effect_label(zone_raw: str) -> str:
        """zone의 주요 기여 축 + gap 방향 → 방향 태그 생성."""
        axis = ZONE_AXIS_MAP.get(zone_raw)
        if axis and axis in gap_vector:
            delta = gap_vector[axis]
            ax = AXIS_LABELS.get(axis, {})
            direction = ax.get("high") if delta > 0 else ax.get("low")
            name_kr = ax.get("name_kr", axis)
            if direction:
                return f"더 {direction} {name_kr}으로"
        # SSOT 폴백: primary 축의 AXIS_LABELS 라벨
        p_dir = gap.get("primary_direction", "")
        p_delta = gap_vector.get(p_dir, 0)
        p_ax = AXIS_LABELS.get(p_dir, {})
        p_label = p_ax.get("high") if p_delta > 0 else p_ax.get("low", "")
        return f"더 {p_label} 느낌으로"

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
            "expected_effect": _zone_effect_label(cat_raw),
        })

    items = list(category_map.values())

    # 폴백: LLM이 빈 결과를 줬을 때 기본 카테고리 생성
    if not items:
        _p_dir = gap.get("primary_direction", "")
        _p_delta = gap_vector.get(_p_dir, 0)
        _p_ax = AXIS_LABELS.get(_p_dir, {})
        shift_kr = _p_ax.get("high") if _p_delta > 0 else _p_ax.get("low", "")
        if gender == "male":
            items = [
                {
                    "category": "헤어스타일",
                    "priority": "핵심 포인트",
                    "recommendations": [{"action": "헤어 스타일링으로 전체 인상을 조정해보세요.", "expected_effect": f"더 {shift_kr} 느낌으로"}],
                },
                {
                    "category": "그루밍",
                    "priority": "핵심 포인트",
                    "recommendations": [{"action": "눈썹과 수염 정리로 인상을 다듬어보세요.", "expected_effect": f"더 {shift_kr} 느낌으로"}],
                },
                {
                    "category": "체형 관리",
                    "priority": "추가하면 좋은 포인트",
                    "recommendations": [{"action": "체형 관리로 전체 인상의 밸런스를 맞춰보세요.", "expected_effect": f"더 {shift_kr} 느낌으로"}],
                },
                {
                    "category": "스킨케어",
                    "priority": "추가하면 좋은 포인트",
                    "recommendations": [{"action": "피부 관리로 전체 분위기를 마무리해보세요.", "expected_effect": "전체 조화"}],
                },
            ]
        else:
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


def build_why_this_type(current_type: str, match_score: float, axis_values: dict) -> list[str]:
    """WHY THIS TYPE 3 bullet 구조 — LLM placeholder 방지용 deterministic fallback."""
    bullets = []
    if match_score >= 0.8:
        bullets.append(f"전체적인 얼굴 구조가 '{current_type}' 유형과 높은 유사성을 보여요.")
    else:
        bullets.append(f"얼굴 구조의 주요 특징이 '{current_type}' 유형 경향과 맞아요.")

    if axis_values:
        strongest_axis = max(axis_values.items(), key=lambda x: abs(x[1]))
        ax = AXIS_LABELS.get(strongest_axis[0], {})
        axis_name = ax.get("name_kr", strongest_axis[0])
        direction = ax.get("high", "") if strongest_axis[1] > 0 else ax.get("low", "")
        bullets.append(f"{axis_name} 축에서 {direction} 쪽 경향이 뚜렷해요.")

    bullets.append("현재 이미지의 비율, 각도, 인상이 이 유형의 전형적 특징과 잘 연결돼요.")
    return bullets


def _build_type_reference(
    similar_types: list[dict],
    report_content: dict,
    gap: dict = None,
    type_match_explanation: dict | None = None,
) -> dict:
    """type_reference 섹션 -- full 잠금.

    Phase B-3 (PI-REVIVE 2026-04-26):
      type_match_explanation 가 dict 이고 reasons/styling_tips 비어있지
      않으면 LLM 동적 생성 결과 PRIMARY 사용. 비어있으면 기존 deterministic
      fallback (build_why_this_type / build_type_styling_tips) 그대로.
    """
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

    # Phase B-3: LLM type_match_explanation PRIMARY (vault-aware)
    reasons: list[str] = []
    styling_tips: list[str] = []
    if isinstance(type_match_explanation, dict):
        llm_reasons = type_match_explanation.get("reasons", [])
        llm_tips = type_match_explanation.get("styling_tips", [])
        if isinstance(llm_reasons, list):
            reasons = [r for r in llm_reasons if isinstance(r, str) and r.strip()]
        if isinstance(llm_tips, list):
            styling_tips = [t for t in llm_tips if isinstance(t, str) and t.strip()]

    # 보조: 기존 generate_report 의 similar_types 영역 (placeholder 가능성)
    if not reasons:
        llm_similar = _safe_get(report_content, "similar_types", [])
        if llm_similar:
            first_llm = llm_similar[0] if isinstance(llm_similar, list) and llm_similar else {}
            reasons = first_llm.get("reason", "").split(", ") if isinstance(first_llm.get("reason"), str) else []
            if not reasons:
                reasons = [first_llm.get("reason", "")] if first_llm.get("reason") else []
            styling_insight = first_llm.get("styling_insight", "")
            if styling_insight and not styling_tips:
                styling_tips.append(styling_insight)

    # bracket placeholder 감지 → deterministic fallback
    has_bracket = any("[" in r or "]" in r for r in reasons)
    if not reasons or has_bracket:
        match_score = similarity_pct / 100.0
        axis_values = primary.get("axis_delta", {})
        reasons = build_why_this_type(type_name, match_score, axis_values)

    # styling_tips deterministic 폴백
    if not styling_tips and gap:
        gap_vector = gap.get("vector", {})
        primary_dir = gap.get("primary_direction", "shape")
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


def _build_trend_context(
    report_content: dict,
    user_name: str = "",
    aspiration_coords: dict | None = None,
    action_spec=None,
) -> dict:
    """trend_context 섹션 -- full 잠금. trend_data.py 기반 deterministic."""
    from pipeline.trend_data import (
        TREND_SEASON, TREND_DIRECTION, TREND_MOODS,
        MAKEUP_TRENDS, COLOR_PARADIGM,
    )
    import math

    name = user_name or "고객"
    aspiration = aspiration_coords or {}

    # 1) 유저 추구미 ↔ 트렌드 방향 거리 → 정합도
    trend_vec = TREND_DIRECTION
    dist = math.sqrt(sum(
        (aspiration.get(ax, 0) - trend_vec.get(ax, 0)) ** 2
        for ax in ["shape", "volume", "age"]
    )) if aspiration else 999

    if dist < 0.3:
        alignment = "aligned"
        alignment_kr = "트렌드와 잘 맞아요"
        alignment_desc = f"{name}님의 추구미는 이번 시즌 트렌드와 방향이 비슷해요. 자연스럽게 트렌드를 타면서 나다운 스타일을 만들 수 있어요."
    elif dist < 0.7:
        alignment = "neutral"
        alignment_kr = "트렌드와 일부 겹쳐요"
        alignment_desc = f"{name}님의 추구미는 트렌드와 일부 방향이 같아요. 맞는 부분은 살리고, 다른 부분은 그대로 유지하는 게 자연스러워요."
    else:
        alignment = "divergent"
        alignment_kr = "트렌드와 다른 방향이에요"
        alignment_desc = f"{name}님의 추구미는 이번 시즌 주류 트렌드와 다른 방향이에요. 그게 오히려 개성이고, 얼굴형에 맞는 게 트렌드보다 항상 우선이에요."

    # 2) 가장 가까운 TREND_MOOD 매칭 (유클리드)
    best_mood_id, best_mood = "", {}
    best_dist = 999
    for mood_id, mood in TREND_MOODS.items():
        mc = mood.get("coordinates", {})
        d = math.sqrt(sum(
            (aspiration.get(ax, 0) - mc.get(ax, 0)) ** 2
            for ax in ["shape", "volume", "age"]
        )) if aspiration else 999
        if d < best_dist:
            best_dist = d
            best_mood_id = mood_id
            best_mood = mood

    # 3) action_spec 추천 vs 트렌드 사후 태깅
    action_tags = []
    if action_spec and hasattr(action_spec, "recommended_actions"):
        for action in action_spec.recommended_actions[:4]:
            zone = action.zone
            zone_kr = ZONE_NAME_KR.get(zone, zone)
            makeup_zone = MAKEUP_TRENDS.get(zone, {})
            rising = makeup_zone.get("rising", [])
            declining = makeup_zone.get("declining", [])
            # 존에 트렌드 데이터가 있으면 태깅
            if rising or declining:
                action_tags.append({
                    "zone": zone,
                    "zone_kr": zone_kr,
                    "rising_top": [r.split(" (")[0].split("（")[0].strip() for r in rising[:2]] if rising else [],
                    "declining_top": [d.split(" (")[0].split("（")[0].strip() for d in declining[:1]] if declining else [],
                })

    # 4) 메이크업 트렌드 존별 요약
    def _short_label(s: str) -> str:
        """괄호 설명 제거: '자연눈썹/결살/플러피 (설명...)' → '자연눈썹/결살/플러피'"""
        import re
        return re.sub(r"\s*[\(（].*?[\)）]", "", s).strip()

    makeup_summary = []
    for zone_key in ["eyebrow", "eye", "lip", "base"]:
        zone_data = MAKEUP_TRENDS.get(zone_key, {})
        if zone_data.get("summary"):
            zone_names = {"eyebrow": "눈썹", "eye": "아이", "lip": "립", "base": "베이스"}
            makeup_summary.append({
                "zone": zone_key,
                "zone_kr": zone_names.get(zone_key, zone_key),
                "rising": [_short_label(r) for r in zone_data.get("rising", [])[:2]],
                "declining": [_short_label(d) for d in zone_data.get("declining", [])[:1]],
                "summary": zone_data["summary"],
            })

    return {
        "id": "trend_context",
        "locked": True,
        "unlock_level": "full",
        "teaser": {"headline": f"2026 S/S · {alignment_kr}"},
        "content": {
            "season": TREND_SEASON,
            "season_summary": trend_vec.get("summary_kr", ""),
            "trend_direction": {
                "shape": trend_vec.get("shape", 0),
                "volume": trend_vec.get("volume", 0),
                "age": trend_vec.get("age", 0),
            },
            "alignment": alignment,
            "alignment_kr": alignment_kr,
            "alignment_description": alignment_desc,
            "matched_mood": {
                "id": best_mood_id,
                "label_kr": best_mood.get("label_kr", ""),
                "description": best_mood.get("description", ""),
                "keywords": best_mood.get("keywords", []),
                "trend_score": best_mood.get("trend_score", 0),
            } if best_mood else None,
            "action_trend_tags": action_tags,
            "makeup_trends": makeup_summary,
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
    aspiration_anchor: Optional[dict] = None,
    type_match_explanation: Optional[dict] = None,
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
        current_coords: 현재 미감 3축 좌표 (shape/volume/age)
        aspiration_coords: 추구미 3축 좌표 (shape/volume/age)
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
        _build_face_structure(face_features, face_interpretation),
        _build_skin_analysis(face_features),
        _build_gap_analysis(
            current_coords, aspiration_coords, gap,
            similar_types, aspiration_interpretation, report_content,
            aspiration_anchor=aspiration_anchor,
        ),
        _build_hair_recommendation(gap, report_content, gender=gender),
        _build_action_plan(gap, face_features, report_content, gender=gender),
        _build_type_reference(similar_types, report_content, gap=gap, type_match_explanation=type_match_explanation),
        _build_trend_context(report_content, user_name=user_name, aspiration_coords=aspiration_coords),
    ]

    result = {
        "id": report_id,
        "user_id": user_id,
        "user_name": user_name,
        "access_level": "free",
        "pending_level": None,
        "sections": sections,
        "paywall": {
            "standard": {
                "price": 2900,
                "original_price": 5000,
                "label": "\u20A92,900 잠금 해제",
                "method": "manual",
            },
            "full": {
                "price": 26100,
                "original_price": 44000,
                "label": "+\u20A926,100 잠금 해제",
                "total_note": "이전 결제 포함 총 \u20A929,000",
                "method": "manual",
            },
        },
        "payment_account": {
            "bank": "우체국",
            "number": "120-0001-11506",
            "holder": "주식회사시각",
            "kakao_link": "kakaotalk://send?amount={amount}&bank=epost&account=120000111506",
        },
    }

    # numpy 타입 → Python 네이티브 변환 (FastAPI JSON 직렬화용)
    return _sanitize(result)
