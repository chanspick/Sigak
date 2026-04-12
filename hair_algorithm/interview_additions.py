"""
SIGAK Interview Additions for Hair Recommendation
==================================================
build_hair_spec()에 필요한 입력 데이터를 확보하기 위한
질문지 추가/개선 스키마.

기존 6개 질문 유지 + 신규 4개 + 기존 1개 구조화 = 총 11개
"""

# ============================================================
# 신규 질문 4개
# ============================================================

NEW_QUESTIONS = [
    {
        "key": "neck_length",
        "label": "목 길이",
        "label_en": "Neck Length",
        "type": "single_select",
        "required": True,
        "options": [
            {"value": "short", "label": "짧은 편"},
            {"value": "normal", "label": "보통"},
            {"value": "long", "label": "긴 편"},
        ],
        "placeholder": "목 길이가 어느 정도인지 선택해주세요.",
        "help_text": "턱 아래부터 어깨선까지의 길이를 기준으로 판단해주세요.",
        "pipeline_consumer": "build_hair_spec",
        "affects": [
            "뒷머리 기장 제한 (보브단발~긴머리)",
            "컬감 위치 제한 (목 주변)",
            "묶음머리 추천도",
        ],
    },
    {
        "key": "shoulder_width",
        "label": "어깨 너비",
        "label_en": "Shoulder Width",
        "type": "single_select",
        "required": True,
        "options": [
            {"value": "narrow", "label": "좁은 편 (얼굴보다 좁아보임)"},
            {"value": "normal", "label": "보통"},
            {"value": "wide", "label": "넓은 편"},
        ],
        "placeholder": "얼굴 가로 폭 대비 어깨 너비를 기준으로 선택해주세요.",
        "pipeline_consumer": "build_hair_spec",
        "affects": [
            "고볼륨 스타일 (히피펌, 단발S컬) 추천도",
            "전체 비율 균형 판단",
        ],
    },
    {
        "key": "hair_volume",
        "label": "모발 숱/볼륨",
        "label_en": "Hair Volume",
        "type": "single_select",
        "required": True,
        "options": [
            {"value": "low", "label": "적은 편 (얇고 빈약)"},
            {"value": "normal", "label": "보통"},
            {"value": "high", "label": "많은 편 (풍성)"},
        ],
        "placeholder": "머리숱이 어느 정도인지 선택해주세요.",
        "pipeline_consumer": "build_hair_spec",
        "affects": [
            "시스루뱅 조건부 추천 (숱 많으면 감점)",
            "히피펌 조건부 추천 (숱 적으면 오히려 활용 가능)",
            "풀뱅 추천도",
        ],
    },
    {
        "key": "current_hair_state",
        "label": "현재 머리 상태",
        "label_en": "Current Hair State",
        "type": "multi_field",
        "required": False,
        "sub_fields": [
            {
                "key": "current_length",
                "label": "현재 기장",
                "type": "single_select",
                "options": [
                    {"value": "short", "label": "숏컷"},
                    {"value": "bob", "label": "단발 (턱선)"},
                    {"value": "mid", "label": "중단발 (어깨)"},
                    {"value": "long", "label": "긴머리 (가슴선 이상)"},
                ],
            },
            {
                "key": "current_perm",
                "label": "현재 펌 상태",
                "type": "single_select",
                "options": [
                    {"value": "none", "label": "없음 (생머리)"},
                    {"value": "c_curl", "label": "C컬/굵은펌"},
                    {"value": "s_curl", "label": "S컬/잔컬펌"},
                ],
            },
            {
                "key": "current_color",
                "label": "현재 염색",
                "type": "single_select",
                "options": [
                    {"value": "natural", "label": "자연모 (검정/진갈색)"},
                    {"value": "dyed", "label": "염색 (밝은 갈색~)"},
                    {"value": "bleached", "label": "탈색 (금발~)"},
                ],
            },
        ],
        "pipeline_consumer": "build_hair_spec (salon_instruction 생성 + 전환비용 계산)",
    },
]


# ============================================================
# 기존 질문 구조화 개선 1개
# ============================================================

IMPROVED_QUESTIONS = [
    {
        "key": "hair_texture",
        "label": "모질",
        "label_en": "Hair Texture",
        "type": "single_select",  # 기존: textarea
        "required": True,
        "options": [
            {"value": "straight", "label": "직모"},
            {"value": "wavy", "label": "약간 웨이브"},
            {"value": "curly", "label": "곱슬"},
        ],
        "pipeline_consumer": "build_hair_spec + generate_report",
        "note": "기존 textarea에서 single_select로 변경. 굵기는 hair_thickness로 분리.",
    },
    {
        "key": "hair_thickness",
        "label": "모발 굵기",
        "label_en": "Hair Thickness",
        "type": "single_select",  # 기존: hair_texture에 합쳐져 있었음
        "required": True,
        "options": [
            {"value": "thin", "label": "가는 편"},
            {"value": "normal", "label": "보통"},
            {"value": "thick", "label": "굵은 편"},
        ],
        "pipeline_consumer": "build_hair_spec + generate_report",
        "note": "hair_texture에서 분리. 모질과 굵기를 독립 변수로.",
    },
]


# ============================================================
# 추가 권장 (v2): 얼굴 고민 구체화
# ============================================================

V2_QUESTIONS = [
    {
        "key": "face_concerns",
        "label": "가장 신경 쓰이는 부분",
        "label_en": "Face Concerns",
        "type": "multi_select",
        "max_select": 3,
        "required": False,
        "options": [
            {"value": "wide_forehead", "label": "넓은 이마"},
            {"value": "short_forehead", "label": "짧은 이마"},
            {"value": "cheekbone", "label": "광대"},
            {"value": "square_jaw", "label": "사각턱"},
            {"value": "long_face", "label": "긴 얼굴"},
            {"value": "wide_face", "label": "넓은/짧은 얼굴"},
            {"value": "large_nose", "label": "큰 코"},
            {"value": "mouth_protrusion", "label": "돌출입"},
            {"value": "long_philtrum", "label": "긴 인중"},
            {"value": "wide_between_eyes", "label": "넓은 미간"},
        ],
        "pipeline_consumer": "build_hair_spec (교차검증: AI분석 vs 유저자각)",
        "note": "v2에서 추가. AI 분석과 유저 자각 사이 교차검증 가능.",
    },
]


# ============================================================
# 최종 질문 플로우 (Step 2에 삽입)
# ============================================================

STEP2_HAIR_BODY_QUESTIONS = [
    # 기존 hair_texture 구조화
    "hair_texture",       # single_select (직모/웨이브/곱슬)
    "hair_thickness",     # single_select (가는/보통/굵은) — 분리
    # 신규
    "hair_volume",        # single_select (적은/보통/많은)
    "current_hair_state", # multi_field (기장+펌+컬러)
    "neck_length",        # single_select (짧은/보통/긴)
    "shoulder_width",     # single_select (좁은/보통/넓은)
]

# UI 가이드:
# - 6개 전부 single_select 또는 multi_field → 클릭 몇 번이면 끝
# - textarea 추가 부담 0
# - current_hair_state만 optional, 나머지 required
# - 기존 Step 1의 6개 textarea는 그대로 유지
