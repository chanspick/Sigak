# SIGAK 스킨톤 모듈 심화 설계서

> Version: 1.0 | 2026-04-10
> 목표: 6타입(warm/neutral/cool × clear/soft) → 4계절 × 서브타입(라이트/브라이트/뮤트/딥)
> 핵심: 백지 레퍼런스 촬영 → 화이트밸런스 캘리브레이션 → 정밀 LAB 측정

---

## 1. 현재 시스템의 문제

### 1-1. 측정 오차 원인

| 원인 | 영향 | 현재 대응 |
|------|------|---------|
| 조명 색온도 | warmth 값 전체가 시프트 (화사가 neutral로 나온 이유) | 없음 |
| 카메라 화이트밸런스 | 기기마다 다른 색 보정 | 없음 |
| 피부 ROI 부족 | 볼 2점만 샘플링 → 국소적 편향 | 볼 2점 |
| CENTER/STD 추정치 | SCUT 추정 → 셀럽 42장 실측으로 교정했지만 아직 불안정 | CENTER=13, STD=9.5 |
| 사진 포맷 | avif/webp에서 색공간 깨짐 | 미대응 (6장 실패) |

### 1-2. 분류 체계 한계

현재 6타입:
```
warm_clear / warm_soft / neutral_clear / neutral_soft / cool_clear / cool_soft
```

문제:
- warmth z-score 하나로 웜/쿨 이분법 → 나무위키에서 말한 "웜쿨보다 명채도가 중요한 사람" 미반영
- neutral 43%가 과다 → 변별력 없음
- 4계절(봄/여름/가을/겨울)로의 매핑 불가
- 서브타입(라이트/브라이트/뮤트/딥) 정보 없음

---

## 2. 백지 캘리브레이션 시스템

### 2-1. 촬영 프로토콜

```
유저에게 요구하는 사진 2장:

[사진 1] 얼굴 정면 (기존)
  - 쌩얼 올빽
  - 자연광 (창가, 직사광 아님)
  - 정면 응시

[사진 2] 얼굴 + 백지 (신규)
  - A4 백지를 턱 아래~가슴 높이에 수평으로 들고 촬영
  - 백지가 얼굴과 같은 조명을 받도록 (그림자 X)
  - 얼굴과 백지가 한 프레임에 동시 포함

  또는 (간소화 버전):
  - 사진 1장만 받되, "흰색 상의를 입고 찍어주세요" 가이드
  - 어깨 영역에서 흰색 참조점 추출
```

### 2-2. 화이트밸런스 캘리브레이션 알고리즘

```python
import cv2
import numpy as np

class WhiteBalanceCalibrator:
    """
    백지 영역의 LAB 값을 측정하여 조명 색온도를 역산,
    피부 LAB 값을 조명-독립적으로 보정.
    """
    
    # 이상적 백지의 LAB 값 (D65 표준 조명 하)
    IDEAL_WHITE_LAB = np.array([100.0, 0.0, 0.0])  # L=100, a=0, b=0
    
    def detect_white_reference(self, image_bgr, face_landmarks):
        """
        백지 영역 자동 검출.
        
        전략:
        1. 얼굴 바운딩박스 아래 영역에서 흰색 영역 탐색
        2. 또는 어깨/상의 영역에서 고명도+저채도 영역 탐색
        """
        face_bbox = get_face_bbox(face_landmarks)
        
        # 얼굴 아래 영역 (턱~이미지 하단의 상위 1/3)
        search_y_start = face_bbox.bottom
        search_y_end = min(face_bbox.bottom + face_bbox.height, image_bgr.shape[0])
        search_region = image_bgr[search_y_start:search_y_end, :]
        
        # LAB 변환
        search_lab = cv2.cvtColor(search_region, cv2.COLOR_BGR2LAB)
        
        # 흰색 조건: L > 200 (8bit LAB에서), |a-128| < 15, |b-128| < 15
        white_mask = (
            (search_lab[:, :, 0] > 200) &
            (np.abs(search_lab[:, :, 1].astype(int) - 128) < 15) &
            (np.abs(search_lab[:, :, 2].astype(int) - 128) < 15)
        )
        
        if white_mask.sum() < 500:  # 최소 500px 이상이어야 유효
            return None  # 백지 감지 실패 → 캘리브레이션 불가, 폴백
        
        # 흰색 영역의 평균 LAB
        white_pixels = search_lab[white_mask]
        measured_white = np.mean(white_pixels, axis=0)
        
        return measured_white  # [L, a, b] in 8bit LAB
    
    def calibrate(self, skin_lab_8bit, measured_white_8bit):
        """
        측정된 백지 LAB vs 이상적 백지 LAB의 차이로
        피부 LAB를 보정.
        
        원리:
        - 백지가 (L=95, a=130, b=135)로 측정됨
        - 이상적 백지는 (L=100, a=128, b=128)
        - 차이: ΔL=-5, Δa=+2, Δb=+7
        - → 조명이 약간 어둡고(ΔL) 노란빛(Δb>0)
        - → 피부 LAB에서 이 편차를 역보정
        """
        # 8bit LAB → float LAB
        measured_white = np.array([
            measured_white_8bit[0] / 255 * 100,  # L: 0-255 → 0-100
            measured_white_8bit[1] - 128,          # a: 128-center → signed
            measured_white_8bit[2] - 128,          # b: 128-center → signed
        ])
        
        # 보정 벡터 (이상적 - 측정)
        correction = self.IDEAL_WHITE_LAB - measured_white
        
        # 피부 LAB 보정
        skin_float = np.array([
            skin_lab_8bit[0] / 255 * 100,
            skin_lab_8bit[1] - 128,
            skin_lab_8bit[2] - 128,
        ])
        
        # L은 비율 보정, a/b는 절대 보정
        calibrated = np.array([
            skin_float[0] * (100.0 / max(measured_white[0], 1)),  # 명도: 비율
            skin_float[1] + correction[1],                         # a: 절대 이동
            skin_float[2] + correction[2],                         # b: 절대 이동
        ])
        
        return calibrated  # [L, a, b] in float LAB
    
    def get_calibration_confidence(self, measured_white_8bit):
        """
        캘리브레이션 신뢰도.
        백지가 이상적 흰색에서 얼마나 벗어났는지로 판단.
        """
        deviation = np.sqrt(
            ((measured_white_8bit[0] / 255 * 100) - 100) ** 2 +
            (measured_white_8bit[1] - 128) ** 2 +
            (measured_white_8bit[2] - 128) ** 2
        )
        
        # deviation 0 = 완벽 → confidence 1.0
        # deviation 30+ = 극단적 조명 → confidence < 0.5
        confidence = max(0, 1 - deviation / 30)
        
        return round(confidence, 2)
```

### 2-3. 확장 피부 ROI (2점 → 6점)

```python
class SkinROIExtractor:
    """
    InsightFace landmarks_2d_106에서 피부 샘플링 포인트 6개 추출.
    각 포인트에서 5×5 영역 평균 LAB 측정.
    """
    
    ROI_POINTS = {
        "forehead_center": {
            "landmarks": [10],  # 이마 중앙
            "offset": (0, -15),  # 헤어라인 방향으로 올림
            "weight": 0.15,
        },
        "left_cheek": {
            "landmarks": [36, 37],  # 왼쪽 볼 중앙
            "offset": (0, 0),
            "weight": 0.25,  # 볼이 가장 대표적
        },
        "right_cheek": {
            "landmarks": [42, 43],  # 오른쪽 볼 중앙
            "offset": (0, 0),
            "weight": 0.25,
        },
        "nose_side_left": {
            "landmarks": [50],  # 코 옆 왼쪽
            "offset": (-8, 0),
            "weight": 0.1,
        },
        "nose_side_right": {
            "landmarks": [52],  # 코 옆 오른쪽
            "offset": (8, 0),
            "weight": 0.1,
        },
        "jaw_center": {
            "landmarks": [16],  # 턱 중앙 위
            "offset": (0, -10),
            "weight": 0.15,
        },
    }
    
    def extract(self, image_lab, landmarks):
        """
        6개 ROI에서 가중 평균 LAB 추출.
        이상치(홍조, 점, 그림자) 제거 포함.
        """
        samples = []
        
        for name, config in self.ROI_POINTS.items():
            # 랜드마크에서 좌표 계산
            center = self._get_center(landmarks, config["landmarks"], config["offset"])
            
            # 5×5 패치 추출
            patch = self._extract_patch(image_lab, center, size=5)
            
            if patch is None:
                continue
            
            # 이상치 제거 (IQR 기반)
            cleaned = self._remove_outliers(patch)
            
            if len(cleaned) < 10:  # 유효 픽셀 부족
                continue
            
            mean_lab = np.mean(cleaned, axis=0)
            samples.append({
                "name": name,
                "lab": mean_lab,
                "weight": config["weight"],
            })
        
        # 가중 평균
        if not samples:
            return None
        
        total_weight = sum(s["weight"] for s in samples)
        weighted_lab = sum(s["lab"] * s["weight"] for s in samples) / total_weight
        
        # ROI 간 편차 (조명 불균일 감지)
        lab_std = np.std([s["lab"] for s in samples], axis=0)
        uniformity = 1.0 - min(np.mean(lab_std) / 10, 1.0)
        
        return {
            "mean_lab": weighted_lab,
            "samples": samples,
            "uniformity": uniformity,  # 0~1, 높을수록 조명 균일
        }
```

---

## 3. 4계절 × 서브타입 분류 시스템

### 3-1. PCCS 기반 분류 체계

나무위키 + 업계 표준 정리:

```
봄 (Spring) — 웜톤, 화사한
  ├ 봄 라이트 (Spring Light) — 고명도, 저~중채도, 웜
  └ 봄 브라이트 (Spring Bright) — 중~고명도, 고채도, 웜

여름 (Summer) — 쿨톤, 청량한
  ├ 여름 라이트 (Summer Light) — 고명도, 저~중채도, 쿨
  └ 여름 뮤트 (Summer Mute) — 중명도, 저채도, 쿨

가을 (Autumn) — 웜톤, 차분한
  ├ 가을 뮤트 (Autumn Mute) — 중명도, 저채도, 웜
  └ 가을 딥 (Autumn Deep) — 저명도, 중~고채도, 웜

겨울 (Winter) — 쿨톤, 강렬한
  ├ 겨울 브라이트 (Winter Bright) — 중~고명도, 고채도, 쿨
  └ 겨울 딥 (Winter Deep) — 저명도, 중~고채도, 쿨
```

### 3-2. LAB → 4계절 매핑 로직

```python
from enum import Enum
from dataclasses import dataclass

class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

class SubType(Enum):
    LIGHT = "light"
    BRIGHT = "bright"
    MUTE = "mute"
    DEEP = "deep"

@dataclass
class PersonalColorResult:
    season: Season
    subtype: SubType
    label_kr: str           # "봄 라이트"
    warmth: float           # 원시 warmth 값
    brightness: float       # 명도 (L)
    chroma: float           # 채도
    confidence: float       # 0~1
    calibrated: bool        # 백지 캘리브레이션 적용 여부
    
    # 추천 팔레트
    recommended_colors: list  # hex 4~6개
    avoid_colors: list        # hex 3~4개
    
    # 화장품 가이드
    foundation_tone: str    # "21호 웜" / "23호 쿨" 등
    lip_direction: str      # "코랄/피치 계열" / "로즈/베리 계열"
    cheek_direction: str    # "피치/살구" / "로즈/핑크"


class PersonalColorClassifier:
    """
    캘리브레이션된 LAB → 4계절 × 서브타입 분류.
    
    분류 축 3개:
    1. Warmth (웜/쿨) — LAB의 b(황청) + a(적녹) 조합
    2. Brightness (명도) — LAB의 L
    3. Chroma (채도) — LAB의 a² + b² 벡터 크기
    
    이 3축의 조합으로 8타입 분류.
    """
    
    # ── 캘리브레이션된 기준값 (셀럽 데이터 + 유저 데이터 축적 후 업데이트) ──
    
    # Warmth 기준
    # warmth = b + a * 0.5 (기존 공식 유지)
    # 캘리브레이션 후에는 CENTER를 0에 가깝게 설정 가능
    # (백지 보정이 조명 편향을 제거하므로)
    _WARMTH_CENTER_CALIBRATED = 5.0   # 캘리브레이션된 경우
    _WARMTH_CENTER_UNCALIBRATED = 13.0  # 미캘리브레이션 (기존)
    _WARMTH_STD = 9.5
    
    # Brightness 기준 (L값, 0-100 스케일)
    _BRIGHTNESS_HIGH = 68    # 고명도 기준
    _BRIGHTNESS_LOW = 55     # 저명도 기준
    
    # Chroma 기준
    _CHROMA_HIGH = 18        # 고채도 기준
    _CHROMA_LOW = 10         # 저채도 기준
    
    def classify(self, calibrated_lab, is_calibrated=True):
        """
        메인 분류 함수.
        
        Args:
            calibrated_lab: [L, a, b] float LAB (캘리브레이션 적용 시 보정됨)
            is_calibrated: 백지 캘리브레이션 적용 여부
        """
        L, a, b = calibrated_lab
        
        # ── 3축 계산 ──
        warmth = b + a * 0.5
        brightness = L
        chroma = np.sqrt(a**2 + b**2)
        
        center = (self._WARMTH_CENTER_CALIBRATED if is_calibrated 
                  else self._WARMTH_CENTER_UNCALIBRATED)
        warmth_z = (warmth - center) / self._WARMTH_STD
        
        # ── 1차: 웜/쿨 판정 ──
        is_warm = warmth_z > 0.3
        is_cool = warmth_z < -0.3
        is_neutral = not is_warm and not is_cool
        
        # ── 2차: 명도/채도 판정 ──
        is_bright_skin = brightness > self._BRIGHTNESS_HIGH
        is_dark_skin = brightness < self._BRIGHTNESS_LOW
        is_high_chroma = chroma > self._CHROMA_HIGH
        is_low_chroma = chroma < self._CHROMA_LOW
        
        # ── 3차: 4계절 × 서브타입 결정 ──
        season, subtype = self._determine_type(
            is_warm, is_cool, is_neutral,
            is_bright_skin, is_dark_skin,
            is_high_chroma, is_low_chroma,
            warmth_z, brightness, chroma
        )
        
        # ── 신뢰도 계산 ──
        confidence = self._calculate_confidence(
            warmth_z, brightness, chroma, is_calibrated
        )
        
        return PersonalColorResult(
            season=season,
            subtype=subtype,
            label_kr=self._get_korean_label(season, subtype),
            warmth=warmth,
            brightness=brightness,
            chroma=chroma,
            confidence=confidence,
            calibrated=is_calibrated,
            recommended_colors=self._get_palette(season, subtype, "recommended"),
            avoid_colors=self._get_palette(season, subtype, "avoid"),
            foundation_tone=self._get_foundation_guide(brightness, warmth_z),
            lip_direction=self._get_lip_guide(season, subtype),
            cheek_direction=self._get_cheek_guide(season, subtype),
        )
    
    def _determine_type(self, is_warm, is_cool, is_neutral,
                        is_bright_skin, is_dark_skin,
                        is_high_chroma, is_low_chroma,
                        warmth_z, brightness, chroma):
        """
        분류 결정 트리.
        
        나무위키 PCCS 기반:
        - 봄: 웜 + (고명도 or 고채도)
        - 여름: 쿨 + (고명도 or 저채도)
        - 가을: 웜 + (저채도 or 저명도)
        - 겨울: 쿨 + (고채도 or 저명도)
        
        Neutral 처리:
        - neutral은 명채도 패턴으로 계절 결정
        - 명도 높고 채도 낮으면 → 여름라이트/봄라이트 중 warmth_z 부호로
        - 명도 낮고 채도 높으면 → 겨울딥/가을딥 중 warmth_z 부호로
        """
        
        if is_warm:
            # 웜톤 → 봄 or 가을
            if is_bright_skin and is_high_chroma:
                return Season.SPRING, SubType.BRIGHT    # 봄 브라이트
            elif is_bright_skin:
                return Season.SPRING, SubType.LIGHT     # 봄 라이트
            elif is_dark_skin:
                return Season.AUTUMN, SubType.DEEP      # 가을 딥
            elif is_low_chroma:
                return Season.AUTUMN, SubType.MUTE      # 가을 뮤트
            elif is_high_chroma:
                return Season.SPRING, SubType.BRIGHT    # 봄 브라이트
            else:
                # 중간 → warmth 강도로 판단
                if warmth_z > 0.8:
                    return Season.AUTUMN, SubType.MUTE  # 강한 웜 + 중간 = 가을
                else:
                    return Season.SPRING, SubType.LIGHT  # 약한 웜 + 중간 = 봄
        
        elif is_cool:
            # 쿨톤 → 여름 or 겨울
            if is_bright_skin and is_low_chroma:
                return Season.SUMMER, SubType.LIGHT     # 여름 라이트
            elif is_bright_skin and is_high_chroma:
                return Season.WINTER, SubType.BRIGHT    # 겨울 브라이트
            elif is_dark_skin:
                return Season.WINTER, SubType.DEEP      # 겨울 딥
            elif is_low_chroma:
                return Season.SUMMER, SubType.MUTE      # 여름 뮤트
            elif is_high_chroma:
                return Season.WINTER, SubType.BRIGHT    # 겨울 브라이트
            else:
                if warmth_z < -0.8:
                    return Season.WINTER, SubType.DEEP  # 강한 쿨 = 겨울
                else:
                    return Season.SUMMER, SubType.MUTE  # 약한 쿨 = 여름
        
        else:
            # Neutral → 명채도 패턴으로 결정
            # "웜쿨보다 명채도가 더 중요한 사람"이 여기에 해당
            if is_bright_skin:
                if warmth_z >= 0:
                    return Season.SPRING, SubType.LIGHT
                else:
                    return Season.SUMMER, SubType.LIGHT
            elif is_dark_skin:
                if warmth_z >= 0:
                    return Season.AUTUMN, SubType.DEEP
                else:
                    return Season.WINTER, SubType.DEEP
            elif is_low_chroma:
                if warmth_z >= 0:
                    return Season.AUTUMN, SubType.MUTE
                else:
                    return Season.SUMMER, SubType.MUTE
            elif is_high_chroma:
                if warmth_z >= 0:
                    return Season.SPRING, SubType.BRIGHT
                else:
                    return Season.WINTER, SubType.BRIGHT
            else:
                # 완전 중간 → warmth 미세 부호로 결정
                if warmth_z >= 0:
                    return Season.SPRING, SubType.LIGHT
                else:
                    return Season.SUMMER, SubType.LIGHT
    
    def _calculate_confidence(self, warmth_z, brightness, chroma, is_calibrated):
        """
        분류 신뢰도.
        
        경계선에 가까울수록 낮음.
        캘리브레이션 안 됐으면 기본 -0.2.
        """
        # warmth 경계 거리 (|z| = 0.3이 경계)
        warmth_dist = abs(abs(warmth_z) - 0.3) / 0.3
        
        # 명도 경계 거리
        brightness_dist = min(
            abs(brightness - self._BRIGHTNESS_HIGH),
            abs(brightness - self._BRIGHTNESS_LOW)
        ) / 10
        
        # 채도 경계 거리
        chroma_dist = min(
            abs(chroma - self._CHROMA_HIGH),
            abs(chroma - self._CHROMA_LOW)
        ) / 5
        
        base = min(warmth_dist, brightness_dist, chroma_dist)
        base = max(0.1, min(base, 1.0))
        
        if not is_calibrated:
            base *= 0.7  # 캘리브레이션 없으면 30% 감소
        
        return round(base, 2)
    
    # ── 라벨 ──
    
    LABELS = {
        (Season.SPRING, SubType.LIGHT): "봄 라이트",
        (Season.SPRING, SubType.BRIGHT): "봄 브라이트",
        (Season.SUMMER, SubType.LIGHT): "여름 라이트",
        (Season.SUMMER, SubType.MUTE): "여름 뮤트",
        (Season.AUTUMN, SubType.MUTE): "가을 뮤트",
        (Season.AUTUMN, SubType.DEEP): "가을 딥",
        (Season.WINTER, SubType.BRIGHT): "겨울 브라이트",
        (Season.WINTER, SubType.DEEP): "겨울 딥",
    }
```

### 3-3. 설문 보정 (사진 + 설문 교차 검증)

```python
class SurveyCalibrator:
    """
    사진 분석 결과를 설문으로 교차 검증/보정.
    
    사진만으로는 경계선 케이스가 불안정하므로,
    설문 3~4문항으로 분류 확신도를 높임.
    """
    
    QUESTIONS = [
        {
            "id": "metal",
            "question": "골드와 실버 액세서리 중 어느 쪽이 더 어울린다는 말을 듣나요?",
            "options": [
                {"label": "골드", "warm_score": +0.3},
                {"label": "실버", "cool_score": +0.3},
                {"label": "둘 다 / 모르겠다", "score": 0},
            ]
        },
        {
            "id": "vein",
            "question": "손목 안쪽 혈관 색이 어떤가요?",
            "options": [
                {"label": "초록빛", "warm_score": +0.2},
                {"label": "보라/파란빛", "cool_score": +0.2},
                {"label": "섞여 있다", "score": 0},
            ]
        },
        {
            "id": "lip_test",
            "question": "오렌지 립 vs 핑크 립, 어디가 더 자연스러운가요?",
            "options": [
                {"label": "오렌지가 자연스럽다", "warm_score": +0.25},
                {"label": "핑크가 자연스럽다", "cool_score": +0.25},
                {"label": "둘 다 괜찮다", "score": 0},
            ]
        },
        {
            "id": "white_test",
            "question": "순백색 vs 아이보리색 옷, 어느 쪽이 얼굴이 화사해 보이나요?",
            "options": [
                {"label": "아이보리", "warm_score": +0.2},
                {"label": "순백색", "cool_score": +0.2},
                {"label": "차이 모르겠다", "score": 0},
            ]
        },
    ]
    
    def adjust(self, photo_result: PersonalColorResult, survey_answers: dict):
        """
        사진 기반 warmth_z에 설문 스코어를 가산하여 최종 판정.
        
        설문이 사진과 일치하면 confidence 상승.
        설문이 사진과 반대면 재분류 트리거.
        """
        survey_warmth = sum(
            self._get_score(q, survey_answers.get(q["id"]))
            for q in self.QUESTIONS
        )
        
        # 사진 warmth_z와 설문 방향 비교
        photo_direction = "warm" if photo_result.warmth > 0 else "cool"
        survey_direction = "warm" if survey_warmth > 0 else "cool"
        
        if photo_direction == survey_direction:
            # 일치 → confidence 상승
            adjusted_confidence = min(photo_result.confidence + 0.15, 1.0)
            return photo_result._replace(confidence=adjusted_confidence)
        else:
            # 불일치 → 경계선 케이스일 가능성
            # warmth_z를 설문 방향으로 보정
            adjusted_warmth_z = photo_result.warmth + survey_warmth * self._WARMTH_STD * 0.3
            # 재분류
            return self.classifier.classify_with_adjusted_warmth(adjusted_warmth_z)
```

---

## 4. 화장품 발색 가이드

### 4-1. 파운데이션 매칭

```python
class FoundationGuide:
    """
    피부 명도(L) + 웜쿨 → 파운데이션 호수/톤 추천.
    """
    
    # 한국 파운데이션 호수 매핑 (대략적)
    FOUNDATION_MAP = {
        # (명도 범위, 웜쿨) → 호수
        "bright_warm": {"호수": "13~17호", "톤": "웜", "예시": "13W, 17W"},
        "bright_cool": {"호수": "13~17호", "톤": "쿨", "예시": "13C, 17C"},
        "medium_warm": {"호수": "21~23호", "톤": "웜", "예시": "21W, 23W"},
        "medium_cool": {"호수": "21~23호", "톤": "쿨", "예시": "21C, 23C"},
        "dark_warm":   {"호수": "25~27호", "톤": "웜", "예시": "25W, 27W"},
        "dark_cool":   {"호수": "25~27호", "톤": "쿨", "예시": "25C, 27C"},
    }
    
    def recommend(self, brightness, warmth_z):
        if brightness > 68:
            level = "bright"
        elif brightness > 55:
            level = "medium"
        else:
            level = "dark"
        
        tone = "warm" if warmth_z > 0 else "cool"
        key = f"{level}_{tone}"
        
        return self.FOUNDATION_MAP[key]
```

### 4-2. 색조 화장품 방향 가이드

```python
SEASON_MAKEUP_GUIDE = {
    (Season.SPRING, SubType.LIGHT): {
        "lip": {
            "best": ["코랄 핑크", "피치", "살몬"],
            "ok": ["라이트 오렌지", "누드 핑크"],
            "avoid": ["버건디", "딥 레드", "와인"],
            "direction": "밝고 따뜻한 색조. 피부보다 약간 선명한 정도.",
        },
        "cheek": {
            "best": ["피치", "라이트 코랄"],
            "direction": "살구빛 혈색. 자연스러운 화사함.",
        },
        "eye_shadow": {
            "best": ["코랄", "피치", "라이트 브라운"],
            "avoid": ["쿨 그레이", "네이비", "퍼플"],
            "direction": "따뜻한 명색 계열. 펄은 골드 펄.",
        },
    },
    (Season.SUMMER, SubType.LIGHT): {
        "lip": {
            "best": ["로즈 핑크", "베이비 핑크", "라벤더 핑크"],
            "ok": ["쿨 누드", "소프트 레드"],
            "avoid": ["오렌지", "브릭", "테라코타"],
            "direction": "차갑고 밝은 핑크 계열. 부드러운 발색.",
        },
        "cheek": {
            "best": ["로즈", "쿨 핑크"],
            "direction": "청량한 핑크빛 혈색.",
        },
        "eye_shadow": {
            "best": ["로즈", "라벤더", "쿨 브라운"],
            "avoid": ["웜 브라운", "골드", "카키"],
            "direction": "시원한 톤의 명색. 펄은 실버/핑크 펄.",
        },
    },
    (Season.AUTUMN, SubType.MUTE): {
        "lip": {
            "best": ["테라코타", "브릭 레드", "머스타드 누드"],
            "ok": ["딥 코랄", "브라운 레드"],
            "avoid": ["핫 핑크", "네온", "쿨 레드"],
            "direction": "탁하고 깊은 웜 계열. 차분한 발색.",
        },
        "cheek": {
            "best": ["브라운 피치", "테라코타"],
            "direction": "은은한 흙빛 혈색. 자연스럽게.",
        },
        "eye_shadow": {
            "best": ["카키", "머스타드", "웜 브라운"],
            "avoid": ["쿨 핑크", "실버", "네온"],
            "direction": "내추럴 어스톤. 펄은 골드/브론즈.",
        },
    },
    (Season.AUTUMN, SubType.DEEP): {
        "lip": {
            "best": ["버건디", "딥 브라운 레드", "다크 코랄"],
            "ok": ["와인", "초콜릿"],
            "avoid": ["파스텔 핑크", "라벤더", "네온"],
            "direction": "깊고 진한 웜 계열. 무게감 있는 발색.",
        },
        "cheek": {
            "best": ["플럼", "딥 코랄"],
            "direction": "깊은 혈색. 피부와 대비 살리기.",
        },
        "eye_shadow": {
            "best": ["다크 브라운", "올리브", "버건디"],
            "avoid": ["파스텔", "실버", "하늘색"],
            "direction": "깊은 어스톤. 스모키에 강함.",
        },
    },
    (Season.WINTER, SubType.BRIGHT): {
        "lip": {
            "best": ["체리 레드", "핫 핑크", "비비드 레드"],
            "ok": ["푸시아", "쿨 오렌지"],
            "avoid": ["누드", "살몬", "코랄"],
            "direction": "선명하고 쨍한 쿨 계열. 대비감 극대화.",
        },
        "cheek": {
            "best": ["비비드 핑크", "쿨 레드"],
            "direction": "선명한 대비. 피부 밝기와 대비 강조.",
        },
        "eye_shadow": {
            "best": ["실버", "네이비", "비비드 퍼플"],
            "avoid": ["웜 브라운", "골드", "카키"],
            "direction": "쨍한 쿨 계열. 글리터는 실버.",
        },
    },
    (Season.WINTER, SubType.DEEP): {
        "lip": {
            "best": ["와인", "딥 퍼플", "다크 체리"],
            "ok": ["딥 레드", "블랙 레드"],
            "avoid": ["파스텔", "코랄", "피치"],
            "direction": "어둡고 강렬한 쿨 계열.",
        },
        "cheek": {
            "best": ["딥 로즈", "다크 플럼"],
            "direction": "깊은 쿨빛 혈색.",
        },
        "eye_shadow": {
            "best": ["블랙", "다크 네이비", "딥 퍼플"],
            "avoid": ["웜 브라운", "골드", "파스텔"],
            "direction": "강렬한 대비감. 스모키 최적.",
        },
    },
    (Season.SUMMER, SubType.MUTE): {
        "lip": {
            "best": ["모브", "더스티 로즈", "쿨 누드"],
            "ok": ["밀키 핑크", "소프트 레드"],
            "avoid": ["오렌지", "비비드 레드", "테라코타"],
            "direction": "탁하고 부드러운 쿨 계열. 과하지 않은 발색.",
        },
        "cheek": {
            "best": ["더스티 핑크", "모브"],
            "direction": "안개 낀 듯 은은한 쿨 혈색.",
        },
        "eye_shadow": {
            "best": ["더스티 핑크", "모브", "그레이 브라운"],
            "avoid": ["비비드", "골드", "네온"],
            "direction": "뮤트 톤 전체. 펄은 핑크/라벤더.",
        },
    },
    (Season.SPRING, SubType.BRIGHT): {
        "lip": {
            "best": ["비비드 코랄", "브라이트 오렌지", "웜 레드"],
            "ok": ["비비드 핑크(웜)", "선명한 피치"],
            "avoid": ["버건디", "다크 브라운", "뮤트 톤"],
            "direction": "선명하고 밝은 웜 계열. 화사한 생기.",
        },
        "cheek": {
            "best": ["브라이트 코랄", "비비드 피치"],
            "direction": "선명한 웜 혈색. 건강하고 화사하게.",
        },
        "eye_shadow": {
            "best": ["코랄", "오렌지", "밝은 골드"],
            "avoid": ["그레이", "뮤트 톤", "다크 컬러"],
            "direction": "밝고 선명한 웜. 글리터는 골드.",
        },
    },
}
```

---

## 5. 리포트 출력 스펙 (추후 스킨톤+패션 +10p에 포함)

### 5-1. 스킨톤 결과 페이지 (2p)

**p1: 퍼스널 컬러 진단 결과**

```
┌──────────────────────────────────────────┐
│                                          │
│  SKIN TONE ANALYSIS                      │
│                                          │
│  ┌─────────────────────────────────┐     │
│  │                                 │     │
│  │  [PCCS 명채도 맵]               │     │
│  │  x = 채도 (저→고)               │     │
│  │  y = 명도 (저→고)               │     │
│  │  ● = 당신의 위치                 │     │
│  │  색상 영역으로 4계절 구분          │     │
│  │                                 │     │
│  └─────────────────────────────────┘     │
│                                          │
│  당신은                                   │
│  여름 뮤트 (Summer Mute)                  │
│                                          │
│  Warmth: Cool (-0.45)                    │
│  Brightness: Medium (62.3)               │
│  Chroma: Low (8.7)                       │
│  Confidence: 0.82 ✅                     │
│  (백지 캘리브레이션 적용)                    │
│                                          │
│  ─────────────────────────────────       │
│                                          │
│  추천 팔레트:                              │
│  [■ 더스티로즈] [■ 모브] [■ 쿨누드]         │
│  [■ 라벤더] [■ 소프트레드]                  │
│                                          │
│  피해야 할 색:                             │
│  [■ 오렌지] [■ 비비드레드] [■ 테라코타]      │
│                                          │
└──────────────────────────────────────────┘
```

**p2: 화장품 가이드**

```
┌──────────────────────────────────────────┐
│                                          │
│  COSMETIC GUIDE                          │
│                                          │
│  파운데이션                                │
│  → 21~23호 쿨 (21C~23C)                  │
│  → 핑크 베이스 권장                        │
│                                          │
│  립                                      │
│  BEST: 모브, 더스티 로즈, 쿨 누드           │
│  OK: 밀키 핑크, 소프트 레드                 │
│  AVOID: 오렌지, 비비드, 테라코타            │
│  → 탁하고 부드러운 쿨 계열. 과하지 않게.     │
│                                          │
│  치크                                    │
│  → 더스티 핑크, 모브                       │
│  → 안개 낀 듯 은은하게                     │
│                                          │
│  아이섀도우                                │
│  → 더스티 핑크, 모브, 그레이 브라운          │
│  → 펄은 핑크/라벤더                        │
│  → 골드/네온 절대 금지                     │
│                                          │
│  ⚠️ 사진 기반 추정치입니다.                 │
│  오프라인 드레이핑과 차이가 있을 수 있으며,    │
│  경계선(confidence < 0.6)인 경우            │
│  설문 결과를 우선 참고하시기 바랍니다.         │
│                                          │
└──────────────────────────────────────────┘
```

---

## 6. 파이프라인 통합

### 기존 face.py 수정 사항

```python
# face.py에서 변경되는 것:

# 1. skin_tone 6타입 분류 → PersonalColorClassifier로 교체
# 2. ROI 2점 → SkinROIExtractor 6점으로 교체
# 3. WhiteBalanceCalibrator 추가

# 기존 warmth/chroma 계산 로직은 유지하되,
# 캘리브레이션 레이어가 위에 얹힘

def analyze_skin(image_bgr, landmarks, white_reference_image=None):
    """
    통합 스킨톤 분석 함수.
    """
    calibrator = WhiteBalanceCalibrator()
    roi_extractor = SkinROIExtractor()
    classifier = PersonalColorClassifier()
    
    # 1. 화이트밸런스 캘리브레이션
    is_calibrated = False
    if white_reference_image is not None:
        measured_white = calibrator.detect_white_reference(
            white_reference_image, landmarks
        )
        if measured_white is not None:
            cal_confidence = calibrator.get_calibration_confidence(measured_white)
            if cal_confidence > 0.5:
                is_calibrated = True
    
    # 2. LAB 변환
    image_lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    
    # 3. 6점 ROI 추출
    roi_result = roi_extractor.extract(image_lab, landmarks)
    if roi_result is None:
        return None
    
    mean_lab_8bit = roi_result["mean_lab"]
    
    # 4. 캘리브레이션 적용
    if is_calibrated:
        calibrated_lab = calibrator.calibrate(mean_lab_8bit, measured_white)
    else:
        # 캘리브레이션 없이 기존 방식
        calibrated_lab = np.array([
            mean_lab_8bit[0] / 255 * 100,
            mean_lab_8bit[1] - 128,
            mean_lab_8bit[2] - 128,
        ])
    
    # 5. 4계절 분류
    result = classifier.classify(calibrated_lab, is_calibrated)
    
    # 6. 기존 6타입 호환 (하위 호환)
    legacy_6type = map_to_legacy_6type(result)
    
    return {
        "personal_color": result,
        "legacy_skin_tone": legacy_6type,
        "roi_uniformity": roi_result["uniformity"],
        "calibration": {
            "applied": is_calibrated,
            "confidence": cal_confidence if is_calibrated else 0,
        }
    }
```

---

## 7. 촬영 가이드 UI 스펙

```
┌──────────────────────────────────────────┐
│                                          │
│  📸 사진 촬영 가이드                       │
│                                          │
│  1. 쌩얼 상태에서 촬영해주세요               │
│     (선크림/보습제 OK, 색조 화장 X)         │
│                                          │
│  2. 머리를 완전히 올백으로 넘겨주세요         │
│                                          │
│  3. 자연광이 드는 창가에서 촬영               │
│     (직사광선 X, 형광등/백열등 X)            │
│                                          │
│  4. A4 백지를 턱 아래에 수평으로 대고         │
│     얼굴과 백지가 한 프레임에 나오게          │
│                                          │
│  [올바른 예시 ✅]    [잘못된 예시 ❌]         │
│  [사진]             [사진]                 │
│  자연광+백지         형광등+그림자            │
│                                          │
│  ℹ️ 백지가 없으면 흰색 상의도 가능합니다.     │
│     정확도가 약간 낮아질 수 있습니다.         │
│                                          │
└──────────────────────────────────────────┘
```

---

## 8. 빌드 순서

| 순서 | 항목 | 의존성 | 신규/수정 |
|------|------|------|---------|
| 1 | SkinROIExtractor (6점) | InsightFace landmarks | 신규 |
| 2 | WhiteBalanceCalibrator | 백지 사진 입력 | 신규 |
| 3 | PersonalColorClassifier (8타입) | 캘리브레이션된 LAB | 신규 |
| 4 | SurveyCalibrator (설문 보정) | 설문 UI | 신규 |
| 5 | 화장품 가이드 데이터 | 8타입별 팔레트 | 신규 |
| 6 | face.py 통합 | 위 1~3 | 수정 |
| 7 | 촬영 가이드 UI | 프론트 | 신규 |
| 8 | 리포트 렌더링 | 프론트 | 신규 |

---

## 9. 검증 계획

1. **셀럽 42장 재검증**: 새 분류기로 돌려서 잼페이스 분포(가을웜트루 22.3%, 여름쿨트루 21.3%)와 비교
2. **화사 테스트**: 캘리브레이션 유/무에서 웜톤으로 정확히 나오는지
3. **경계선 케이스**: neutral 영역 유저의 설문 보정 효과 측정
4. **유저 피드백**: "본인이 알고 있는 퍼컬"과 시스템 결과 일치율 추적