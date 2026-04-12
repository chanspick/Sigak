"""
SIGAK Hair Rule Tables
======================
레어리 헤어 보고서 37페이지에서 추출한 의사결정 로직을
룰 기반 스코어링 테이블로 구조화.

스코어링 구조:
  final_score = base_score (0.5)
              + Σ feature_modifiers (해당하는 것만)
              + cross_effect (앞×뒤 조합 시)

  rating = 3 if score >= 0.7
           2 if score >= 0.45
           1 if score < 0.45
"""

# ============================================================
# 1. FEATURE MODIFIERS
# ============================================================

FEATURE_MODIFIERS = {

    # ── 짧고 넓은 얼굴 ──
    "face_wide_short": {
        "h-f01": {"mod": -0.3, "reason": "이마 가리면 얼굴 더 짧고 넙데데해 보임"},
        "h-f02": {
            "mod": +0.1,
            "reason": "이마 부분 노출로 넙데데함 완화",
            "conditions": [{
                "if_field": "hair_volume",
                "if_value": "high",
                "then_mod": -0.2,
                "rescue": "숱을 매우 적게 내거나, 귀 뒤로 꽂거나, 묶고 내리기",
                "rescue_mod": +0.15,
            }],
        },
        "h-f03": {"mod": -0.05, "reason": "좌우 커버 가능하나 대칭이라 턱 부각 가능"},
        "h-f04": {"mod": +0.2, "reason": "비대칭으로 좌우골격 자연스럽게 커버, 얼굴 갸름해 보임"},
        "h-f05": {"mod": +0.1, "reason": "한쪽 광대+옆턱 라인 완전 커버, 얼굴 작아 보임"},
        "h-f06": {
            "mod": +0.15,
            "reason": "화려한 앞머리로 시선 상향, 넙데데함 완화",
            "conditions": [{
                "if_field": "forehead_coverage_heavy",
                "if_value": True,
                "then_mod": -0.1,
                "rescue": "숱을 적게 내어 이마 중간 드러내면서 애교머리처럼 스타일링",
                "rescue_mod": +0.1,
            }],
        },
        "h-f07": {"mod": -0.1, "reason": "짧은 앞머리가 얼굴 더 넙데데해 보이게 할 수 있음"},
        "h-f08": {"mod": -0.05, "reason": "앞머리 없으면 시선이 하관으로 쏠림"},
        "h-b01": {"mod": -0.05, "reason": "골격 대비 없어 밋밋할 수 있음"},
        "h-b02": {"mod": +0.2, "reason": "하관 옆 무게감 최소, 답답함 최소화"},
        "h-b03": {"mod": +0.05, "reason": "뿌리볼륨 전제 하에 어울림"},
        "h-b04": {"mod": -0.1, "reason": "턱 주변 컬로 답답해질 수 있음"},
        "h-b05": {"mod": -0.3, "reason": "좌우 넙데데함 극대화"},
        "h-b06": {"mod": -0.2, "reason": "일자 라인이 넙데데함 강조, 사각턱 부각"},
        "h-b07": {"mod": +0.2, "reason": "하관 주변 무게감 가벼워 시원해 보임"},
        "h-b08": {"mod": +0.1, "reason": "턱끝 C컬로 시선 분산, 골격 대비 감소"},
        "h-b09": {"mod": -0.3, "reason": "턱 주변 무게감+목 가림으로 답답함 극대화"},
        "h-b10": {"mod": +0.05, "reason": "기장감 길면 세로 비율 보완 가능"},
        "h-b11": {"mod": +0.05, "reason": "기장감으로 보완 가능하나 컬 주의"},
        "h-b12": {"mod": +0.2, "reason": "레이어드로 가벼움 + 기장감 보완"},
        "h-b13": {"mod": -0.2, "reason": "부피 과다, 체구 대비 머리 커 보임"},
        "h-e02": {"mod": +0.2, "reason": "묶으면 얼굴 가장 갸름해 보임, 짧은 얼굴에 세로 볼륨"},
        "h-e03": {"mod": -0.05, "reason": "양갈래가 얼굴 더 넓어 보이게 함"},
    },

    # ── 짧은 이마 ──
    "short_forehead": {
        "h-f01": {"mod": -0.2, "reason": "이마를 빽빽하게 가리면 하관이 더 부해 보이고 답답함"},
        "h-f02": {"mod": +0.1, "reason": "이마 부분 노출 가능"},
        "h-f03": {"mod": -0.05, "reason": "5:5보다 비대칭이 더 시원해 보임"},
        "h-f04": {"mod": +0.1, "reason": "비대칭이 시원함, 뿌리볼륨 살리기 좋음"},
        "h-f06": {"mod": +0.1, "reason": "숱 적게 내어 이마 중간 드러내면 효과적"},
        "h-b03": {
            "mod": 0,
            "reason": "뿌리볼륨 없으면 바로 답답",
            "conditions": [{
                "if_field": "_root_volume",
                "if_value": False,
                "then_mod": -0.2,
                "rescue": "뿌리볼륨에 특히 집중",
                "rescue_mod": +0.15,
            }],
        },
        "h-b04": {"mod": -0.1, "reason": "하관 컬감이 답답함 강화"},
        "h-b05": {"mod": -0.15, "reason": "턱 주변 무게감으로 이마 더 좁아 보임"},
        "h-b09": {"mod": -0.15, "reason": "턱 주변 무게감 쌓여 답답"},
        "_global": {
            "root_volume_required": True,
            "root_volume_reason": "이마가 짧아 뿌리볼륨 없으면 하관이 부해 보임",
            "root_volume_instruction": "이마 바로 위 헤어라인쪽 뿌리볼륨을 특히 신경써서 확실히 살리기",
        },
    },

    # ── 긴 중안부 ──
    "long_midface": {
        "h-f01": {"mod": -0.1, "reason": "눈썹 가리고 코를 대비시켜 더 크고 길어 보이게 부각"},
        "h-f02": {"mod": +0.1, "reason": "코끝으로 가는 시선을 눈으로 분산"},
        "h-f03": {"mod": +0.05, "reason": "중안부 여백 커버 가능"},
        "h-f04": {"mod": +0.05, "reason": "중안부 여백 일부 커버"},
        "h-f08": {"mod": -0.05, "reason": "5:5 가르마 시 중안부, 코 가장 길어 보임"},
    },

    # ── 긴 인중 ──
    "long_philtrum": {
        "h-f01": {"mod": -0.05, "reason": "눈썹기장 빽빽한 앞머리가 코~인중 대비 강화"},
        "h-f02": {"mod": +0.05, "reason": "기장감 눈썹보다 길게 내면 인중 시선 분산"},
        "h-f06": {"mod": +0.1, "reason": "화려한 디자인이 인중으로 가는 시선을 위로 끌어올림"},
    },

    # ── 사각턱 골격 ──
    "square_jaw": {
        "h-f03": {"mod": -0.1, "reason": "대칭 가르마가 턱 골격 더 부각"},
        "h-f04": {"mod": +0.2, "reason": "비대칭이라 턱 부각 덜함"},
        "h-f05": {"mod": +0.1, "reason": "한쪽 턱선 커버"},
        "h-b02": {"mod": +0.15, "reason": "층으로 턱 옆 무게감 감소"},
        "h-b03": {"mod": -0.05, "reason": "일자 끝단이 턱선과 대비"},
        "h-b06": {"mod": -0.15, "reason": "일자 라인이 턱 각져 보이게 대비"},
        "h-b07": {"mod": +0.15, "reason": "레이어드로 하관 가벼움"},
        "h-b09": {"mod": -0.15, "reason": "컬감이 턱 더 각져 보이고 넙데데하게"},
        "h-b12": {"mod": +0.15, "reason": "레이어드로 턱 아래 무게감 감소"},
        "_parting": {"symmetric_penalty": -0.1, "reason": "5:5 가르마 비추, 비대칭 권장"},
    },

    # ── 입돌출 ──
    "mouth_protrusion": {
        "h-f01": {"mod": -0.1, "reason": "이마 가리면 남은 얼굴에서 돌출입 강조, 하관 답답"},
        "h-f04": {"mod": +0.1, "reason": "앞머리로 돌출입 시선 분산, 투박함 보완"},
        "h-f06": {"mod": +0.1, "reason": "화려한 앞머리로 시선 위로"},
        "h-f08": {"mod": -0.1, "reason": "앞머리 없으면 시선이 하관으로 쏠림"},
        "h-b04": {
            "mod": -0.05,
            "reason": "컬감 많으면 입 부각",
            "conditions": [{
                "if_field": "curl_at_jaw_heavy",
                "if_value": True,
                "then_mod": -0.15,
                "rescue": "반묶음으로 무게감 줄이기",
                "rescue_mod": +0.1,
            }],
        },
        "h-b12": {"mod": +0.1, "reason": "레이어드컷이 하관 무거운 느낌 완화"},
        "h-e02": {"mod": +0.15, "reason": "정수리 부피감이 시선 위로 올림"},
    },

    # ── 큰 코 ──
    "large_nose": {
        "h-f01": {"mod": -0.15, "reason": "눈썹 가리고 코 대비시켜 코 자체를 더 부각"},
        "h-f02": {"mod": +0.1, "reason": "시선을 눈으로 분산"},
        "h-f06": {"mod": +0.1, "reason": "화려한 앞머리로 시선 상향"},
        "h-f08": {"mod": -0.05, "reason": "코로 시선 직행"},
    },

    # ── 짧은 목 ──
    "short_neck": {
        "h-f05": {
            "mod": 0, "reason": "기장 주의 필요",
            "conditions": [{
                "if_field": "bangs_length_over_chin",
                "if_value": True,
                "then_mod": -0.15,
                "rescue": "앞턱 끝보다 기장이 과하게 길어지지 않도록",
                "rescue_mod": +0.1,
            }],
        },
        "h-b02": {"mod": +0.05, "reason": "짧은 기장이 목선 노출"},
        "h-b04": {"mod": -0.05, "reason": "목 주변 컬감 답답"},
        "h-b06": {"mod": -0.1, "reason": "목 더 가늘어 보이게 해 넙데데함 강조"},
        "h-b08": {
            "mod": +0.1, "reason": "충분히 긴 기장감이 목 길이 늘림",
            "conditions": [{
                "if_field": "length_too_short",
                "if_value": True,
                "then_mod": -0.1,
                "rescue": "쇄골보다 1-3cm 더 넉넉한 기장",
                "rescue_mod": +0.1,
            }],
        },
        "h-b09": {"mod": -0.2, "reason": "목 가림 + 부피로 답답함 극대화"},
        "h-b11": {
            "mod": 0, "reason": "목 주변 컬 제한 필요",
            "conditions": [{
                "constraint": "curl_at_neck_max",
                "max_intensity": "light_c",
                "reason": "목 주변엔 컬감 거의 없이 늘어지도록 아주 굵게",
            }],
        },
        "h-b12": {
            "mod": +0.05, "reason": "레이어드로 가벼우나 C컬 레이어드 위치 주의",
            "conditions": [{
                "constraint": "layered_min_position",
                "min_position": "clavicle_minus_3cm",
                "reason": "C컬에 한해 쇄골보다 적어도 2-3cm 아래에 레이어드",
            }],
        },
        "h-b13": {"mod": -0.2, "reason": "목 주변 부피감 큰 디자인, 답답함 확실"},
        "h-e02": {"mod": +0.15, "reason": "높게 묶으면 목선 길어보이고 답답함 해소"},
    },

    # ── 좁은 어깨 ──
    "narrow_shoulders": {
        "h-b05": {"mod": -0.1, "reason": "머리 부피 > 체구, 얼굴 커 보이고 비율 안 좋음"},
        "h-b13": {"mod": -0.1, "reason": "머리 부피 > 체구, 비율 안 좋음"},
        "h-e02": {
            "mod": 0, "reason": "타이트 올백 시 비율 안 좋을 수 있음",
            "conditions": [{
                "if_field": "tight_slick_back",
                "if_value": True,
                "then_mod": -0.1,
                "rescue": "뿌리볼륨 살리거나 시스루뱅/잔머리로 헤어라인 커버하고 묶기",
                "rescue_mod": +0.1,
            }],
        },
    },

    # ── 옆광대 없음 ──
    "no_cheekbone": {},
}


# ============================================================
# 2. LENGTH CONSTRAINTS
# ============================================================

LENGTH_CONSTRAINTS = {
    "h-f04": {
        "min_length": "lip_line",
        "reason": "기장감이 입술선보다 길면 무리 없이 어울림",
    },
    "h-f05": {
        "default_max": "chin_tip",
        "if_short_neck": "chin_tip_strict",
        "salon_note": "앞턱 끝보다 기장이 과하게 길어지지 않도록 주의",
    },
    "h-b02": {
        "default_max": "mid_neck",
        "if_short_neck": "jawline_to_mid_neck",
        "salon_note": "목 중간보다 길어지지 않도록",
    },
    "h-b03": {
        "default": "jawline",
        "tolerance": "+slight",
        "salon_note": "기장감은 턱선이나 그보다 미미하게 긴 정도",
    },
    "h-b08": {
        "default_min": "clavicle",
        "if_short_neck": "clavicle_plus_3cm",
        "curl_note": "쇄골 기장에서는 인컬이 아닌 아웃컬이 더 어울림",
        "salon_note": "쇄골보다 적어도 1-3cm 더 넉넉한 기장 권장",
    },
    "h-b10": {
        "recommended": "chest_line",
        "if_face_short": "chest_line_strict",
        "salon_note": "얼굴 짧은 편이라 쇄골보다 가슴선 근처로 확 길게",
    },
    "h-b11": {
        "recommended": "chest_line",
        "curl_max_at_neck": "light_c",
        "salon_note": "기장감은 가슴선에 가깝게, 목 주변 컬은 아주 굵게만",
    },
    "h-b12": {
        "recommended": "chest_line",
        "layered_min": "clavicle_plus_3cm",
        "c_curl_layered_min": "clavicle_plus_5cm",
        "salon_note": "C컬은 쇄골보다 2-3cm 아래에 레이어드, 목 주변 컬 아주 굵게",
    },
}


# ============================================================
# 3. CROSS EFFECTS
# ============================================================

CROSS_EFFECTS = {
    ("h-f08", "long"): {
        "mod": -0.1,
        "reason": "앞머리 없이 긴머리는 하관이 대비되어 시선 하향",
        "rescue": "중단발 이상에서는 앞머리 디자인 있는 것이 더 좋음",
    },
    ("h-f08", "mid"): {
        "mod": -0.05,
        "reason": "중단발에서도 앞머리 있는 것이 시선 분산에 유리",
    },
    ("h-f01", "heavy_curl"): {
        "mod": -0.1,
        "reason": "앞뒤 모두 무거워 답답함 극대화",
    },
    ("h-f04", "layered"): {
        "mod": +0.05,
        "reason": "비대칭 앞머리 + 가벼운 뒷머리 = 시원하고 세련된 조화",
    },
}


def match_cross_effect(front_style, back_style, all_styles):
    """앞×뒤 조합 시너지/페널티 계산."""
    total_mod = 0.0
    reasons = []

    for (front_pattern, back_pattern), effect in CROSS_EFFECTS.items():
        front_match = False
        back_match = False

        if front_pattern.startswith("h-f"):
            front_match = (front_style["id"] == front_pattern)

        if back_pattern.startswith("h-b"):
            back_match = (back_style["id"] == back_pattern)
        elif back_pattern == "long":
            back_match = (back_style.get("length_category") == "long")
        elif back_pattern == "mid":
            back_match = (back_style.get("length_category") == "mid")
        elif back_pattern == "heavy_curl":
            back_match = back_style.get("curl_intensity") in ("heavy_s", "hippy")
        elif back_pattern == "layered":
            back_match = back_style.get("has_layers", False)

        if front_match and back_match:
            total_mod += effect["mod"]
            reasons.append(effect["reason"])

    return total_mod, reasons


# ============================================================
# 4. IMAGE VECTOR MATCHING
# ============================================================

IMAGE_AXES = ["러블리", "청순", "도도/시크", "우아/차분", "개성"]

KEYWORD_TO_AXIS = {
    "러블리": 0, "귀여운": 0, "사랑스러운": 0, "여리여리": 0, "lovely": 0,
    "청순": 1, "깨끗한": 1, "순수한": 1, "내추럴": 1, "innocent": 1, "natural": 1,
    "시크": 2, "도도": 2, "쿨": 2, "세련된": 2, "모던": 2, "샤프": 2, "chic": 2, "modern": 2,
    "우아": 3, "차분": 3, "고급스러운": 3, "클래식": 3, "페미닌": 3, "elegant": 3,
    "개성": 4, "유니크": 4, "힙한": 4, "자유로운": 4, "보이시": 4, "unique": 4, "sexy": 4,
}


def match_image_preference(style_vector, user_desired_keywords):
    """이미지 벡터와 유저 키워드 매칭 → 보너스 (0~0.15)."""
    if not user_desired_keywords:
        return 0.0

    matched_axes = set()
    for kw in user_desired_keywords:
        kw_clean = kw.strip().replace("한", "").replace("하다", "")
        for key, axis_idx in KEYWORD_TO_AXIS.items():
            if key in kw_clean:
                matched_axes.add(axis_idx)

    if not matched_axes:
        return 0.0

    axis_scores = [style_vector[i] for i in matched_axes if i < len(style_vector)]
    if not axis_scores:
        return 0.0

    avg = sum(axis_scores) / len(axis_scores)
    return round(avg * 0.15, 3)
