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
    "spring_light": {
        "label_kr": "봄 라이트",
        "description": "밝고 따뜻한 톤이에요. 파스텔과 화사한 색이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "코랄 핑크", "hex": "#F88379", "usage": "립"},
            {"name": "피치", "hex": "#FFCBA4", "usage": "블러셔"},
            {"name": "살몬", "hex": "#FA8072", "usage": "립"},
            {"name": "라이트 오렌지", "hex": "#FFB347", "usage": "포인트"},
            {"name": "누드 핑크", "hex": "#E8C4B8", "usage": "베이스"},
        ],
        "avoid": [
            {"name": "버건디", "hex": "#800020"},
            {"name": "딥 레드", "hex": "#8B0000"},
            {"name": "와인", "hex": "#722F37"},
        ],
        "avoid_reason": "어둡고 무거운 색이 얼굴을 칙칙하게 가려요.",
        "lip_direction": "밝고 따뜻한 색조. 피부보다 약간 선명한 정도.",
        "cheek_direction": "살구빛 혈색. 자연스러운 화사함.",
        "eye_direction": "따뜻한 명색 계열. 펄은 골드 펄.",
        "foundation_guide": "13~17호 웜 (13W, 17W)",
    },
    "spring_bright": {
        "label_kr": "봄 브라이트",
        "description": "선명하고 화사한 웜톤이에요. 비비드한 따뜻한 색이 생기를 더해줘요.",
        "recommended": [
            {"name": "비비드 코랄", "hex": "#FF6F61", "usage": "립"},
            {"name": "브라이트 오렌지", "hex": "#FF8C00", "usage": "립"},
            {"name": "웜 레드", "hex": "#E25822", "usage": "립"},
            {"name": "비비드 피치", "hex": "#FF9966", "usage": "블러셔"},
            {"name": "선명한 피치", "hex": "#FFCC99", "usage": "블러셔"},
        ],
        "avoid": [
            {"name": "버건디", "hex": "#800020"},
            {"name": "다크 브라운", "hex": "#5C4033"},
            {"name": "뮤트 톤", "hex": "#A89F91"},
        ],
        "avoid_reason": "탁하거나 어두운 색이 화사함을 가려요.",
        "lip_direction": "선명하고 밝은 웜 계열. 화사한 생기.",
        "cheek_direction": "선명한 웜 혈색. 건강하고 화사하게.",
        "eye_direction": "밝고 선명한 웜. 글리터는 골드.",
        "foundation_guide": "13~21호 웜 (17W, 21W)",
    },
    "summer_light": {
        "label_kr": "여름 라이트",
        "description": "밝고 청량한 쿨톤이에요. 부드러운 파스텔 핑크 계열이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "로즈 핑크", "hex": "#FF66B2", "usage": "립"},
            {"name": "베이비 핑크", "hex": "#F4C2C2", "usage": "립"},
            {"name": "라벤더 핑크", "hex": "#D8A0D8", "usage": "립"},
            {"name": "쿨 누드", "hex": "#D2B4A0", "usage": "베이스"},
            {"name": "소프트 레드", "hex": "#C74375", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "오렌지", "hex": "#FF8C00"},
            {"name": "브릭", "hex": "#CB4154"},
            {"name": "테라코타", "hex": "#E2725B"},
        ],
        "avoid_reason": "따뜻하고 탁한 색이 피부에서 뜨거나 칙칙해 보여요.",
        "lip_direction": "차갑고 밝은 핑크 계열. 부드러운 발색.",
        "cheek_direction": "청량한 핑크빛 혈색.",
        "eye_direction": "시원한 톤의 명색. 펄은 실버/핑크 펄.",
        "foundation_guide": "13~17호 쿨 (13C, 17C)",
    },
    "summer_mute": {
        "label_kr": "여름 뮤트",
        "description": "부드럽고 차분한 쿨톤이에요. 탁하고 은은한 색이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "모브", "hex": "#C8A2C8", "usage": "립"},
            {"name": "더스티 로즈", "hex": "#DCAE96", "usage": "립"},
            {"name": "쿨 누드", "hex": "#D2B4A0", "usage": "립"},
            {"name": "밀키 핑크", "hex": "#F3D1DC", "usage": "블러셔"},
            {"name": "소프트 레드", "hex": "#C74375", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "오렌지", "hex": "#FF8C00"},
            {"name": "비비드 레드", "hex": "#FF0000"},
            {"name": "테라코타", "hex": "#E2725B"},
        ],
        "avoid_reason": "선명하거나 따뜻한 색이 피부와 충돌해서 부담스러워 보여요.",
        "lip_direction": "탁하고 부드러운 쿨 계열. 과하지 않은 발색.",
        "cheek_direction": "안개 낀 듯 은은한 쿨 혈색.",
        "eye_direction": "뮤트 톤 전체. 펄은 핑크/라벤더.",
        "foundation_guide": "21~23호 쿨 (21C, 23C)",
    },
    "autumn_mute": {
        "label_kr": "가을 뮤트",
        "description": "차분하고 부드러운 웜톤이에요. 탁하고 깊은 어스톤이 자연스럽게 어울려요.",
        "recommended": [
            {"name": "테라코타", "hex": "#E2725B", "usage": "립"},
            {"name": "브릭 레드", "hex": "#CB4154", "usage": "립"},
            {"name": "머스타드 누드", "hex": "#C8A951", "usage": "립"},
            {"name": "딥 코랄", "hex": "#E56B6F", "usage": "블러셔"},
            {"name": "브라운 레드", "hex": "#A52A2A", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "핫 핑크", "hex": "#FF69B4"},
            {"name": "네온", "hex": "#39FF14"},
            {"name": "쿨 레드", "hex": "#DC143C"},
        ],
        "avoid_reason": "선명하고 차가운 색이 피부에서 동떨어져 보여요.",
        "lip_direction": "탁하고 깊은 웜 계열. 차분한 발색.",
        "cheek_direction": "은은한 흙빛 혈색. 자연스럽게.",
        "eye_direction": "내추럴 어스톤. 펄은 골드/브론즈.",
        "foundation_guide": "21~23호 웜 (21W, 23W)",
    },
    "autumn_deep": {
        "label_kr": "가을 딥",
        "description": "깊고 풍부한 웜톤이에요. 진하고 무게감 있는 색이 잘 소화돼요.",
        "recommended": [
            {"name": "버건디", "hex": "#800020", "usage": "립"},
            {"name": "딥 브라운 레드", "hex": "#6B3A2A", "usage": "립"},
            {"name": "다크 코랄", "hex": "#C04040", "usage": "립"},
            {"name": "와인", "hex": "#722F37", "usage": "포인트"},
            {"name": "초콜릿", "hex": "#7B3F00", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "파스텔 핑크", "hex": "#FFD1DC"},
            {"name": "라벤더", "hex": "#B57EDC"},
            {"name": "네온", "hex": "#39FF14"},
        ],
        "avoid_reason": "가볍고 밝은 파스텔이 피부톤과 분리되어 보여요.",
        "lip_direction": "깊고 진한 웜 계열. 무게감 있는 발색.",
        "cheek_direction": "깊은 혈색. 피부와 대비 살리기.",
        "eye_direction": "깊은 어스톤. 스모키에 강함.",
        "foundation_guide": "25~27호 웜 (25W, 27W)",
    },
    "winter_bright": {
        "label_kr": "겨울 브라이트",
        "description": "선명하고 강렬한 쿨톤이에요. 쨍한 고채도 색이 대비감을 살려줘요.",
        "recommended": [
            {"name": "체리 레드", "hex": "#DE3163", "usage": "립"},
            {"name": "핫 핑크", "hex": "#FF69B4", "usage": "립"},
            {"name": "비비드 레드", "hex": "#FF0000", "usage": "립"},
            {"name": "푸시아", "hex": "#FF00FF", "usage": "포인트"},
            {"name": "쿨 오렌지", "hex": "#FF6347", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "누드", "hex": "#E8C4B8"},
            {"name": "살몬", "hex": "#FA8072"},
            {"name": "코랄", "hex": "#FF7F50"},
        ],
        "avoid_reason": "따뜻하고 연한 색이 피부의 선명함을 가려요.",
        "lip_direction": "선명하고 쨍한 쿨 계열. 대비감 극대화.",
        "cheek_direction": "선명한 대비. 피부 밝기와 대비 강조.",
        "eye_direction": "쨍한 쿨 계열. 글리터는 실버.",
        "foundation_guide": "17~21호 쿨 (17C, 21C)",
    },
    "winter_deep": {
        "label_kr": "겨울 딥",
        "description": "어둡고 강렬한 쿨톤이에요. 깊고 무게감 있는 쿨 계열이 강한 존재감을 줘요.",
        "recommended": [
            {"name": "와인", "hex": "#722F37", "usage": "립"},
            {"name": "딥 퍼플", "hex": "#301934", "usage": "립"},
            {"name": "다크 체리", "hex": "#990033", "usage": "립"},
            {"name": "딥 레드", "hex": "#8B0000", "usage": "포인트"},
            {"name": "블랙 레드", "hex": "#660000", "usage": "포인트"},
        ],
        "avoid": [
            {"name": "파스텔", "hex": "#FFD1DC"},
            {"name": "코랄", "hex": "#FF7F50"},
            {"name": "피치", "hex": "#FFCBA4"},
        ],
        "avoid_reason": "가볍고 따뜻한 색이 대비감 없이 떠 보여요.",
        "lip_direction": "어둡고 강렬한 쿨 계열.",
        "cheek_direction": "깊은 쿨빛 혈색.",
        "eye_direction": "강렬한 대비감. 스모키 최적.",
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
    """특정 계절+서브타입의 팔레트를 반환한다."""
    key = f"{season}_{subtype}"
    return SEASON_PALETTES.get(key, SEASON_PALETTES["spring_light"])


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
