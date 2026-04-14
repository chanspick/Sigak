"""
SIGAK Personal Color Module -- 4계절 x 서브타입 퍼스널 컬러 분류

6타입(warm/neutral/cool x clear/soft)에서
4계절 x 서브타입(light/bright/mute/deep) = 8타입으로 확장.

분류 축 3개:
  1. Warmth (웜/쿨) -- LAB의 b(황청) + a(적녹) 조합의 z-score
  2. Brightness (명도) -- LAB의 L (0-100 스케일)
  3. Chroma (채도) -- LAB의 sqrt(a^2 + b^2)
"""

import math
from dataclasses import dataclass


# ============================================================
# PersonalColorResult 데이터클래스
# ============================================================

@dataclass
class PersonalColorResult:
    """4계절 x 서브타입 퍼스널 컬러 분류 결과."""

    season: str       # "spring" | "summer" | "autumn" | "winter"
    subtype: str      # "light" | "bright" | "mute" | "deep"
    label_kr: str     # "봄 라이트"
    warmth_z: float   # z-score
    brightness: float  # L 값 (0-100)
    chroma: float
    confidence: float  # 0-1
    calibrated: bool


# ============================================================
# 계절 x 서브타입 팔레트 데이터 (8타입)
# ============================================================

SEASON_PALETTES: dict[str, dict] = {
    # ────────────────────────────────────────
    #  봄 라이트
    # ────────────────────────────────────────
    "spring_light": {
        "label_kr": "봄 라이트",
        "description": "밝고 따뜻한 톤이에요. 파스텔과 화사한 색이 자연스럽게 어울려요.",
        "best_colors": [
            {"name": "코랄 핑크", "hex": "#F88379", "usage": "립", "why": "따뜻한 피부톤과 톤온톤으로 자연스러운 화사함을 줘요."},
            {"name": "피치", "hex": "#FFCBA4", "usage": "블러셔", "why": "피부 속에서 우러나오는 듯한 혈색을 만들어요."},
            {"name": "살몬", "hex": "#FA8072", "usage": "립", "why": "밝은 톤을 해치지 않으면서 생기를 더해요."},
        ],
        "okay_colors": [
            {"name": "로즈 핑크", "hex": "#FF66B2", "usage": "립", "why": "약간 쿨하지만 밝은 톤이라 포인트로 활용 가능해요."},
            {"name": "라이트 오렌지", "hex": "#FFB347", "usage": "포인트", "why": "같은 웜 계열이라 눈에 살짝 올리면 화사해져요."},
        ],
        "avoid_colors": [
            {"name": "버건디", "hex": "#800020", "why": "어두운 색이 밝은 피부를 칙칙하게 눌러요."},
            {"name": "딥 레드", "hex": "#8B0000", "why": "무게감이 너무 강해서 얼굴이 가려져요."},
            {"name": "와인", "hex": "#722F37", "why": "탁하고 어두운 톤이 밝은 피부와 분리돼요."},
        ],
        "hair_colors": [
            {"name": "허니 브라운", "hex": "#C08040", "why": "따뜻한 피부톤에 부드러운 생기를 더해요."},
            {"name": "밀크 베이지", "hex": "#D4B896", "why": "밝은 톤과 자연스럽게 이어지는 부드러운 컬러예요."},
            {"name": "카라멜", "hex": "#A0632B", "why": "따뜻한 광택이 피부와 조화를 이뤄요."},
        ],
        "lip_direction": "밝고 따뜻한 색조. 피부보다 약간 선명한 정도로 발라요.",
        "cheek_direction": "살구빛 혈색. 피부 안에서 우러나오는 느낌으로 가볍게.",
        "eye_direction": "따뜻한 명색 계열. 펄은 골드 펄로 화사하게.",
        "foundation_guide": "13~17호 웜 (13W, 17W)",
    },
    # ────────────────────────────────────────
    #  봄 브라이트
    # ────────────────────────────────────────
    "spring_bright": {
        "label_kr": "봄 브라이트",
        "description": "선명하고 화사한 웜톤이에요. 비비드한 따뜻한 색이 생기를 더해줘요.",
        "best_colors": [
            {"name": "비비드 코랄", "hex": "#FF6F61", "usage": "립", "why": "선명한 피부톤을 한층 더 살려주는 최적의 립 컬러예요."},
            {"name": "브라이트 오렌지", "hex": "#FF8C00", "usage": "립", "why": "화사한 웜톤과 시너지를 내서 건강한 인상을 줘요."},
            {"name": "웜 레드", "hex": "#E25822", "usage": "립", "why": "강렬하면서도 피부와 잘 녹아드는 레드예요."},
        ],
        "okay_colors": [
            {"name": "코랄 핑크", "hex": "#F88379", "usage": "립", "why": "살짝 연하지만 데일리로 부담 없이 쓰기 좋아요."},
            {"name": "선명한 피치", "hex": "#FFCC99", "usage": "블러셔", "why": "내추럴 메이크업에 자연스러운 혈색을 줘요."},
        ],
        "avoid_colors": [
            {"name": "버건디", "hex": "#800020", "why": "탁한 색이 선명한 피부톤의 장점을 지워요."},
            {"name": "다크 브라운", "hex": "#5C4033", "why": "어둡고 무거워서 화사한 인상이 사라져요."},
            {"name": "뮤트 톤", "hex": "#A89F91", "why": "채도가 낮은 색이 얼굴을 흐리게 만들어요."},
        ],
        "hair_colors": [
            {"name": "코퍼 브라운", "hex": "#B05C3B", "why": "볕에 비치면 붉은 광택이 생기를 더해요."},
            {"name": "브라이트 카라멜", "hex": "#C47735", "why": "선명한 따뜻함이 피부톤과 하나로 이어져요."},
            {"name": "웜 체스넛", "hex": "#8B5E3C", "why": "톤을 정리하면서도 무겁지 않은 갈색이에요."},
        ],
        "lip_direction": "선명하고 밝은 웜 계열. 과감하게 발색을 올려도 어울려요.",
        "cheek_direction": "선명한 웜 혈색. 건강하고 화사한 느낌으로.",
        "eye_direction": "밝고 선명한 웜. 글리터는 골드로 포인트.",
        "foundation_guide": "13~21호 웜 (17W, 21W)",
    },
    # ────────────────────────────────────────
    #  여름 라이트
    # ────────────────────────────────────────
    "summer_light": {
        "label_kr": "여름 라이트",
        "description": "밝고 청량한 쿨톤이에요. 부드러운 파스텔 핑크 계열이 자연스럽게 어울려요.",
        "best_colors": [
            {"name": "로즈 핑크", "hex": "#FF66B2", "usage": "립", "why": "쿨한 피부톤을 맑고 화사하게 살려줘요."},
            {"name": "베이비 핑크", "hex": "#F4C2C2", "usage": "립", "why": "파스텔 톤이 밝은 피부와 자연스럽게 녹아요."},
            {"name": "라벤더 핑크", "hex": "#D8A0D8", "usage": "포인트", "why": "쿨 언더톤을 살리면서 고급스러운 느낌을 줘요."},
        ],
        "okay_colors": [
            {"name": "쿨 누드", "hex": "#D2B4A0", "usage": "베이스", "why": "무난하고 편안한 데일리 톤이에요."},
            {"name": "소프트 레드", "hex": "#C74375", "usage": "포인트", "why": "강한 포인트가 필요할 때 쿨 베이스로 활용해요."},
        ],
        "avoid_colors": [
            {"name": "오렌지", "hex": "#FF8C00", "why": "따뜻한 색이 쿨한 피부에서 떠요."},
            {"name": "브릭", "hex": "#CB4154", "why": "탁한 웜 계열이 피부를 칙칙하게 만들어요."},
            {"name": "테라코타", "hex": "#E2725B", "why": "흙빛 웜톤이 청량한 피부와 충돌해요."},
        ],
        "hair_colors": [
            {"name": "애쉬 블론드", "hex": "#B8A590", "why": "쿨한 피부톤에 투명한 느낌을 더해요."},
            {"name": "라벤더 그레이", "hex": "#9C8FA3", "why": "쿨 언더톤을 극대화하는 트렌디한 컬러예요."},
            {"name": "쿨 베이지 브라운", "hex": "#A09080", "why": "자연스러우면서도 칙칙하지 않은 중간 톤이에요."},
        ],
        "lip_direction": "차갑고 밝은 핑크 계열. 부드럽게 한 겹 올리는 느낌으로.",
        "cheek_direction": "청량한 핑크빛 혈색. 피부 속 투명감을 살려요.",
        "eye_direction": "시원한 톤의 명색. 펄은 실버/핑크 펄.",
        "foundation_guide": "13~17호 쿨 (13C, 17C)",
    },
    # ────────────────────────────────────────
    #  여름 뮤트
    # ────────────────────────────────────────
    "summer_mute": {
        "label_kr": "여름 뮤트",
        "description": "부드럽고 차분한 쿨톤이에요. 탁하고 은은한 색이 자연스럽게 어울려요.",
        "best_colors": [
            {"name": "모브", "hex": "#C8A2C8", "usage": "립", "why": "부드러운 쿨 톤이 피부의 차분함을 살려줘요."},
            {"name": "더스티 로즈", "hex": "#DCAE96", "usage": "립", "why": "뮤트한 채도가 피부와 자연스럽게 하나가 돼요."},
            {"name": "밀키 핑크", "hex": "#F3D1DC", "usage": "블러셔", "why": "은은한 혈색이 과하지 않은 분위기를 만들어요."},
        ],
        "okay_colors": [
            {"name": "쿨 누드", "hex": "#D2B4A0", "usage": "립", "why": "데일리로 편안하게 쓸 수 있는 무난한 톤이에요."},
            {"name": "소프트 레드", "hex": "#C74375", "usage": "포인트", "why": "약간 선명하지만 뮤트 피부 위에서 포인트가 돼요."},
        ],
        "avoid_colors": [
            {"name": "오렌지", "hex": "#FF8C00", "why": "선명한 웜 계열이 부드러운 톤과 충돌해요."},
            {"name": "비비드 레드", "hex": "#FF0000", "why": "너무 강한 채도가 얼굴에서 붕 떠요."},
            {"name": "테라코타", "hex": "#E2725B", "why": "흙빛 웜톤이 쿨한 피부를 탁하게 만들어요."},
        ],
        "hair_colors": [
            {"name": "애쉬 브라운", "hex": "#8B7D6B", "why": "탁한 쿨톤이 피부의 차분한 분위기와 맞아요."},
            {"name": "소프트 그레이 브라운", "hex": "#9E9488", "why": "자연스러운 뮤트 톤으로 은은하게 정리돼요."},
            {"name": "더스티 모브", "hex": "#957B8D", "why": "보라빛이 살짝 도는 브라운으로 개성을 줘요."},
        ],
        "lip_direction": "탁하고 부드러운 쿨 계열. 한 겹만 올려도 분위기가 나요.",
        "cheek_direction": "안개 낀 듯 은은한 쿨 혈색. 과하지 않게.",
        "eye_direction": "뮤트 톤 전체. 펄은 핑크/라벤더로 부드럽게.",
        "foundation_guide": "21~23호 쿨 (21C, 23C)",
    },
    # ────────────────────────────────────────
    #  가을 뮤트
    # ────────────────────────────────────────
    "autumn_mute": {
        "label_kr": "가을 뮤트",
        "description": "차분하고 부드러운 웜톤이에요. 탁하고 깊은 어스톤이 자연스럽게 어울려요.",
        "best_colors": [
            {"name": "테라코타", "hex": "#E2725B", "usage": "립", "why": "피부의 웜톤을 살리면서 차분한 분위기를 줘요."},
            {"name": "브릭 레드", "hex": "#CB4154", "usage": "립", "why": "깊은 웜톤이 피부와 자연스럽게 이어져요."},
            {"name": "딥 코랄", "hex": "#E56B6F", "usage": "블러셔", "why": "흙빛 뉘앙스의 혈색이 편안하고 자연스러워요."},
        ],
        "okay_colors": [
            {"name": "머스타드 누드", "hex": "#C8A951", "usage": "립", "why": "톤이 비슷해서 무난하지만 포인트는 약해요."},
            {"name": "브라운 레드", "hex": "#A52A2A", "usage": "포인트", "why": "가을 무드를 강하게 연출하고 싶을 때 좋아요."},
        ],
        "avoid_colors": [
            {"name": "핫 핑크", "hex": "#FF69B4", "why": "선명한 쿨 핑크가 웜 피부에서 동떨어져요."},
            {"name": "네온", "hex": "#39FF14", "why": "강렬한 형광이 차분한 피부 분위기를 깨요."},
            {"name": "쿨 레드", "hex": "#DC143C", "why": "차가운 레드가 따뜻한 피부톤과 분리돼요."},
        ],
        "hair_colors": [
            {"name": "웜 브라운", "hex": "#7B4B2A", "why": "자연스러운 갈색이 피부 톤을 정리해줘요."},
            {"name": "체스넛", "hex": "#954535", "why": "가을빛 붉은 뉘앙스가 웜톤을 살려요."},
            {"name": "올리브 브라운", "hex": "#6B5B3A", "why": "녹색 빛이 살짝 도는 브라운으로 깊이를 줘요."},
        ],
        "lip_direction": "탁하고 깊은 웜 계열. 차분한 발색으로 자연스럽게.",
        "cheek_direction": "은은한 흙빛 혈색. 피부 위에 녹이듯이.",
        "eye_direction": "내추럴 어스톤. 펄은 골드/브론즈.",
        "foundation_guide": "21~23호 웜 (21W, 23W)",
    },
    # ────────────────────────────────────────
    #  가을 딥
    # ────────────────────────────────────────
    "autumn_deep": {
        "label_kr": "가을 딥",
        "description": "깊고 풍부한 웜톤이에요. 진하고 무게감 있는 색이 잘 소화돼요.",
        "best_colors": [
            {"name": "버건디", "hex": "#800020", "usage": "립", "why": "깊은 피부톤이 무겁고 고급스러운 색을 소화해요."},
            {"name": "딥 브라운 레드", "hex": "#6B3A2A", "usage": "립", "why": "피부와 동일 계열의 깊은 색이 자연스러운 통일감을 줘요."},
            {"name": "와인", "hex": "#722F37", "usage": "포인트", "why": "시크한 무드를 극대화하는 가을 딥의 시그니처 컬러예요."},
        ],
        "okay_colors": [
            {"name": "다크 코랄", "hex": "#C04040", "usage": "립", "why": "약간 밝지만 웜 베이스라 낮에 쓰기 좋아요."},
            {"name": "초콜릿", "hex": "#7B3F00", "usage": "포인트", "why": "아이섀도나 라이너로 깊이를 더해요."},
        ],
        "avoid_colors": [
            {"name": "파스텔 핑크", "hex": "#FFD1DC", "why": "가볍고 밝은 색이 깊은 피부톤과 분리돼요."},
            {"name": "라벤더", "hex": "#B57EDC", "why": "쿨한 보라빛이 웜 피부에서 떠요."},
            {"name": "네온", "hex": "#39FF14", "why": "형광색이 무게감 있는 톤과 심하게 충돌해요."},
        ],
        "hair_colors": [
            {"name": "다크 초콜릿", "hex": "#3B2219", "why": "깊은 갈색이 피부의 풍부함을 한층 살려요."},
            {"name": "딥 마호가니", "hex": "#4E2C2C", "why": "붉은 뉘앙스가 웜톤의 깊이와 어우러져요."},
            {"name": "에스프레소", "hex": "#3C2218", "why": "거의 블랙에 가까운 진한 갈색으로 세련미를 줘요."},
        ],
        "lip_direction": "깊고 진한 웜 계열. 무게감 있는 발색으로 시크하게.",
        "cheek_direction": "깊은 혈색. 피부와 대비를 살려 입체감을 더해요.",
        "eye_direction": "깊은 어스톤. 스모키 메이크업에 강한 타입이에요.",
        "foundation_guide": "25~27호 웜 (25W, 27W)",
    },
    # ────────────────────────────────────────
    #  겨울 브라이트
    # ────────────────────────────────────────
    "winter_bright": {
        "label_kr": "겨울 브라이트",
        "description": "선명하고 강렬한 쿨톤이에요. 쨍한 고채도 색이 대비감을 살려줘요.",
        "best_colors": [
            {"name": "체리 레드", "hex": "#DE3163", "usage": "립", "why": "선명한 쿨 레드가 피부 대비를 극대화해요."},
            {"name": "핫 핑크", "hex": "#FF69B4", "usage": "립", "why": "강한 채도가 피부의 선명함과 시너지를 내요."},
            {"name": "비비드 레드", "hex": "#FF0000", "usage": "립", "why": "겨울 브라이트만 소화할 수 있는 원 컬러예요."},
        ],
        "okay_colors": [
            {"name": "푸시아", "hex": "#FF00FF", "usage": "포인트", "why": "아이 포인트나 블러셔로 개성 있게 활용 가능해요."},
            {"name": "쿨 오렌지", "hex": "#FF6347", "usage": "포인트", "why": "쿨 베이스의 오렌지라 겨울 타입에도 어울려요."},
        ],
        "avoid_colors": [
            {"name": "누드", "hex": "#E8C4B8", "why": "연한 색이 대비감을 없앤서 얼굴이 밋밋해져요."},
            {"name": "살몬", "hex": "#FA8072", "why": "웜한 뉘앙스가 쿨 피부의 선명함을 흐려요."},
            {"name": "코랄", "hex": "#FF7F50", "why": "따뜻한 오렌지빛이 피부톤과 안 맞아요."},
        ],
        "hair_colors": [
            {"name": "블루 블랙", "hex": "#1A1A2E", "why": "푸른 광택이 쿨 피부의 대비감을 살려요."},
            {"name": "다크 애쉬", "hex": "#3B3B3B", "why": "차가운 회색 톤이 세련된 인상을 줘요."},
            {"name": "제트 블랙", "hex": "#0A0A0A", "why": "피부와 머리카락의 강한 대비가 겨울 타입의 장점이에요."},
        ],
        "lip_direction": "선명하고 쨍한 쿨 계열. 대비감을 극대화해요.",
        "cheek_direction": "선명한 대비. 피부 밝기와 대비를 강조하세요.",
        "eye_direction": "쨍한 쿨 계열. 글리터는 실버로 차갑게.",
        "foundation_guide": "17~21호 쿨 (17C, 21C)",
    },
    # ────────────────────────────────────────
    #  겨울 딥
    # ────────────────────────────────────────
    "winter_deep": {
        "label_kr": "겨울 딥",
        "description": "어둡고 강렬한 쿨톤이에요. 깊고 무게감 있는 쿨 계열이 강한 존재감을 줘요.",
        "best_colors": [
            {"name": "와인", "hex": "#722F37", "usage": "립", "why": "깊은 쿨톤이 강한 존재감과 세련미를 줘요."},
            {"name": "딥 퍼플", "hex": "#301934", "usage": "립", "why": "어두운 피부톤이 무겁고 고급스러운 색을 소화해요."},
            {"name": "다크 체리", "hex": "#990033", "usage": "립", "why": "블루 베이스의 레드가 쿨 피부와 완벽하게 맞아요."},
        ],
        "okay_colors": [
            {"name": "딥 레드", "hex": "#8B0000", "usage": "포인트", "why": "강렬한 레드를 아이라인이나 포인트로 활용해요."},
            {"name": "블랙 레드", "hex": "#660000", "usage": "포인트", "why": "거의 블랙에 가까운 레드로 시크함의 극치예요."},
        ],
        "avoid_colors": [
            {"name": "파스텔", "hex": "#FFD1DC", "why": "가볍고 밝은 색이 강한 피부톤과 분리돼요."},
            {"name": "코랄", "hex": "#FF7F50", "why": "따뜻한 오렌지빛이 쿨 피부에서 떠요."},
            {"name": "피치", "hex": "#FFCBA4", "why": "연한 웜톤이 대비 없이 밋밋해져요."},
        ],
        "hair_colors": [
            {"name": "오프 블랙", "hex": "#1C1C1C", "why": "자연스러운 블랙에 깊이감을 더해요."},
            {"name": "다크 에스프레소", "hex": "#2C1A12", "why": "블랙에 가까운 진갈색이 강렬한 인상을 유지해요."},
            {"name": "차콜", "hex": "#2F2F2F", "why": "회색 뉘앙스가 쿨톤의 세련미를 살려요."},
        ],
        "lip_direction": "어둡고 강렬한 쿨 계열. 깊이 있는 발색으로.",
        "cheek_direction": "깊은 쿨빛 혈색. 피부와 톤을 맞춰요.",
        "eye_direction": "강렬한 대비감. 스모키 메이크업이 최적이에요.",
        "foundation_guide": "25~27호 쿨 (25C, 27C)",
    },
}


# ============================================================
# PersonalColorClassifier
# ============================================================

class PersonalColorClassifier:
    """
    캘리브레이션되지 않은 RAW LAB 기반 3축 → 4계절 x 서브타입 분류.

    분류 축:
      1. Warmth -- (b_mean - 128) + (a_mean - 128) * 0.5 의 z-score
      2. Brightness -- L값 (0-100 스케일)
      3. Chroma -- sqrt((a_mean - 128)^2 + (b_mean - 128)^2)
    """

    # warmth 기준
    _WARMTH_CENTER_CALIBRATED = 5.0
    _WARMTH_CENTER_UNCALIBRATED = 13.0
    _WARMTH_STD = 9.5

    # 명도 기준 (L값, 0-100 스케일)
    # SCUT mean=61.7, 셀럽 mean=46.1 → 중간값 기준 상대 분류
    _BRIGHTNESS_CENTER = 50.0
    _BRIGHTNESS_STD = 15.0
    # |z| > 0.5 → high/low, |z| <= 0.5 → medium
    _BRIGHTNESS_Z_THRESHOLD = 0.5

    # 채도 기준 (LAB C* 벡터 크기)
    _CHROMA_HIGH = 18
    _CHROMA_LOW = 10

    def classify(
        self,
        warmth: float,
        brightness: float,
        chroma: float,
        is_calibrated: bool = False,
    ) -> PersonalColorResult:
        """
        4계절 x 서브타입 분류.

        Args:
            warmth: raw warmth 값 = (b_mean - 128) + (a_mean - 128) * 0.5
            brightness: L 값 (0-100 스케일). face.py에서 l_mean * 100으로 변환해서 전달.
            chroma: 채도 = sqrt((a_mean - 128)^2 + (b_mean - 128)^2)
            is_calibrated: 백지 캘리브레이션 적용 여부
        """
        center = (
            self._WARMTH_CENTER_CALIBRATED
            if is_calibrated
            else self._WARMTH_CENTER_UNCALIBRATED
        )
        warmth_z = (warmth - center) / self._WARMTH_STD

        # 1차: 웜/쿨 판정
        is_warm = warmth_z > 0.3
        is_cool = warmth_z < -0.3
        is_neutral = not is_warm and not is_cool

        # 2차: 명도/채도 판정 (명도도 z-score 기반)
        brightness_z = (brightness - self._BRIGHTNESS_CENTER) / self._BRIGHTNESS_STD
        is_bright_skin = brightness_z > self._BRIGHTNESS_Z_THRESHOLD
        is_dark_skin = brightness_z < -self._BRIGHTNESS_Z_THRESHOLD
        is_high_chroma = chroma > self._CHROMA_HIGH
        is_low_chroma = chroma < self._CHROMA_LOW

        # 3차: 4계절 x 서브타입 결정
        season, subtype = self._determine_type(
            is_warm, is_cool, is_neutral,
            is_bright_skin, is_dark_skin,
            is_high_chroma, is_low_chroma,
            warmth_z, brightness, chroma,
        )

        # 신뢰도 계산
        confidence = self._calculate_confidence(
            warmth_z, brightness, chroma, is_calibrated,
        )

        label_kr = _KOREAN_LABELS.get(
            (season, subtype), f"{season} {subtype}"
        )

        return PersonalColorResult(
            season=season,
            subtype=subtype,
            label_kr=label_kr,
            warmth_z=round(warmth_z, 3),
            brightness=round(brightness, 1),
            chroma=round(chroma, 1),
            confidence=confidence,
            calibrated=is_calibrated,
        )

    # ----------------------------------------------------------
    # 분류 결정 트리 (skintone.md Section 3-2)
    # ----------------------------------------------------------

    @staticmethod
    def _determine_type(
        is_warm: bool,
        is_cool: bool,
        is_neutral: bool,
        is_bright_skin: bool,
        is_dark_skin: bool,
        is_high_chroma: bool,
        is_low_chroma: bool,
        warmth_z: float,
        brightness: float,
        chroma: float,
    ) -> tuple[str, str]:
        """PCCS 기반 분류 결정 트리."""

        if is_warm:
            # 웜톤 -> 봄 or 가을
            if is_bright_skin and is_high_chroma:
                return "spring", "bright"
            elif is_bright_skin:
                return "spring", "light"
            elif is_dark_skin:
                return "autumn", "deep"
            elif is_low_chroma:
                return "autumn", "mute"
            elif is_high_chroma:
                return "spring", "bright"
            else:
                # 중간 -> warmth 강도로 판단
                if warmth_z > 0.8:
                    return "autumn", "mute"
                else:
                    return "spring", "light"

        elif is_cool:
            # 쿨톤 -> 여름 or 겨울
            if is_bright_skin and is_low_chroma:
                return "summer", "light"
            elif is_bright_skin and is_high_chroma:
                return "winter", "bright"
            elif is_dark_skin:
                return "winter", "deep"
            elif is_low_chroma:
                return "summer", "mute"
            elif is_high_chroma:
                return "winter", "bright"
            else:
                if warmth_z < -0.8:
                    return "winter", "deep"
                else:
                    return "summer", "mute"

        else:
            # Neutral -> 명채도 패턴으로 결정
            if is_bright_skin:
                if warmth_z >= 0:
                    return "spring", "light"
                else:
                    return "summer", "light"
            elif is_dark_skin:
                if warmth_z >= 0:
                    return "autumn", "deep"
                else:
                    return "winter", "deep"
            elif is_low_chroma:
                if warmth_z >= 0:
                    return "autumn", "mute"
                else:
                    return "summer", "mute"
            elif is_high_chroma:
                if warmth_z >= 0:
                    return "spring", "bright"
                else:
                    return "winter", "bright"
            else:
                # 완전 중간 -> warmth 미세 부호로 결정
                if warmth_z >= 0:
                    return "spring", "light"
                else:
                    return "summer", "light"

    def _calculate_confidence(
        self,
        warmth_z: float,
        brightness: float,
        chroma: float,
        is_calibrated: bool,
    ) -> float:
        """
        분류 신뢰도. 경계선에 가까울수록 낮음.
        캘리브레이션 안 됐으면 30% 감소.
        """
        # warmth 경계 거리 (|z| = 0.3이 경계)
        warmth_dist = abs(abs(warmth_z) - 0.3) / 0.3

        # 명도 경계 거리 (z-score 기반)
        brightness_z = (brightness - self._BRIGHTNESS_CENTER) / self._BRIGHTNESS_STD
        brightness_dist = abs(abs(brightness_z) - self._BRIGHTNESS_Z_THRESHOLD) / 0.5

        # 채도 경계 거리
        chroma_dist = min(
            abs(chroma - self._CHROMA_HIGH),
            abs(chroma - self._CHROMA_LOW),
        ) / 5

        base = min(warmth_dist, brightness_dist, chroma_dist)
        base = max(0.1, min(base, 1.0))

        if not is_calibrated:
            base *= 0.7

        return round(base, 2)


# ============================================================
# 한국어 라벨 매핑
# ============================================================

_KOREAN_LABELS: dict[tuple[str, str], str] = {
    ("spring", "light"): "봄 라이트",
    ("spring", "bright"): "봄 브라이트",
    ("summer", "light"): "여름 라이트",
    ("summer", "mute"): "여름 뮤트",
    ("autumn", "mute"): "가을 뮤트",
    ("autumn", "deep"): "가을 딥",
    ("winter", "bright"): "겨울 브라이트",
    ("winter", "deep"): "겨울 딥",
}


# ============================================================
# 팔레트 조회
# ============================================================

def get_season_palette(season: str, subtype: str) -> dict:
    """특정 계절+서브타입의 팔레트를 반환한다. 하위호환 키 자동 생성."""
    key = f"{season}_{subtype}"
    palette = SEASON_PALETTES.get(key, SEASON_PALETTES["spring_light"]).copy()
    # 하위호환: recommended / avoid / avoid_reason 자동 생성
    if "recommended" not in palette:
        palette["recommended"] = palette.get("best_colors", [])
    if "avoid" not in palette:
        palette["avoid"] = palette.get("avoid_colors", [])
    if "avoid_reason" not in palette:
        avoid_colors = palette.get("avoid_colors", [])
        palette["avoid_reason"] = avoid_colors[0].get("why", "") if avoid_colors else ""
    return palette


# ============================================================
# 레거시 6타입 역매핑 (하위 호환)
# ============================================================

def map_to_legacy_6type(result: PersonalColorResult) -> dict:
    """
    4계절 결과를 기존 6타입 시스템으로 역매핑.

    매핑 규칙:
      - spring -> warm (clear if bright, soft if mute/light)
      - summer -> cool (clear if bright, soft if mute/light)
      - autumn -> warm (soft if mute/light, clear if deep)
      - winter -> cool (clear if bright/deep)
    """
    season = result.season
    subtype = result.subtype

    if season == "spring":
        undertone = "warm"
        chroma_type = "clear" if subtype == "bright" else "soft"
    elif season == "summer":
        undertone = "cool"
        chroma_type = "soft"  # 여름은 대체로 soft
        if subtype == "light":
            # 여름 라이트는 고명도+저채도이므로 soft
            chroma_type = "soft"
    elif season == "autumn":
        undertone = "warm"
        chroma_type = "clear" if subtype == "deep" else "soft"
    elif season == "winter":
        undertone = "cool"
        chroma_type = "clear"  # 겨울은 대체로 clear
    else:
        undertone = "neutral"
        chroma_type = "soft"

    legacy_key = f"{undertone}_{chroma_type}"

    return {
        "skin_tone": undertone,
        "chroma_type": chroma_type,
        "legacy_key": legacy_key,
    }
