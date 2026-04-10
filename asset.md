# SIGAK 오버레이 에셋 제작 기획서

> 2026-04-10 | 총 37종 | InsightFace 106점 실측 기반

---

## 제작 개요

| 항목 | 내용 |
|------|------|
| 총 에셋 수 | 37종 (헤어 21 + 눈썹 5 + 속눈썹 2 + 블러셔 5 + 립 5) |
| 포맷 | PNG, RGBA (투명 배경) |
| 색상 기준 | dark brown (H:25 S:60 L:20) — 코드로 5색 변형 |
| 앵커 기준 | InsightFace 2d106det 실측 랜드마크 |

---

## A. 헤어 — 앞머리 (8종)

### 공통 규격
```
크기: 1024×512px
배경: 투명
시점: 정면 (유저 셀카와 동일 각도)
색상: dark brown 단색 기준 (코드로 변형)
앵커: 이미지 중앙 하단 = 미간 위치 [43-48] 🟠
정렬: 관자놀이 [17]↔[25] 간 거리로 스케일
```

### 개별 에셋

| ID | 파일명 | 설명 | 제작 방식 |
|----|--------|------|---------|
| H-F01 | bang_full.png | 이마 완전히 덮는 빽빽한 일자 앞머리. 눈썹 기장. 이마 0% 노출. | AI생성 → 배경제거 → 하단 페더링 |
| H-F02 | bang_seethrough.png | 이마 40% 비치는 가벼운 앞머리. 눈썹보다 살짝 긴 기장. 양끝으로 갈수록 숱 증가. | AI생성 → 배경제거. 투명도 그라디언트로 비침 표현 |
| H-F03 | bang_side55.png | 5:5 정가르마 사이드뱅. 인중~입술 기장. S컬. 좌우 대칭. | AI생성 → 배경제거. 정중앙 기준 좌우 대칭 확인 |
| H-F04 | bang_side_asym.png | 6:4 비대칭 사이드뱅. 입술 기장. 많은 쪽 S컬, 적은 쪽 귀 뒤. | AI생성 → 배경제거. 6쪽이 이미지 왼쪽(subject 오른쪽) |
| H-F05 | bang_jawline.png | 턱선 기장 사이드뱅. 한쪽 얼굴 감싸는 형태. 끝단 C컬. | AI생성 → 배경제거. 한쪽 광대~턱 완전 커버 |
| H-F06 | bang_curly.png | 잔컬 앞머리. 이마 중간 살짝 비침. 애교머리 느낌. | AI생성 → 배경제거. 컬 디테일 살리기 |
| H-F07 | bang_choppy.png | 눈썹 위 짧은 앞머리. 지그재그 끝단. | AI생성 → 배경제거 |
| H-F08 | bang_none.png | 투명 1×1px (no-op) | 수작업 |

### 제작 워크플로우
```
1. DeeVid/Midjourney: 프롬프트로 정면 여성 + 해당 뱅 스타일 생성
2. 얼굴/몸통 영역 마스킹 → 앞머리 영역만 추출
3. 배경 완전 투명 처리
4. 하단(이마 접합부): 5~10px 페더링으로 자연스러운 경계
5. 좌우 끝(관자놀이): 10~15px 페더링
6. 앵커 포인트 확인: 중앙 하단이 미간 위치에 오는지 테스트
```

---

## B. 헤어 — 뒷머리 (13종)

### 공통 규격
```
크기: 1024×1024px
배경: 투명
시점: 정면
색상: dark brown 단색 기준
앵커: 이미지 중앙 상단 1/3 = 정수리 추정 위치
정렬: 관자놀이 [17]↔[25] 중점, 거리 × 1.8로 스케일
z-order: 유저 사진 뒤 (레이어 1)
```

### 개별 에셋

| ID | 파일명 | 설명 | 핵심 포인트 |
|----|--------|------|-----------|
| H-B01 | back_short.png | 숏컷. 귓불 아래 안 보이는 기장. | 얼굴 옆~뒤만 커버. 어깨 노출 |
| H-B02 | back_bob_layered.png | 보브단발/레이어드. 턱선 기장. 둥근 실루엣. | 턱선에서 둥글게 마무리 |
| H-B03 | back_blunt_bob.png | 칼단발. 턱선 기장. 층/컬 없이 일자. | 끝단 완전 일자 |
| H-B04 | back_bob_cperm.png | 단발 굵은펌. 턱선 기장. C컬/굵은 S컬. | 턱 주변 볼륨감 |
| H-B05 | back_bob_scurl.png | 단발 S컬펌. 턱선 기장. 작은 S컬 강하게. | 강한 컬감, 넓은 실루엣 |
| H-B06 | back_mid_straight.png | 일자 중단발. 어깨~쇄골. 층/컬 없음. | 직선 끝단 |
| H-B07 | back_mid_layered.png | 중단발 레이어드. 쇄골 기장. 끝 3~4cm 층. | 끝단 가벼움, 여리여리 |
| H-B08 | back_mid_outcurl.png | 중단발 아웃C컬. 어깨 기장. 끝 바깥 C컬. | 끝단만 바깥으로 말림 |
| H-B09 | back_mid_perm.png | 중단발펌. 목~쇄골. 강한 S컬. | 목 주변 볼륨 큼 |
| H-B10 | back_long_straight.png | 긴 생머리. 가슴선. 컬 없음. | 길고 매끈한 직모 |
| H-B11 | back_long_perm.png | 긴머리펌. 가슴선. C컬/굵은 S컬. | 하단부 웨이브 |
| H-B12 | back_long_layered_perm.png | 긴머리 레이어드펌. 쇄골 아래 층 + C/S컬. | 층 + 컬 조합. 가벼운 느낌 |
| H-B13 | back_hippie_perm.png | 히피펌. 가슴선. 아주 작은 컬 강하게. | 부스스한 볼륨. 전체 넓은 실루엣 |

### 제작 워크플로우
```
1. AI 생성: 뒷머리 스타일 포함 정면 여성 이미지
2. 얼굴 영역 마스킹 → 얼굴 부분을 투명 처리 (도넛 형태)
   - 얼굴 윤곽 [0-32] 안쪽 = 투명
   - 바깥쪽 = 머리카락 유지
3. 상단(정수리): 자연스러운 페더링
4. 하단: 기장에 따라 다름 (단발=턱선, 긴머리=가슴선)
5. 핵심: 유저 사진 "뒤에" 깔리므로 얼굴 영역이 반드시 투명이어야 함
```

### ⚠️ 뒷머리 에셋의 특수 처리
```
뒷머리는 유저 사진 뒤에 깔리므로:
- 얼굴 영역: 완전 투명 (윤곽 [0-32] 기반 마스크)
- 귀 앞 사이드 머리: 반투명 처리 (유저 얼굴과 자연스럽게 블렌딩)
- 어깨 영역: 유저 옷이 보여야 하므로 머리카락만 남기고 투명

실제로는 "사이드 헤어"가 유저 사진 위에 와야 하는 경우도 있음.
→ back 에셋을 2레이어로 분리:
  - back_behind.png (레이어 1: 뒤쪽 머리)
  - back_side.png (레이어 2.5: 귀 앞 사이드, 유저 위에)
```

---

## C. 눈썹 (5종)

### 공통 규격
```
크기: 256×64px
배경: 투명
시점: 오른쪽 눈썹 기준 (왼쪽은 코드에서 flip)
색상: dark brown 단색 (코드로 변형, 헤어색 × 0.8)
앵커: 에셋 내 5개 컨트롤 포인트 → [38,39,40,41,42] 🟡에 정렬
```

### 개별 에셋

| ID | 파일명 | 형태 | 핵심 |
|----|--------|------|------|
| M-E01 | eb_strong_arch.png | 강한 아치형. 산 각도 sharp. 꼬리 2mm+ 높음. | 꺾임 강하게 |
| M-E02 | eb_semi_arch.png | 세미 아치형. 산 완만. 꼬리 0~2mm 높음. | 가장 범용적 형태 |
| M-E03 | eb_round_arch.png | 둥근 아치형. 곡선 부드러움. 산 거의 없음. | 둥글둥글 |
| M-E04 | eb_straight.png | 일자형. 수평. 산 없음. | 완전 일자 |
| M-E05 | eb_diagonal.png | 사선형. 앞머리→꼬리 사선 상승. | 시크한 각도 |

### 제작 워크플로우
```
1. Figma/Illustrator에서 벡터 드로잉 (가장 정밀)
   - 또는 AI 생성 눈썹 클로즈업 → 추출
2. 5개 컨트롤 포인트 마킹:
   - pt0: 눈썹 앞머리 (안쪽 끝)
   - pt1: 앞머리에서 1/4
   - pt2: 눈썹 산 (가장 높은 점)
   - pt3: 산에서 꼬리 중간
   - pt4: 눈썹 꼬리 (바깥 끝)
3. 컨트롤 포인트를 메타데이터로 저장 (JSON)
4. 두께: 중간 두께 기준 (코드에서 ±20% 스케일 가능)
```

### 컨트롤 포인트 메타데이터 예시
```json
{
  "eb_semi_arch": {
    "points": [[12,40], [64,28], [140,22], [200,30], [244,38]],
    "thickness_range": [6, 10]
  }
}
```

---

## D. 속눈썹 (2종)

### 공통 규격
```
크기: 256×64px
배경: 투명
시점: 오른쪽 눈 기준 (왼쪽은 flip)
색상: 블랙 고정
앵커: 눈 상단 곡선 5포인트 → [33,34,35,36,37] 🔵 상단에 정렬
```

| ID | 파일명 | 설명 |
|----|--------|------|
| M-L01 | lash_natural.png | 자연스러운 속눈썹. 중앙 약간 길고 양끝 짧음. |
| M-L02 | lash_dramatic.png | 볼륨 속눈썹. 전체적으로 길고 숱 많음. 꼬리쪽 강조. |

### 제작 워크플로우
```
1. Figma에서 벡터 (얇은 곡선 다발)
   - 또는 실제 인조속눈썹 사진 → 배경제거
2. 눈 곡선을 따라 배치되는 형태
3. 5포인트 컨트롤 마킹
```

---

## E. 블러셔 (5종)

### 공통 규격
```
크기: 512×512px
배경: 투명
형식: grayscale 마스크 (흰색 = 영역, 검정 = 투명)
적용: color × mask → multiply blend, opacity 30~50%
앵커: 코끝 [52] 기준 + 스타일별 offset
```

### 개별 에셋

| ID | 파일명 | 영역 형태 | offset (코끝 기준) |
|----|--------|---------|------------------|
| M-B01 | blush_center.png | 볼 중앙 원형. 동그란 블러셔. | dx=±0.18, dy=+0.02 |
| M-B02 | blush_diagonal.png | 광대 사선. 45도 타원형. | dx=±0.22, dy=-0.03 |
| M-B03 | blush_undereye.png | 눈 밑 가로로 길게. | dx=±0.12, dy=-0.04 |
| M-B04 | blush_noseside.png | 코 옆 세로로 길게. | dx=±0.08, dy=0 |
| M-B05 | blush_outer_vertical.png | 광대 바깥쪽 세로. | dx=±0.28, dy=-0.02 |

### 제작 워크플로우
```
1. Figma에서 제작 (가장 효율적)
   - 512×512 캔버스
   - 중앙 = 적용 기준점
   - 흰색 → 가우시안 블러 30~50px (자연스러운 경계)
2. 한쪽만 제작 (코드에서 좌우 대칭 배치)
3. 각 마스크의 "무게중심"이 offset과 일치하는지 확인
```

---

## F. 립 (5종)

### 공통 규격
```
크기: 256×128px
배경: 투명
형식: grayscale shape 마스크
적용: TPS warp → color × mask → soft light blend, opacity 60~80%
앵커: 20포인트 (윗입술 [55-59] + 아랫입술 [60-70])
```

### 개별 에셋

| ID | 파일명 | 형태 | 핵심 차이 |
|----|--------|------|---------|
| M-L01 | lip_full.png | 풀 립. 입술선 전체 100% fill. 경계 sharp. | 균일한 흰색, 경계 선명 |
| M-L02 | lip_over.png | 오버 립. 실제 입술선보다 1~2mm 확장. | 마스크가 입술보다 큼 |
| M-L03 | lip_gradient.png | 그라데이션 립. 중앙 100% → 경계 0%. | radial gradient |
| M-L04 | lip_glossy.png | 글로시 립. 전체 fill + 중앙 하이라이트 스팟. | 추가 밝은 영역 포함 |
| M-L05 | lip_matte.png | 매트 립. 전체 균일 fill. 하이라이트 없음. | lip_full과 유사, 텍스처 차이 |

### 제작 워크플로우
```
1. 기준 입술 형태 (평균적 한국 여성 입술) 벡터 드로잉
2. 20개 컨트롤 포인트 마킹
3. 스타일별 마스크 변형:
   - full: 입술 경계까지 흰색
   - over: 경계에서 2px 바깥까지 흰색
   - gradient: 중앙 → 경계 radial gradient
   - glossy: full + 중앙 하단에 밝은 타원 추가
   - matte: full과 동일 (blend mode에서 차이)
4. TPS warp가 형태를 유저 입술에 맞추므로, 에셋은 "평균 형태"로 제작
```

### 컨트롤 포인트 메타데이터 예시
```json
{
  "lip_full": {
    "upper": [[20,50], [60,30], [128,25], [196,30], [236,50]],
    "lower": [[20,50], [40,70], [70,90], [100,98], [128,100],
              [156,98], [186,90], [216,70], [236,50]],
    "total": 14
  }
}
```

---

## 제작 우선순위

```
Phase 1 — MVP (리포트 오버레이 작동 확인)
  ├─ bang_side_asym.png      ← TOP 추천 빈도 1위
  ├─ back_mid_layered.png    ← TOP 추천 빈도 1위
  ├─ eb_semi_arch.png        ← 가장 범용
  ├─ blush_center.png        ← 가장 범용
  └─ lip_gradient.png        ← 가장 범용
  → 5종으로 template_compositor.py E2E 테스트

Phase 2 — 헤어 풀셋
  ├─ 나머지 bang 7종
  └─ 나머지 back 12종

Phase 3 — 메이크업 풀셋
  ├─ 나머지 eyebrow 4종
  ├─ eyelash 2종
  ├─ 나머지 blusher 4종
  └─ 나머지 lip 4종
```

---

## 제작 도구

| 에셋 | 추천 도구 | 이유 |
|------|---------|------|
| 헤어 (bang + back) | DeeVid/Midjourney → Photoshop/GIMP 후처리 | 자연스러운 머리카락 질감은 AI가 우위 |
| 눈썹 | Figma 벡터 | 정밀한 형태 컨트롤 + 컨트롤 포인트 정확히 잡기 |
| 속눈썹 | Figma 벡터 | 얇은 선 다발 = 벡터가 깔끔 |
| 블러셔 마스크 | Figma | 단순 형태 + 가우시안 블러 |
| 립 마스크 | Figma | 단순 형태 + 그라디언트 |

---

## QA 체크리스트 (에셋별)

```
□ 투명 배경 확인 (RGBA, alpha 채널)
□ 규격 사이즈 정확 (±0px)
□ dark brown 기준 색상 (H:25 S:60 L:20 ±5)
□ 앵커/컨트롤 포인트 JSON 작성 완료
□ 테스트 사진 3장에 합성 → 자연스러움 확인
□ 페더링 경계 확인 (딱딱한 잘림 없음)
□ flip 테스트 (눈썹, 속눈썹: 좌우 반전 시 자연스러운지)
```

## compositor.py

'''
"""
SIGAK Template Compositor v1
에셋 기반 헤어/메이크업 오버레이 합성 엔진

InsightFace 2d106det 실측 랜드마크 기반
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ─────────────────────────────────────────────
# 1. 랜드마크 인덱스 (실측 확인)
# ─────────────────────────────────────────────

class LM:
"""InsightFace 106-point landmark indices"""
# 얼굴 윤곽
CONTOUR = list(range(0, 33))  # [0-32]

    # 관자놀이 (윤곽 상단)
    TEMPLE_R = 17   # subject 오른쪽 관자놀이 (이미지 왼쪽)
    TEMPLE_L = 25   # subject 왼쪽 관자놀이 (이미지 오른쪽)
    
    # 눈
    EYE_R = list(range(33, 38))     # [33-37] 오른쪽 눈
    EYE_L = list(range(83, 88))     # [83-87] 왼쪽 눈 (93까지 눈썹 포함)
    PUPIL_L = [94, 95]
    
    # 눈썹
    EYEBROW_R = list(range(38, 43))  # [38-42] 🟡
    EYEBROW_L = list(range(88, 93))  # [88-92] 🟣 상단부
    
    # 코
    NOSE_BRIDGE = list(range(43, 52))  # [43-51] 이마~미간
    NOSE_TIP = list(range(52, 55))     # [52-54]
    NOSE_FULL = list(range(71, 83))    # [71-82]
    
    # 이마
    FOREHEAD = list(range(96, 106))    # [96-105] 🟢 헤어라인
    FOREHEAD_MID = list(range(43, 49)) # [43-48] 🟠 미간~이마 중앙
    
    # 입술
    LIP_UPPER = list(range(55, 60))    # [55-59]
    LIP_LOWER = list(range(60, 71))    # [60-70]
    LIP_ALL = list(range(55, 71))


# ─────────────────────────────────────────────
# 2. 색상 유틸
# ─────────────────────────────────────────────

HAIR_COLORS = {
"black":       {"h": 25, "s": 30, "l": 10},
"dark_brown":  {"h": 25, "s": 60, "l": 20},
"brown":       {"h": 25, "s": 55, "l": 30},
"light_brown": {"h": 28, "s": 50, "l": 45},
"ash":         {"h": 35, "s": 30, "l": 35},
}

BLUSHER_PRESETS = {
"warm_pink":  {"h": 350, "s": 60, "l": 70},
"coral":      {"h": 15,  "s": 65, "l": 65},
"peach":      {"h": 25,  "s": 50, "l": 75},
"rose":       {"h": 340, "s": 55, "l": 60},
}

LIP_PRESETS = {
"mlbb":   {"h": 355, "s": 45, "l": 55},
"coral":  {"h": 10,  "s": 70, "l": 60},
"red":    {"h": 0,   "s": 80, "l": 45},
"rose":   {"h": 340, "s": 60, "l": 50},
"nude":   {"h": 20,  "s": 35, "l": 65},
}


def hsl_to_bgr(h: float, s: float, l: float) -> tuple:
"""HSL (h:0-360, s:0-100, l:0-100) → BGR"""
s /= 100
l /= 100
c = (1 - abs(2 * l - 1)) * s
x = c * (1 - abs((h / 60) % 2 - 1))
m = l - c / 2

    if h < 60:    r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x
    
    return (int((b + m) * 255), int((g + m) * 255), int((r + m) * 255))


def shift_asset_color(asset_bgra: np.ndarray, target_hsl: dict) -> np.ndarray:
"""
에셋(dark brown 기준)의 색조를 target HSL로 변환.
밝기 대비는 유지, H/S만 교체, L은 상대적 shift.
"""
result = asset_bgra.copy()
bgr = result[:, :, :3]
alpha = result[:, :, 3]

    # BGR → HLS (OpenCV: H 0-180, L 0-255, S 0-255)
    hls = cv2.cvtColor(bgr, cv2.COLOR_BGR2HLS).astype(np.float32)
    
    mask = alpha > 0
    
    # H 교체
    hls[:, :, 0][mask] = (target_hsl["h"] / 2) % 180  # OpenCV H = 0~180
    
    # S 교체
    hls[:, :, 2][mask] = target_hsl["s"] * 2.55  # 0~100 → 0~255
    
    # L: 원본 대비 유지하면서 target 기준으로 shift
    base_l = 20 * 2.55  # dark_brown base L
    target_l = target_hsl["l"] * 2.55
    l_shift = target_l - base_l
    hls[:, :, 1][mask] = np.clip(hls[:, :, 1][mask] + l_shift, 0, 255)
    
    result[:, :, :3] = cv2.cvtColor(hls.astype(np.uint8), cv2.COLOR_HLS2BGR)
    return result


# ─────────────────────────────────────────────
# 3. 에셋 로더
# ─────────────────────────────────────────────

@dataclass
class AssetMeta:
"""에셋 메타데이터"""
id: str
path: str
control_points: Optional[list] = None  # [[x,y], ...]
offset: Optional[dict] = None          # {"dx": float, "dy": float}


class AssetLoader:
def __init__(self, assets_dir: str):
self.dir = Path(assets_dir)
self._cache: dict[str, np.ndarray] = {}
self._meta: dict[str, AssetMeta] = {}
self._load_meta()

    def _load_meta(self):
        meta_path = self.dir / "meta.json"
        if meta_path.exists():
            with open(meta_path) as f:
                raw = json.load(f)
            for k, v in raw.items():
                self._meta[k] = AssetMeta(id=k, **v)
    
    def get(self, asset_id: str) -> np.ndarray:
        """BGRA 이미지 반환 (캐시)"""
        if asset_id not in self._cache:
            # 카테고리별 서브디렉토리 탐색
            for subdir in ["bang", "back", "eyebrow", "eyelash", "blusher", "lip"]:
                path = self.dir / subdir / f"{asset_id}.png"
                if path.exists():
                    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
                    if img is not None:
                        self._cache[asset_id] = img
                        break
            else:
                raise FileNotFoundError(f"Asset not found: {asset_id}")
        return self._cache[asset_id]
    
    def get_meta(self, asset_id: str) -> Optional[AssetMeta]:
        return self._meta.get(asset_id)


# ─────────────────────────────────────────────
# 4. 앵커 정렬
# ─────────────────────────────────────────────

class AnchorAligner:
"""랜드마크 기반 에셋 변환"""

    @staticmethod
    def get_face_angle(landmarks: np.ndarray) -> float:
        """두 눈 중심 기울기 (라디안)"""
        eye_r_center = landmarks[LM.EYE_R].mean(axis=0)
        eye_l_center = landmarks[LM.EYE_L].mean(axis=0)
        dy = eye_l_center[1] - eye_r_center[1]
        dx = eye_l_center[0] - eye_r_center[0]
        return math.atan2(dy, dx)
    
    @staticmethod
    def get_temple_width(landmarks: np.ndarray) -> float:
        """관자놀이 간 거리"""
        r = landmarks[LM.TEMPLE_R]
        l = landmarks[LM.TEMPLE_L]
        return np.linalg.norm(l - r)
    
    @staticmethod
    def get_forehead_center(landmarks: np.ndarray) -> np.ndarray:
        """이마 중앙점 (앞머리 앵커)"""
        pts = np.concatenate([
            landmarks[LM.FOREHEAD],      # [96-105]
            landmarks[LM.FOREHEAD_MID],   # [43-48]
        ])
        return pts.mean(axis=0)
    
    @staticmethod
    def get_crown_center(landmarks: np.ndarray) -> np.ndarray:
        """정수리 추정점 (뒷머리 앵커)"""
        r = landmarks[LM.TEMPLE_R]
        l = landmarks[LM.TEMPLE_L]
        mid = (r + l) / 2
        # 관자놀이 중점에서 위로 올림 (얼굴 높이의 30%)
        face_height = landmarks[LM.CONTOUR[8]][1] - mid[1]  # 턱 - 관자놀이
        mid[1] -= face_height * 0.3
        return mid
    
    @staticmethod
    def align_bang(
        asset: np.ndarray,
        landmarks: np.ndarray,
        canvas_shape: tuple,
        scale_factor: float = 1.3,
    ) -> np.ndarray:
        """앞머리 에셋을 유저 얼굴에 정렬"""
        h, w = asset.shape[:2]
        
        # 타겟 위치/크기
        center = AnchorAligner.get_forehead_center(landmarks)
        temple_w = AnchorAligner.get_temple_width(landmarks)
        target_w = temple_w * scale_factor
        angle = AnchorAligner.get_face_angle(landmarks)
        
        # 스케일
        scale = target_w / w
        
        # 변환 행렬: 에셋 중앙 하단 → center
        anchor_src = np.float32([w / 2, h])  # 에셋 앵커 (중앙 하단)
        
        M = cv2.getRotationMatrix2D(
            center=(float(center[0]), float(center[1])),
            angle=math.degrees(angle),
            scale=scale,
        )
        # translation 보정: 에셋 앵커가 center에 오도록
        tx = center[0] - anchor_src[0] * scale
        ty = center[1] - anchor_src[1] * scale
        M[0, 2] += tx
        M[1, 2] += ty
        
        canvas_h, canvas_w = canvas_shape[:2]
        result = cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )
        return result
    
    @staticmethod
    def align_back_hair(
        asset: np.ndarray,
        landmarks: np.ndarray,
        canvas_shape: tuple,
        scale_factor: float = 1.8,
    ) -> np.ndarray:
        """뒷머리 에셋 정렬 (유저 사진 뒤에 깔림)"""
        h, w = asset.shape[:2]
        
        center = AnchorAligner.get_crown_center(landmarks)
        temple_w = AnchorAligner.get_temple_width(landmarks)
        target_w = temple_w * scale_factor
        angle = AnchorAligner.get_face_angle(landmarks)
        
        scale = target_w / w
        anchor_src = np.float32([w / 2, h / 3])  # 에셋 앵커 (중앙 상단 1/3)
        
        M = cv2.getRotationMatrix2D(
            center=(float(center[0]), float(center[1])),
            angle=math.degrees(angle),
            scale=scale,
        )
        tx = center[0] - anchor_src[0] * scale
        ty = center[1] - anchor_src[1] * scale
        M[0, 2] += tx
        M[1, 2] += ty
        
        canvas_h, canvas_w = canvas_shape[:2]
        result = cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )
        return result
    
    @staticmethod
    def align_eyebrow(
        asset: np.ndarray,
        landmarks: np.ndarray,
        canvas_shape: tuple,
        side: str = "right",
    ) -> np.ndarray:
        """눈썹 에셋을 5포인트 어파인 정렬"""
        if side == "left":
            asset = cv2.flip(asset, 1)  # horizontal flip
            target_pts = landmarks[LM.EYEBROW_L]
        else:
            target_pts = landmarks[LM.EYEBROW_R]
        
        h, w = asset.shape[:2]
        
        # 에셋 5포인트 (좌→우 균등 분배)
        src_pts = np.float32([
            [w * 0.05, h * 0.6],
            [w * 0.25, h * 0.4],
            [w * 0.55, h * 0.3],
            [w * 0.78, h * 0.45],
            [w * 0.95, h * 0.6],
        ])
        
        # 3포인트 어파인 (양끝 + 중앙)
        src_3 = np.float32([src_pts[0], src_pts[2], src_pts[4]])
        dst_3 = np.float32([target_pts[0], target_pts[2], target_pts[4]])
        
        M = cv2.getAffineTransform(src_3, dst_3)
        
        canvas_h, canvas_w = canvas_shape[:2]
        result = cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )
        return result
    
    @staticmethod
    def align_eyelash(
        asset: np.ndarray,
        landmarks: np.ndarray,
        canvas_shape: tuple,
        side: str = "right",
    ) -> np.ndarray:
        """속눈썹 에셋 정렬"""
        if side == "left":
            asset = cv2.flip(asset, 1)
            target_pts = landmarks[LM.EYE_L]
        else:
            target_pts = landmarks[LM.EYE_R]
        
        h, w = asset.shape[:2]
        
        # 에셋 3포인트 → 눈 상단 3포인트
        src_3 = np.float32([
            [w * 0.05, h * 0.7],
            [w * 0.5, h * 0.3],
            [w * 0.95, h * 0.7],
        ])
        dst_3 = np.float32([target_pts[0], target_pts[2], target_pts[4]])
        
        M = cv2.getAffineTransform(src_3, dst_3)
        
        canvas_h, canvas_w = canvas_shape[:2]
        return cv2.warpAffine(
            asset, M, (canvas_w, canvas_h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_TRANSPARENT,
        )
    
    @staticmethod
    def align_blusher(
        mask: np.ndarray,
        landmarks: np.ndarray,
        canvas_shape: tuple,
        offset: dict,
        color_bgr: tuple,
        opacity: float = 0.4,
    ) -> np.ndarray:
        """블러셔 마스크를 코끝 기준으로 배치 (좌우 대칭)"""
        canvas_h, canvas_w = canvas_shape[:2]
        result = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        
        nose_tip = landmarks[52]  # 코끝
        face_w = AnchorAligner.get_temple_width(landmarks)
        
        dx = offset.get("dx", 0.18)
        dy = offset.get("dy", 0.02)
        
        for sign in [-1, +1]:  # 좌우 대칭
            cx = nose_tip[0] + sign * dx * face_w
            cy = nose_tip[1] + dy * face_w
            
            # 마스크 스케일
            target_size = int(face_w * 0.35)
            resized = cv2.resize(mask, (target_size, target_size))
            
            # grayscale mask → alpha
            if len(resized.shape) == 2:
                alpha = resized
            else:
                alpha = resized[:, :, 0]
            
            alpha = (alpha.astype(np.float32) * opacity).astype(np.uint8)
            
            # 배치
            x1 = int(cx - target_size // 2)
            y1 = int(cy - target_size // 2)
            x2 = x1 + target_size
            y2 = y1 + target_size
            
            # 경계 클리핑
            sx1 = max(0, -x1)
            sy1 = max(0, -y1)
            sx2 = target_size - max(0, x2 - canvas_w)
            sy2 = target_size - max(0, y2 - canvas_h)
            
            dx1 = max(0, x1)
            dy1 = max(0, y1)
            dx2 = min(canvas_w, x2)
            dy2 = min(canvas_h, y2)
            
            if dx2 > dx1 and dy2 > dy1:
                region = alpha[sy1:sy2, sx1:sx2]
                result[dy1:dy2, dx1:dx2, 0] = color_bgr[0]
                result[dy1:dy2, dx1:dx2, 1] = color_bgr[1]
                result[dy1:dy2, dx1:dx2, 2] = color_bgr[2]
                result[dy1:dy2, dx1:dx2, 3] = np.maximum(
                    result[dy1:dy2, dx1:dx2, 3], region
                )
        
        return result
    
    @staticmethod
    def align_lip(
        mask: np.ndarray,
        landmarks: np.ndarray,
        canvas_shape: tuple,
        color_bgr: tuple,
        opacity: float = 0.7,
    ) -> np.ndarray:
        """립 마스크를 입술 랜드마크에 TPS/어파인 정렬"""
        canvas_h, canvas_w = canvas_shape[:2]
        
        lip_pts = landmarks[LM.LIP_ALL]  # [55-70] 16포인트
        
        # 입술 바운딩 박스
        x_min, y_min = lip_pts.min(axis=0)
        x_max, y_max = lip_pts.max(axis=0)
        lip_w = x_max - x_min
        lip_h = y_max - y_min
        lip_cx = (x_min + x_max) / 2
        lip_cy = (y_min + y_max) / 2
        
        # 마스크 리사이즈
        mh, mw = mask.shape[:2]
        scale_x = lip_w * 1.1 / mw
        scale_y = lip_h * 1.2 / mh
        
        new_w = int(mw * scale_x)
        new_h = int(mh * scale_y)
        resized = cv2.resize(mask, (new_w, new_h))
        
        if len(resized.shape) == 2:
            alpha = resized
        else:
            alpha = resized[:, :, 0]
        
        alpha = (alpha.astype(np.float32) * opacity).astype(np.uint8)
        
        # 배치 (입술 중앙 정렬)
        result = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        
        x1 = int(lip_cx - new_w // 2)
        y1 = int(lip_cy - new_h // 2)
        x2 = x1 + new_w
        y2 = y1 + new_h
        
        sx1 = max(0, -x1)
        sy1 = max(0, -y1)
        sx2 = new_w - max(0, x2 - canvas_w)
        sy2 = new_h - max(0, y2 - canvas_h)
        
        dx1 = max(0, x1)
        dy1 = max(0, y1)
        dx2 = min(canvas_w, x2)
        dy2 = min(canvas_h, y2)
        
        if dx2 > dx1 and dy2 > dy1:
            region = alpha[sy1:sy2, sx1:sx2]
            result[dy1:dy2, dx1:dx2, 0] = color_bgr[0]
            result[dy1:dy2, dx1:dx2, 1] = color_bgr[1]
            result[dy1:dy2, dx1:dx2, 2] = color_bgr[2]
            result[dy1:dy2, dx1:dx2, 3] = region
        
        return result


# ─────────────────────────────────────────────
# 5. 레이어 합성
# ─────────────────────────────────────────────

class LayerCompositor:
"""z-order 기반 BGRA 레이어 합성"""

    @staticmethod
    def alpha_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """기본 alpha blend (normal mode)"""
        if overlay.shape[2] < 4:
            return base
        
        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        blended = base.copy().astype(np.float32)
        blended[:, :, :3] = (
            overlay[:, :, :3].astype(np.float32) * alpha
            + blended[:, :, :3] * (1 - alpha)
        )
        return np.clip(blended, 0, 255).astype(np.uint8)
    
    @staticmethod
    def multiply_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """multiply blend (블러셔용)"""
        if overlay.shape[2] < 4:
            return base
        
        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        base_f = base[:, :, :3].astype(np.float32)
        over_f = overlay[:, :, :3].astype(np.float32)
        
        multiplied = (base_f * over_f) / 255.0
        blended = base.copy().astype(np.float32)
        blended[:, :, :3] = multiplied * alpha + base_f * (1 - alpha)
        return np.clip(blended, 0, 255).astype(np.uint8)
    
    @staticmethod
    def soft_light_blend(base: np.ndarray, overlay: np.ndarray) -> np.ndarray:
        """soft light blend (립용)"""
        if overlay.shape[2] < 4:
            return base
        
        alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
        b = base[:, :, :3].astype(np.float32) / 255.0
        o = overlay[:, :, :3].astype(np.float32) / 255.0
        
        # Photoshop soft light 공식
        result = np.where(
            o <= 0.5,
            b - (1 - 2 * o) * b * (1 - b),
            b + (2 * o - 1) * (np.sqrt(b) - b),
        )
        
        blended = base.copy().astype(np.float32)
        blended[:, :, :3] = (result * alpha + b * (1 - alpha)) * 255
        return np.clip(blended, 0, 255).astype(np.uint8)


# ─────────────────────────────────────────────
# 6. 메인 컴포지터
# ─────────────────────────────────────────────

@dataclass
class CompositorConfig:
hair_bang: str = "bang_side_asym"
hair_back: str = "back_mid_layered"
eyebrow: str = "eb_semi_arch"
eyelash: str = "lash_natural"
blusher: str = "blush_center"
lip: str = "lip_gradient"

    hair_color: dict = field(default_factory=lambda: HAIR_COLORS["dark_brown"])
    blusher_color: dict = field(default_factory=lambda: BLUSHER_PRESETS["coral"])
    lip_color: dict = field(default_factory=lambda: LIP_PRESETS["mlbb"])
    
    blusher_opacity: float = 0.4
    lip_opacity: float = 0.7


# 블러셔 offset 테이블
BLUSHER_OFFSETS = {
"blush_center":         {"dx": 0.18, "dy": 0.02},
"blush_diagonal":       {"dx": 0.22, "dy": -0.03},
"blush_undereye":       {"dx": 0.12, "dy": -0.04},
"blush_noseside":       {"dx": 0.08, "dy": 0.00},
"blush_outer_vertical": {"dx": 0.28, "dy": -0.02},
}


class TemplateCompositor:
def __init__(self, assets_dir: str):
self.loader = AssetLoader(assets_dir)

    def compose(
        self,
        user_photo: np.ndarray,
        landmarks_106: np.ndarray,
        config: CompositorConfig = CompositorConfig(),
    ) -> np.ndarray:
        """
        전체 합성 파이프라인
        
        레이어 순서:
        1. back hair (behind user)
        2. user photo
        3. blusher (multiply)
        4. lip (soft light)
        5. eyebrow (normal)
        6. eyelash (normal)
        7. bang (normal, topmost)
        """
        h, w = user_photo.shape[:2]
        
        # 유저 사진을 BGRA로
        if user_photo.shape[2] == 3:
            canvas = cv2.cvtColor(user_photo, cv2.COLOR_BGR2BGRA)
        else:
            canvas = user_photo.copy()
        
        # ── Layer 1: 뒷머리 ──
        if config.hair_back != "none":
            back_asset = self.loader.get(config.hair_back)
            back_colored = shift_asset_color(back_asset, config.hair_color)
            back_aligned = AnchorAligner.align_back_hair(
                back_colored, landmarks_106, (h, w)
            )
            # 뒷머리는 유저 사진 뒤에 → 유저 사진의 alpha가 있는 곳은 유저가 우선
            # 여기서는 간단히: 뒷머리 먼저 깔고 유저를 위에
            temp = back_aligned.copy()
            canvas = LayerCompositor.alpha_blend(temp, canvas)
        
        # ── Layer 3: 블러셔 ──
        if config.blusher != "none":
            blush_mask = self.loader.get(config.blusher)
            blush_color = hsl_to_bgr(**config.blusher_color)
            offset = BLUSHER_OFFSETS.get(config.blusher, {"dx": 0.18, "dy": 0.02})
            blush_layer = AnchorAligner.align_blusher(
                blush_mask, landmarks_106, (h, w),
                offset=offset,
                color_bgr=blush_color,
                opacity=config.blusher_opacity,
            )
            canvas = LayerCompositor.multiply_blend(canvas, blush_layer)
        
        # ── Layer 4: 립 ──
        if config.lip != "none":
            lip_mask = self.loader.get(config.lip)
            lip_color = hsl_to_bgr(**config.lip_color)
            lip_layer = AnchorAligner.align_lip(
                lip_mask, landmarks_106, (h, w),
                color_bgr=lip_color,
                opacity=config.lip_opacity,
            )
            canvas = LayerCompositor.soft_light_blend(canvas, lip_layer)
        
        # ── Layer 5: 눈썹 (좌우) ──
        if config.eyebrow != "none":
            eb_asset = self.loader.get(config.eyebrow)
            eb_colored = shift_asset_color(
                eb_asset,
                {"h": config.hair_color["h"],
                 "s": config.hair_color["s"],
                 "l": config.hair_color["l"] * 0.8},
            )
            for side in ["right", "left"]:
                eb_aligned = AnchorAligner.align_eyebrow(
                    eb_colored, landmarks_106, (h, w), side=side
                )
                canvas = LayerCompositor.alpha_blend(canvas, eb_aligned)
        
        # ── Layer 6: 속눈썹 (좌우) ──
        if config.eyelash != "none":
            lash_asset = self.loader.get(config.eyelash)
            for side in ["right", "left"]:
                lash_aligned = AnchorAligner.align_eyelash(
                    lash_asset, landmarks_106, (h, w), side=side
                )
                canvas = LayerCompositor.alpha_blend(canvas, lash_aligned)
        
        # ── Layer 7: 앞머리 ──
        if config.hair_bang != "bang_none":
            bang_asset = self.loader.get(config.hair_bang)
            bang_colored = shift_asset_color(bang_asset, config.hair_color)
            bang_aligned = AnchorAligner.align_bang(
                bang_colored, landmarks_106, (h, w)
            )
            canvas = LayerCompositor.alpha_blend(canvas, bang_aligned)
        
        return canvas


# ─────────────────────────────────────────────
# 7. CLI / 테스트
# ─────────────────────────────────────────────

if __name__ == "__main__":
import sys

    if len(sys.argv) < 3:
        print("Usage: python template_compositor.py <photo> <assets_dir> [output]")
        print("Example: python template_compositor.py user.jpg assets/overlay result.png")
        sys.exit(1)
    
    photo_path = sys.argv[1]
    assets_dir = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "composed.png"
    
    # InsightFace 랜드마크 추출
    from insightface.app import FaceAnalysis
    
    app = FaceAnalysis(
        name="buffalo_l",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=(640, 640))
    
    photo = cv2.imread(photo_path)
    faces = app.get(photo)
    
    if not faces:
        print("No face detected")
        sys.exit(1)
    
    landmarks = faces[0].landmark_2d_106
    
    # 합성
    compositor = TemplateCompositor(assets_dir)
    config = CompositorConfig()  # 기본값 사용
    
    result = compositor.compose(photo, landmarks, config)
    cv2.imwrite(output_path, result)
    print(f"Saved: {output_path}")
'''