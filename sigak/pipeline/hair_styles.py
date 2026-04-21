"""
SIGAK Hair Style Catalog
========================
Female: 8 앞머리(front) + 13 뒷머리(back) + 3 기타(etc) = 24 styles
Male:   12 complete styles (h-m01 ~ h-m12)

Gender-aware routing (2026-04-21 Phase B):
  - 각 style entry 의 `gender` 필드로 female/male 분기
  - `get_front_styles(gender)` / `get_back_styles(gender)` / `get_etc_styles(gender)`
    / `get_complete_styles(gender)` 는 gender 파라미터로 pool 선택
  - build_hair_spec 이 gender 전달받아 필터링
  - Female 은 front × back 조합 체계, Male 은 단일 complete cut 체계

Each style has:
- id, category, gender, name_kr, name_en
- description: 스타일 설명
- base_score: 0.5 (모든 스타일 동일 출발)
- curl_intensity: none/light_c/heavy_c/light_s/heavy_s/hippy
- has_layers: bool
- image_vector: [러블리, 청순, 도도시크, 우아차분, 개성] (0~1)
- gaze_effect: {blocks, attracts, diverts, covers, extends}  (female only — male 은 현재 미적용)
"""

HAIR_STYLES = {
    # ============================================================
    # FRONT STYLES (앞머리) — 8종
    # ============================================================
    "h-f01": {
        "id": "h-f01",
        "category": "front",
        "name_kr": "풀뱅",
        "name_en": "full_bang",
        "description": "이마가 전혀 보이지 않을 정도의 빽빽한 앞머리. 눈썹이나 그보다 살짝 긴 기장.",
        "base_score": 0.5,
        "curl_intensity": "none",
        "volume_at_jaw": "none",
        "forehead_coverage": 1.0,
        "image_vector": [0.8, 0.6, 0.2, 0.2, 0.4],
        "gaze_effect": {
            "blocks": ["forehead", "eyebrow"],
            "emphasizes": ["nose", "mouth", "midface"],
            "attracts": [],
            "diverts": [],
            "covers": [],
        },
    },
    "h-f02": {
        "id": "h-f02",
        "category": "front",
        "name_kr": "시스루뱅",
        "name_en": "see_through",
        "description": "이마가 30% 이상 드러나는 앞머리. 눈썹보다 살짝 긴 기장, 양끝이 더 길고 숱이 많아지는 형태.",
        "base_score": 0.5,
        "curl_intensity": "none",
        "volume_at_jaw": "none",
        "forehead_coverage": 0.7,
        "image_vector": [0.7, 0.7, 0.3, 0.3, 0.3],
        "gaze_effect": {
            "blocks": ["forehead_partial"],
            "emphasizes": [],
            "attracts": ["eyes"],
            "diverts": ["nose_tip"],
            "covers": [],
        },
    },
    "h-f03": {
        "id": "h-f03",
        "category": "front",
        "name_kr": "5:5 사이드뱅",
        "name_en": "symmetric_side",
        "description": "인중~입술 길이 앞머리, S컬 정가르마.",
        "base_score": 0.5,
        "curl_intensity": "light_s",
        "volume_at_jaw": "light",
        "forehead_coverage": 0.3,
        "image_vector": [0.4, 0.4, 0.6, 0.6, 0.4],
        "gaze_effect": {
            "blocks": [],
            "emphasizes": ["midface_center"],
            "attracts": ["eyes"],
            "diverts": ["philtrum"],
            "covers": ["partial_cheek_both"],
        },
    },
    "h-f04": {
        "id": "h-f04",
        "category": "front",
        "name_kr": "비대칭 사이드뱅",
        "name_en": "asymmetric_side",
        "description": "인중~입술 길이 앞머리, S컬 6:4~7:3 비대칭 가르마. 숱 적은 쪽은 귀 뒤로.",
        "base_score": 0.5,
        "curl_intensity": "light_s",
        "volume_at_jaw": "light",
        "forehead_coverage": 0.4,
        "image_vector": [0.4, 0.5, 0.6, 0.7, 0.4],
        "gaze_effect": {
            "blocks": [],
            "emphasizes": [],
            "attracts": ["eyes"],
            "diverts": ["mouth", "jaw"],
            "covers": ["one_side_jaw"],
        },
    },
    "h-f05": {
        "id": "h-f05",
        "category": "front",
        "name_kr": "턱선길이 사이드뱅",
        "name_en": "jawline_side",
        "description": "앞턱 끝 정도의 기장, 6:4~7:3 비대칭, 얼굴 한쪽 면을 감싸는 디자인.",
        "base_score": 0.5,
        "curl_intensity": "light_c",
        "volume_at_jaw": "medium",
        "forehead_coverage": 0.2,
        "image_vector": [0.3, 0.4, 0.7, 0.7, 0.3],
        "gaze_effect": {
            "blocks": [],
            "emphasizes": [],
            "attracts": [],
            "diverts": [],
            "covers": ["one_side_cheekbone", "one_side_jaw"],
        },
    },
    "h-f06": {
        "id": "h-f06",
        "category": "front",
        "name_kr": "컬리뱅",
        "name_en": "curly_bang",
        "description": "이마를 가리는 뱅 스타일에 잔컬. 기장 제한 없음. 짧을수록 러블리 강화.",
        "base_score": 0.5,
        "curl_intensity": "light_s",
        "volume_at_jaw": "none",
        "forehead_coverage": 0.6,
        "image_vector": [0.9, 0.4, 0.2, 0.2, 0.9],
        "gaze_effect": {
            "blocks": ["forehead_partial"],
            "emphasizes": [],
            "attracts": ["forehead_area"],
            "diverts": ["philtrum", "mouth"],
            "covers": [],
        },
    },
    "h-f07": {
        "id": "h-f07",
        "category": "front",
        "name_kr": "처피뱅",
        "name_en": "choppy_bang",
        "description": "눈썹 위로 오는 짧은 앞머리. 유니크하고 개성 강한 이미지.",
        "base_score": 0.5,
        "curl_intensity": "none",
        "volume_at_jaw": "none",
        "forehead_coverage": 0.5,
        "image_vector": [0.6, 0.3, 0.3, 0.2, 0.9],
        "gaze_effect": {
            "blocks": ["forehead_upper"],
            "emphasizes": ["face_width"],
            "attracts": ["forehead_area"],
            "diverts": [],
            "covers": [],
        },
    },
    "h-f08": {
        "id": "h-f08",
        "category": "front",
        "name_kr": "앞머리 없음",
        "name_en": "no_bangs",
        "description": "묶음머리/푼 머리 모두에서 앞머리가 없는 스타일.",
        "base_score": 0.5,
        "curl_intensity": "none",
        "volume_at_jaw": "none",
        "forehead_coverage": 0.0,
        "image_vector": [0.3, 0.5, 0.6, 0.7, 0.3],
        "gaze_effect": {
            "blocks": [],
            "emphasizes": ["midface", "nose", "mouth", "philtrum"],
            "attracts": [],
            "diverts": [],
            "covers": [],
        },
    },

    # ============================================================
    # BACK STYLES (뒷머리) — 13종
    # ============================================================
    "h-b01": {
        "id": "h-b01", "category": "back",
        "name_kr": "숏컷", "name_en": "short_cut",
        "description": "턱선보다 짧은 기장.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "short", "volume_at_jaw": "none", "volume_at_neck": "none",
        "image_vector": [0.2, 0.3, 0.7, 0.3, 0.6],
    },
    "h-b02": {
        "id": "h-b02", "category": "back",
        "name_kr": "보브단발/단발 레이어드컷", "name_en": "bob_layered",
        "description": "턱선 근처 단발, 끝단 층으로 둥근 형태.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": True,
        "length_category": "bob", "volume_at_jaw": "light", "volume_at_neck": "none",
        "image_vector": [0.4, 0.6, 0.7, 0.5, 0.4],
    },
    "h-b03": {
        "id": "h-b03", "category": "back",
        "name_kr": "칼단발", "name_en": "blunt_bob",
        "description": "턱선 근처 단발, 층/컬 없이 일자.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "bob", "volume_at_jaw": "medium", "volume_at_neck": "none",
        "image_vector": [0.3, 0.5, 0.7, 0.5, 0.4],
    },
    "h-b04": {
        "id": "h-b04", "category": "back",
        "name_kr": "단발 굵은 펌", "name_en": "bob_thick_perm",
        "description": "턱선 근처 단발에 굵은 C컬/S컬 혼합.",
        "base_score": 0.5, "curl_intensity": "heavy_c", "has_layers": False,
        "length_category": "bob", "volume_at_jaw": "heavy", "volume_at_neck": "medium",
        "image_vector": [0.7, 0.5, 0.4, 0.4, 0.5],
    },
    "h-b05": {
        "id": "h-b05", "category": "back",
        "name_kr": "단발 S컬펌", "name_en": "bob_s_curl",
        "description": "턱선 근처 단발, 작은 S컬 강하게.",
        "base_score": 0.5, "curl_intensity": "heavy_s", "has_layers": False,
        "length_category": "bob", "volume_at_jaw": "heavy", "volume_at_neck": "medium",
        "image_vector": [0.8, 0.3, 0.2, 0.2, 0.6],
    },
    "h-b06": {
        "id": "h-b06", "category": "back",
        "name_kr": "일자 중단발", "name_en": "straight_mid",
        "description": "어깨선/쇄골 근처, 층 없이 일자.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "mid", "volume_at_jaw": "medium", "volume_at_neck": "medium",
        "image_vector": [0.4, 0.6, 0.5, 0.5, 0.3],
    },
    "h-b07": {
        "id": "h-b07", "category": "back",
        "name_kr": "중단발 레이어드컷", "name_en": "mid_layered",
        "description": "쇄골/어깨선 기장에 끝머리 3-4cm 레이어드.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": True,
        "length_category": "mid", "volume_at_jaw": "light", "volume_at_neck": "light",
        "image_vector": [0.6, 0.7, 0.5, 0.6, 0.4],
    },
    "h-b08": {
        "id": "h-b08", "category": "back",
        "name_kr": "중단발 아웃C컬펌", "name_en": "mid_out_c_curl",
        "description": "쇄골/어깨선 기장, 끝머리에 아웃C컬.",
        "base_score": 0.5, "curl_intensity": "light_c", "has_layers": False,
        "length_category": "mid", "volume_at_jaw": "light", "volume_at_neck": "medium",
        "image_vector": [0.4, 0.5, 0.6, 0.7, 0.3],
    },
    "h-b09": {
        "id": "h-b09", "category": "back",
        "name_kr": "중단발펌", "name_en": "mid_s_curl_perm",
        "description": "목 중간~쇄골 기장, S컬 강하게.",
        "base_score": 0.5, "curl_intensity": "heavy_s", "has_layers": False,
        "length_category": "mid", "volume_at_jaw": "heavy", "volume_at_neck": "heavy",
        "image_vector": [0.8, 0.3, 0.3, 0.3, 0.5],
    },
    "h-b10": {
        "id": "h-b10", "category": "back",
        "name_kr": "긴 생머리", "name_en": "long_straight",
        "description": "겨드랑이선 이상 긴 생머리.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "long", "volume_at_jaw": "light", "volume_at_neck": "light",
        "image_vector": [0.5, 0.7, 0.4, 0.5, 0.3],
    },
    "h-b11": {
        "id": "h-b11", "category": "back",
        "name_kr": "긴머리펌", "name_en": "long_perm",
        "description": "겨드랑이선 이상 긴머리, C컬/굵은S컬.",
        "base_score": 0.5, "curl_intensity": "heavy_c", "has_layers": False,
        "length_category": "long", "volume_at_jaw": "medium", "volume_at_neck": "medium",
        "image_vector": [0.6, 0.6, 0.4, 0.5, 0.4],
    },
    "h-b12": {
        "id": "h-b12", "category": "back",
        "name_kr": "긴머리 레이어드펌", "name_en": "long_layered_perm",
        "description": "겨드랑이선 이상 긴머리, 쇄골 아래 레이어드 + 열펌.",
        "base_score": 0.5, "curl_intensity": "heavy_c", "has_layers": True,
        "length_category": "long", "volume_at_jaw": "light", "volume_at_neck": "light",
        "image_vector": [0.5, 0.5, 0.7, 0.8, 0.4],
    },
    "h-b13": {
        "id": "h-b13", "category": "back",
        "name_kr": "히피펌", "name_en": "hippy_perm",
        "description": "가슴 닿는 긴머리에 아주 작은 컬 강하게.",
        "base_score": 0.5, "curl_intensity": "hippy", "has_layers": False,
        "length_category": "long", "volume_at_jaw": "heavy", "volume_at_neck": "heavy",
        "image_vector": [0.6, 0.5, 0.3, 0.3, 0.9],
    },

    # ============================================================
    # ETC STYLES (기타) — 3종
    # ============================================================
    "h-e01": {
        "id": "h-e01", "category": "etc",
        "name_kr": "가르마", "name_en": "parting",
        "description": "대칭/비대칭 가르마.",
        "base_score": 0.5, "has_rating": False,
    },
    "h-e02": {
        "id": "h-e02", "category": "etc",
        "name_kr": "똥머리/하이포니테일", "name_en": "high_ponytail",
        "description": "정수리 위쪽에 높게 묶은 디자인.",
        "base_score": 0.5,
        "volume_at_jaw": "none", "volume_at_neck": "none",
        "image_vector": [0.7, 0.8, 0.4, 0.4, 0.3],
        "gaze_effect": {
            "blocks": [], "emphasizes": [],
            "attracts": ["crown"], "diverts": ["jaw", "mouth"],
            "covers": [], "extends": ["neck_line"],
        },
    },
    "h-e03": {
        "id": "h-e03", "category": "etc",
        "name_kr": "양갈래 머리", "name_en": "twin_tails",
        "description": "양쪽으로 머리를 갈라서 묶는 스타일.",
        "base_score": 0.5,
        "volume_at_jaw": "none", "volume_at_neck": "none",
        "image_vector": [0.8, 0.5, 0.1, 0.1, 0.7],
        "gaze_effect": {
            "blocks": [], "emphasizes": ["face_width"],
            "attracts": ["sides"], "diverts": [], "covers": [],
        },
    },
}


# ============================================================
# MALE STYLES (complete cuts) — 12종
# ============================================================
# Female 은 front × back 조합 체계이나, 남성 헤어는 cut 단일 체계가 표준.
# 따라서 category="complete" 단일 범주로 관리.
#
# image_vector 는 female 축 [러블리, 청순, 도도시크, 우아차분, 개성] 을 그대로 사용.
# 남성 전용 축(예: masculine/clean_cut/edgy)은 Phase B 에서 재정의 예정.
# 현재 값은 각 스타일의 통념적 인상 기반 초기 세트.
#
# FEATURE_MODIFIERS (hair_rules.py) 는 h-f*/h-b* female 스타일만 다룸.
# 남성 스타일은 현재 face_features 기반 스코어 조정이 없음 (base_score 0.5 + image_bonus).
# 얼굴 특징 교차 스코어링은 Phase B (hair_rules male branch) 에서 추가.
_MALE_STYLES = {
    "h-m01": {
        "id": "h-m01", "category": "complete", "gender": "male",
        "name_kr": "애즈펌", "name_en": "Azz Perm",
        "description": "굵은 웨이브의 중단발 펌. 자연스럽고 여유있는 인상.",
        "base_score": 0.5, "curl_intensity": "heavy_c", "has_layers": False,
        "length_category": "mid",
        "image_vector": [0.5, 0.4, 0.4, 0.5, 0.5],
    },
    "h-m02": {
        "id": "h-m02", "category": "complete", "gender": "male",
        "name_kr": "크롭컷", "name_en": "Crop Cut",
        "description": "매우 짧은 cropped 스타일. 깔끔하고 샤프한 인상.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.1, 0.4, 0.8, 0.2, 0.6],
    },
    "h-m03": {
        "id": "h-m03", "category": "complete", "gender": "male",
        "name_kr": "가르마펌", "name_en": "Parting Perm",
        "description": "뚜렷한 가르마에 자연 웨이브. 정돈된 격식 있는 인상.",
        "base_score": 0.5, "curl_intensity": "light_s", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.3, 0.5, 0.5, 0.8, 0.3],
    },
    "h-m04": {
        "id": "h-m04", "category": "complete", "gender": "male",
        "name_kr": "세미 리프컷", "name_en": "Semi Leaf Cut",
        "description": "리프컷의 순화 버전. 자연스러운 layer 와 볼륨.",
        "base_score": 0.5, "curl_intensity": "light_c", "has_layers": True,
        "length_category": "short",
        "image_vector": [0.4, 0.5, 0.4, 0.5, 0.4],
    },
    "h-m05": {
        "id": "h-m05", "category": "complete", "gender": "male",
        "name_kr": "가일컷", "name_en": "Guile Cut",
        "description": "Street Fighter 가일 캐릭터의 flat-top 스타일. 강한 개성.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.1, 0.2, 0.9, 0.1, 0.9],
    },
    "h-m06": {
        "id": "h-m06", "category": "complete", "gender": "male",
        "name_kr": "리프컷", "name_en": "Leaf Cut",
        "description": "나뭇잎 형태 실루엣, 뚜렷한 layer. 자연스럽고 유행 민감.",
        "base_score": 0.5, "curl_intensity": "light_c", "has_layers": True,
        "length_category": "short",
        "image_vector": [0.4, 0.5, 0.5, 0.5, 0.5],
    },
    "h-m07": {
        "id": "h-m07", "category": "complete", "gender": "male",
        "name_kr": "소프트 투블럭 댄디컷", "name_en": "Soft Two-Block Dandy Cut",
        "description": "옆면을 살짝 친 투블럭에 부드러운 탑. 댄디한 인상.",
        "base_score": 0.5, "curl_intensity": "light_s", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.4, 0.5, 0.5, 0.8, 0.3],
    },
    "h-m08": {
        "id": "h-m08", "category": "complete", "gender": "male",
        "name_kr": "쉐도우펌", "name_en": "Shadow Perm",
        "description": "자연스러운 그림자 같은 웨이브 펌. 볼륨 강조.",
        "base_score": 0.5, "curl_intensity": "heavy_s", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.5, 0.4, 0.4, 0.5, 0.5],
    },
    "h-m09": {
        "id": "h-m09", "category": "complete", "gender": "male",
        "name_kr": "시스루 댄디컷", "name_en": "See-Through Dandy Cut",
        "description": "시스루 앞머리 + 댄디한 뒷머리 조합. 깔끔하고 세련된 인상.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.4, 0.6, 0.5, 0.8, 0.3],
    },
    "h-m10": {
        "id": "h-m10", "category": "complete", "gender": "male",
        "name_kr": "아이비리그컷", "name_en": "Ivy League Cut",
        "description": "클래식한 미국 대학생 스타일. 격식 있고 지적인 인상.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "short",
        "image_vector": [0.3, 0.6, 0.5, 0.9, 0.2],
    },
    "h-m11": {
        "id": "h-m11", "category": "complete", "gender": "male",
        "name_kr": "장발 웨이브", "name_en": "Long Wave",
        "description": "어깨까지 오는 장발에 자연 웨이브. 표현적이고 개성있는 인상.",
        "base_score": 0.5, "curl_intensity": "heavy_c", "has_layers": True,
        "length_category": "long",
        "image_vector": [0.6, 0.4, 0.3, 0.4, 0.8],
    },
    "h-m12": {
        "id": "h-m12", "category": "complete", "gender": "male",
        "name_kr": "중발 묶머", "name_en": "Mid-Length Tied",
        "description": "중단발 길이를 뒤로 묶은 스타일. 자유롭고 독특한 인상.",
        "base_score": 0.5, "curl_intensity": "none", "has_layers": False,
        "length_category": "mid",
        "image_vector": [0.4, 0.4, 0.4, 0.4, 0.7],
    },
}

HAIR_STYLES.update(_MALE_STYLES)

# Female 엔트리에 gender 필드 자동 할당 (male 은 _MALE_STYLES 에서 명시됨).
# 기존 h-f*/h-b*/h-e* 24개 스타일을 한 곳에서 gender="female" 부여.
for _sid, _s in HAIR_STYLES.items():
    if "gender" not in _s:
        _s["gender"] = "female"


def get_front_styles(gender: str = "female"):
    """앞머리 스타일. gender='female' 만 해당 (male 은 complete 체계)."""
    return {
        k: v for k, v in HAIR_STYLES.items()
        if v.get("category") == "front" and v.get("gender") == gender
    }


def get_back_styles(gender: str = "female"):
    """뒷머리 스타일. gender='female' 만 해당."""
    return {
        k: v for k, v in HAIR_STYLES.items()
        if v.get("category") == "back" and v.get("gender") == gender
    }


def get_etc_styles(gender: str = "female"):
    """기타 스타일 (가르마/포니테일 등). gender='female' 만 해당."""
    return {
        k: v for k, v in HAIR_STYLES.items()
        if v.get("category") == "etc" and v.get("gender") == gender
    }


def get_complete_styles(gender: str = "male"):
    """단일 cut 스타일. gender='male' 의 12 entries."""
    return {
        k: v for k, v in HAIR_STYLES.items()
        if v.get("category") == "complete" and v.get("gender") == gender
    }
