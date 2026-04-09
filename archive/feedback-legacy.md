# SIGAK 3축 좌표계 마이그레이션 — 완전 교체 지시서

> 생성일: 2026-04-09
> 목표: 4축(structure/impression/maturity/intensity) → 3축(shape/volume/age) 완전 전환
> 원칙: 레거시 코드 전량 삭제 후 새로 작성. 부분 수정 금지.
> 앵커: 16개 → 8개 (2³ 꼭짓점)

---

## 왜 전면 교체인가

현재 시스템은 수리 불가 수준으로 꼬여있다:

1. **극성 반전 버그**: similarity.py에서 structure 극성이 coordinate.py와 반대
2. **3축 잔해**: type_anchors.json에 죽은 axes_3d 데이터, similarity.py에 옛 "톤" 라벨
3. **라벨 소스 5곳**: coordinate.py, report_formatter.py, llm.py, similarity.py, 프론트 — 전부 다른 라벨
4. **피처 커플링**: eye_width_ratio, lip_fullness가 2축에 역방향 배치
5. **톤 축 소실**: 원본 8앵커의 핵심 구분축이 좌표계에서 사라짐

부분 수정으로는 해결 불가. 깨끗하게 들어내고 새로 만든다.

---

# 현재 시스템 전수 인벤토리 — 삭제 대상

> 이 섹션의 모든 항목은 마이그레이션 완료 시 삭제 또는 교체된다.

## 백엔드 파일별 삭제/교체 대상

### coordinate.py
```
삭제:
- AxisDefinition 클래스 (4축 정의)
- AXIS_DEFINITIONS dict (structure/impression/maturity/intensity)
- compute_coordinates() 내부 4축 가중합 로직
- compute_gap() 내부 4축 기반 gap 계산
- primary_shift_kr / secondary_shift_kr 생성 로직
- _normalize() — 로직은 재사용 가능하나 검증 후 판단
- _weighted_fallback() — 동일

교체:
- OBSERVED_RANGES — 새 3축 피처에 맞게 재정의
- 전체 export interface
```

### report_formatter.py
```
삭제:
- AXIS_LABELS dict (4축 라벨)
- get_position_label() — 새 축에 맞게 재작성
- _build_gap_analysis() 내부 4축 순회 로직
- direction_items 생성 (4축 기반)
- gap_summary 생성 (primary_shift_kr 기반)
- GAP_RECOMMENDATION_TEMPLATES (4축 기반 추천 템플릿)

교체:
- 전체 gap analysis 섹션 포맷팅
```

### similarity.py
```
삭제:
- axis_labels dict (극성 반전된 4축 라벨)
- 4축 기반 거리 계산 로직
- 앵커 매칭 시 4축 좌표 참조 로직

교체:
- 3축 기반 앵커 매칭
```

### llm.py
```
삭제:
- FACE_INTERPRET_SYSTEM 내 4축 설명
- 인터뷰 프롬프트 내 4축 라벨 참조

교체:
- 3축 기반 프롬프트
```

### action_spec.py
```
삭제:
- 4축 기반 delta_contribution 계산
- 4축 기반 zone 매핑

교체:
- 3축 기반 delta_contribution
```

### data/type_anchors.json
```
전면 교체:
- 16개 앵커 → 8개
- axes_3d (죽은 데이터) 삭제
- axes_3d_definition 삭제
- reference_coords: 4축 → 3축
- axis_roles: 4축 → 3축
- description_kr: 8개 재작성
- aliases: 8개 재정의
```

## 프론트 파일별 삭제/교체 대상

### gap-scatter-plot.tsx
```
삭제:
- pickTopTwoAxes() (동적 축 선택)
- AXIS_META (4축 메타데이터)
- CONNECTIVE_MAP (사분면 조합 로직)
- 4축 기반 사분면 라벨 생성

교체:
- 고정 2D 맵 (Shape × Age, Volume = 점 크기)
- aesthetic_map 기반 렌더링
```

### gap-analysis.tsx
```
삭제:
- AXIS_END_LABELS (4축 하드코딩)
- direction_items 4축 렌더링

교체:
- 3축 디테일 카드 렌더링
- 백엔드 label_low/label_high 직접 사용
```

---

# 새 3축 시스템 정의

## Single Source of Truth

> 이 정의가 모든 파일의 유일한 라벨 소스다.
> 다른 어떤 파일도 자체 라벨 dict를 갖지 않는다.

```python
# coordinate.py — 새 좌표계 정의
# ============================================================
# SIGAK 3-AXIS AESTHETIC COORDINATE SYSTEM v2
# 
# Shape:  골격+이목구비 형태 (Soft ↔ Sharp)
# Volume: 이목구비 크기·볼륨 (Subtle ↔ Bold)  
# Age:    비율이 주는 나이 인상 (Fresh ↔ Mature)
#
# 모든 축은 [-1, +1] 범위.
# -1 = low (Soft/Subtle/Fresh), +1 = high (Sharp/Bold/Mature)
# 피처 겹침: 없음. 12개 피처가 3축에 배타적 배치.
# ============================================================

AXIS_DEFINITIONS = {
    "shape": {
        "name_kr": "외형",
        "low": "Soft",
        "high": "Sharp",
        "low_kr": "소프트",
        "high_kr": "샤프",
        "description_kr": "골격과 이목구비가 만드는 전체적인 형태",
        "features": {
            "jaw_angle": {
                "weight": 0.25,
                "direction": "low_is_positive",   # 각도 낮을수록 sharp
                "description": "턱 각도 — 작을수록 각진 턱선",
            },
            "cheekbone_prominence": {
                "weight": 0.25,
                "direction": "high_is_positive",  # 돌출 높을수록 sharp
                "description": "광대 돌출도 — 높을수록 날카로운 윤곽",
            },
            "eye_tilt": {
                "weight": 0.20,
                "direction": "high_is_positive",  # 올라갈수록 sharp
                "description": "눈꼬리 기울기 — 올라갈수록 선명한 눈매",
            },
            "brow_arch": {
                "weight": 0.15,
                "direction": "high_is_positive",  # 아치 높을수록 sharp
                "description": "눈썹 아치 — 높을수록 날카로운 인상",
            },
            "eye_ratio": {
                "weight": 0.15,
                "direction": "high_is_positive",  # 가로 길수록 sharp
                "description": "눈 가로세로비 — 가로 길수록 선명",
            },
        },
    },
    "volume": {
        "name_kr": "존재감",
        "low": "Subtle",
        "high": "Bold",
        "low_kr": "서틀",
        "high_kr": "볼드",
        "description_kr": "이목구비의 크기와 볼륨이 만드는 존재감",
        "features": {
            "eye_width_ratio": {
                "weight": 0.30,
                "direction": "high_is_positive",  # 클수록 bold
                "description": "눈 크기 — 클수록 강한 존재감",
            },
            "lip_fullness": {
                "weight": 0.25,
                "direction": "high_is_positive",  # 도톰할수록 bold
                "description": "입술 풍성도 — 도톰할수록 화려",
            },
            "nose_bridge_height": {
                "weight": 0.25,
                "direction": "high_is_positive",  # 높을수록 bold
                "description": "코 높이 — 높을수록 입체적",
            },
            "brow_eye_distance": {
                "weight": 0.20,
                "direction": "low_is_positive",   # 가까울수록 bold
                "description": "눈썹-눈 거리 — 가까울수록 강렬",
                "fallback_handling": "missing이면 나머지 3피처로 재가중",
            },
        },
    },
    "age": {
        "name_kr": "무드",
        "low": "Fresh",
        "high": "Mature",
        "low_kr": "프레시",
        "high_kr": "매추어",
        "description_kr": "얼굴 비율이 주는 나이 인상과 분위기",
        "features": {
            "forehead_ratio": {
                "weight": 0.35,
                "direction": "high_is_positive",  # 클수록 mature
                "description": "이마 비율 — 클수록 성숙한 인상",
            },
            "philtrum_ratio": {
                "weight": 0.35,
                "direction": "high_is_positive",  # 길수록 mature
                "description": "인중 비율 — 길수록 성숙한 인상",
            },
            "face_length_ratio": {
                "weight": 0.30,
                "direction": "high_is_positive",  # 길수록 mature
                "description": "얼굴 종횡비 — 길수록 성숙한 인상",
            },
        },
    },
}
```

### 피처 배치 검증 — 겹침 제로 확인

```
shape:  jaw_angle, cheekbone_prominence, eye_tilt, brow_arch, eye_ratio  (5개)
volume: eye_width_ratio, lip_fullness, nose_bridge_height, brow_eye_distance  (4개)
age:    forehead_ratio, philtrum_ratio, face_length_ratio  (3개)
                                                                         합계: 12개

겹치는 피처: 없음 ✓
기존 커플링 해소:
  - eye_width_ratio: volume에만 → maturity 커플링 소멸 ✓
  - lip_fullness: volume에만 → impression 커플링 소멸 ✓
```

---

## 8 앵커 유형 정의

```python
# data/type_anchors.json 교체용

ANCHOR_TYPES = {
    "type_1": {
        "name_kr": "따뜻한 첫사랑",
        "coords": {"shape": -1.0, "volume": -1.0, "age": -1.0},
        "quadrant": "Soft Fresh",
        "one_liner": "둥글고 작고 어린 — 순수하고 따뜻한 강아지상",
        "description_kr": "둥근 얼굴형, 부드러운 턱선, 큰 둥근 눈, 도톰한 입술. 작은 이목구비에 어린 비율. 따뜻하고 부드러운 인상.",
        "features_bullet": [
            "둥근 얼굴형과 부드러운 턱선",
            "작고 온화한 이목구비",
            "어리고 생기 있는 비율",
        ],
        "aliases": ["첫사랑", "강아지상", "소프트프레시"],
    },
    "type_2": {
        "name_kr": "사랑스러운 인형",
        "coords": {"shape": -1.0, "volume": +1.0, "age": -1.0},
        "quadrant": "Soft Fresh",
        "one_liner": "둥글고 크고 어린 — 크고 또렷한 이목구비의 동안",
        "description_kr": "둥근 얼굴형, 부드러운 턱선, 매우 큰 눈, 도톰한 입술, 높은 코. 큰 이목구비에 어린 비율. 화려하지만 사랑스러운 인상.",
        "features_bullet": [
            "둥근 윤곽에 크고 또렷한 이목구비",
            "화려하지만 부드러운 인상",
            "어리고 사랑스러운 비율",
        ],
        "aliases": ["인형상", "큰눈동안", "소프트볼드프레시"],
    },
    "type_3": {
        "name_kr": "차갑지만 동안",
        "coords": {"shape": +1.0, "volume": -1.0, "age": -1.0},
        "quadrant": "Sharp Fresh",
        "one_liner": "날카롭고 작고 어린 — 차갑고 어린 고양이상",
        "description_kr": "역삼각형 얼굴, 뾰족한 턱, 날카로운 눈매. 작은 이목구비에 어린 비율. 차갑지만 동안인 시크한 인상.",
        "features_bullet": [
            "날카로운 윤곽과 뾰족한 턱선",
            "작고 절제된 이목구비",
            "어린 비율에 서늘한 눈매",
        ],
        "aliases": ["고양이상", "쿨동안", "샤프프레시"],
    },
    "type_4": {
        "name_kr": "또렷한 에너지",
        "coords": {"shape": +1.0, "volume": +1.0, "age": -1.0},
        "quadrant": "Sharp Fresh",
        "one_liner": "날카롭고 크고 어린 — 선명하고 화려한 동안",
        "description_kr": "각진 얼굴, 날카로운 눈매에 크고 뚜렷한 이목구비. 어린 비율이지만 강렬한 존재감. 에너지 넘치는 인상.",
        "features_bullet": [
            "날카로운 윤곽에 크고 강렬한 이목구비",
            "또렷하고 에너지 넘치는 인상",
            "어린 비율에 화려한 존재감",
        ],
        "aliases": ["또렷동안", "에너지", "샤프볼드프레시"],
    },
    "type_5": {
        "name_kr": "편안한 우아함",
        "coords": {"shape": -1.0, "volume": -1.0, "age": +1.0},
        "quadrant": "Soft Mature",
        "one_liner": "둥글고 작고 성숙한 — 절제되고 편안한 성숙미",
        "description_kr": "타원형 얼굴, 부드러운 턱선에 길이감. 작은 이목구비에 성숙한 비율. 편안하고 우아한 인상.",
        "features_bullet": [
            "부드러운 윤곽에 길이감 있는 얼굴",
            "작고 절제된 이목구비",
            "성숙하고 편안한 비율",
        ],
        "aliases": ["우아함", "편안한성숙", "소프트매추어"],
    },
    "type_6": {
        "name_kr": "부드러운 카리스마",
        "coords": {"shape": -1.0, "volume": +1.0, "age": +1.0},
        "quadrant": "Soft Mature",
        "one_liner": "둥글고 크고 성숙한 — 온화하면서 압도적인 존재감",
        "description_kr": "둥근~타원형 얼굴, 부드러운 턱선. 크고 깊은 눈, 도톰한 입술, 높은 코. 성숙한 비율에 온화하지만 강한 존재감.",
        "features_bullet": [
            "부드러운 윤곽에 크고 깊은 이목구비",
            "온화하면서 존재감 있는 인상",
            "성숙하고 카리스마 있는 비율",
        ],
        "aliases": ["카리스마", "부드러운존재감", "소프트볼드매추어"],
    },
    "type_7": {
        "name_kr": "절제된 시크",
        "coords": {"shape": +1.0, "volume": -1.0, "age": +1.0},
        "quadrant": "Sharp Mature",
        "one_liner": "날카롭고 작고 성숙한 — 차갑고 절제된 시크함",
        "description_kr": "긴 얼굴, 각진 턱선, 높은 광대. 날카로운 눈매에 작은 이목구비. 성숙한 비율에 차갑고 절제된 시크 인상.",
        "features_bullet": [
            "날카로운 윤곽과 높은 광대",
            "작고 절제된 이목구비",
            "성숙하고 시크한 비율",
        ],
        "aliases": ["시크", "절제된차가움", "샤프매추어"],
    },
    "type_8": {
        "name_kr": "날카로운 카리스마",
        "coords": {"shape": +1.0, "volume": +1.0, "age": +1.0},
        "quadrant": "Sharp Mature",
        "one_liner": "날카롭고 크고 성숙한 — 강렬하고 압도적인 시크",
        "description_kr": "긴 각진 얼굴, 강한 턱선. 크고 날카로운 눈, 두꺼운 입술, 높은 코. 성숙한 비율에 압도적인 존재감. 강렬한 카리스마.",
        "features_bullet": [
            "날카로운 윤곽에 크고 강렬한 이목구비",
            "압도적인 존재감과 카리스마",
            "성숙하고 강한 비율",
        ],
        "aliases": ["카리스마시크", "강렬함", "샤프볼드매추어"],
    },
}
```

---

## 2D 미적 좌표계

```
메인 뷰: Shape(X축) × Age(Y축) — 고정. 동적 축 선택 없음.
3번째 축 Volume은 점 크기로 표현.

         Fresh
           │
  Soft ────┼──── Sharp
           │
        Mature

사분면 라벨 (고정):
  좌하: Soft Fresh
  우하: Sharp Fresh
  좌상: Soft Mature
  우상: Sharp Mature
```

### 2D 맵 JSON 구조

```python
aesthetic_map = {
    "current": {
        "x": current_coords["shape"],          # Shape
        "y": current_coords["age"],             # Age (반전: Fresh가 아래)
        "size": current_coords["volume"],       # Volume → 점 크기
    },
    "aspiration": {
        "x": aspiration_coords["shape"],
        "y": aspiration_coords["age"],
        "size": aspiration_coords["volume"],
    },
    "x_axis": {"label": "외형", "low": "Soft", "high": "Sharp"},
    "y_axis": {"label": "무드", "low": "Fresh", "high": "Mature"},
    "size_axis": {"label": "존재감", "low": "Subtle", "high": "Bold"},
    "quadrants": {
        "top_left": "Soft Mature",
        "top_right": "Sharp Mature",
        "bottom_left": "Soft Fresh",
        "bottom_right": "Sharp Fresh",
    },
    "description": "가로축은 골격과 이목구비의 형태, 세로축은 비율이 주는 무드예요. 점이 클수록 이목구비 존재감이 강해요.",
}
```

---

## 3축 디테일 카드

기존 4축 디테일 → 3축으로 교체:

```python
direction_items = [
    {
        "axis": "shape",
        "name_kr": "외형",
        "description_kr": "골격과 이목구비가 만드는 전체적인 형태",
        "label_low": "Soft",
        "label_high": "Sharp",
        "current_value": -0.45,
        "current_label": "약간 소프트",        # get_position_label()
        "aspiration_value": 0.60,
        "aspiration_label": "샤프",
        "difficulty": "중간 변화",
        "recommendation": "...",
    },
    {
        "axis": "volume",
        "name_kr": "존재감",
        # ... 동일 구조
    },
    {
        "axis": "age",
        "name_kr": "무드",
        # ... 동일 구조
    },
]
```

---

# 마이그레이션 Phase 계획

---

## Phase 0: 즉시 핫픽스 (4/10 전)

> 현행 4축 유지한 상태에서 치명적 버그만 수정.
> 3축 전환과 무관한 독립 수정.

```
0-1. similarity.py 극성 반전 수정
     "structure": {-1: "날카로운", 1: "부드러운"} 
     → {-1: "부드러운", 1: "날카로운"}  (coordinate.py 기준)
     
     "impression": {-1: "따뜻한", 1: "쿨한"} 
     → {-1: "부드러운", 1: "선명한"}  (coordinate.py 기준)

0-2. gap_summary의 primary_shift_kr이 coordinate.py 라벨 대신 
     report_formatter AXIS_LABELS 라벨을 사용하도록 수정

0-3. 기존 v4.1 스펙의 나머지 UI 수정 (수치 숨기기, zone 한글화 등) 마무리

검증: 리포트 1건 생성 → 유형 매칭 방향 정상 확인
```

---

## Phase 1: 백엔드 좌표계 교체

> coordinate.py 전면 교체. 이 Phase 완료 시 백엔드는 3축으로 동작.
> 프론트는 아직 4축 → 프론트에서 깨지는 것은 Phase 2에서 처리.

### 1-1. coordinate.py 전면 재작성

```
삭제:
- AxisDefinition 클래스
- 기존 AXIS_DEFINITIONS (4축)
- compute_coordinates() 내부 4축 로직

생성:
- 위 "새 3축 시스템 정의"의 AXIS_DEFINITIONS 그대로 사용
- compute_coordinates() 재작성:

def compute_coordinates(features: dict) -> dict:
    """
    12개 피처 → 3축 좌표 계산.
    각 피처는 OBSERVED_RANGES로 [-1, +1] 정규화 후 가중합.
    """
    coords = {}
    for axis_name, axis_def in AXIS_DEFINITIONS.items():
        values = []
        weights = []
        for feat_name, feat_def in axis_def["features"].items():
            raw = features.get(feat_name)
            if raw is None:
                continue
            normalized = _normalize(feat_name, raw)
            if feat_def["direction"] == "low_is_positive":
                normalized = -normalized
            values.append(normalized)
            weights.append(feat_def["weight"])
        
        if not values:
            coords[axis_name] = 0.0
        else:
            # 가중합 후 재정규화
            total_weight = sum(weights)
            coords[axis_name] = sum(v * w for v, w in zip(values, weights)) / total_weight
            coords[axis_name] = max(-1.0, min(1.0, coords[axis_name]))
    
    return coords
```

### 1-2. OBSERVED_RANGES 업데이트

```
기존 피처 범위는 유지 (동일 피처 사용).
다만 3축에서 사용하지 않는 피처가 있으면 정리:

사용 피처 (12개):
  jaw_angle, cheekbone_prominence, eye_tilt, brow_arch, eye_ratio,
  eye_width_ratio, lip_fullness, nose_bridge_height, brow_eye_distance,
  forehead_ratio, philtrum_ratio, face_length_ratio

사용하지 않는 피처:
  face.py에서 추출하지만 좌표 계산에 미사용인 피처가 있으면 확인 후 정리.
```

### 1-3. compute_gap() 3축 기반 재작성

```python
def compute_gap(current: dict, aspiration: dict) -> dict:
    """
    current/aspiration: {"shape": float, "volume": float, "age": float}
    """
    vector = {}
    for axis in AXIS_DEFINITIONS:
        vector[axis] = aspiration[axis] - current[axis]
    
    magnitude = math.sqrt(sum(v**2 for v in vector.values()))
    
    # primary/secondary 축 결정
    sorted_axes = sorted(vector.items(), key=lambda x: abs(x[1]), reverse=True)
    primary_axis = sorted_axes[0][0]
    primary_delta = sorted_axes[0][1]
    secondary_axis = sorted_axes[1][0] if len(sorted_axes) > 1 else None
    
    # shift 라벨 — AXIS_DEFINITIONS에서만 가져옴
    ax_def = AXIS_DEFINITIONS[primary_axis]
    primary_shift_kr = ax_def["high_kr"] if primary_delta > 0 else ax_def["low_kr"]
    
    return {
        "vector": vector,
        "magnitude": round(magnitude, 2),
        "primary_axis": primary_axis,
        "primary_shift_kr": primary_shift_kr,
        "secondary_axis": secondary_axis,
    }
```

### 1-4. get_axis_labels() 함수 — 라벨 조회 유일 경로

```python
def get_axis_labels(axis_name: str) -> dict:
    """다른 모든 파일은 이 함수로만 라벨을 조회한다."""
    ax = AXIS_DEFINITIONS[axis_name]
    return {
        "name_kr": ax["name_kr"],
        "low": ax["low"],
        "high": ax["high"],
        "low_kr": ax["low_kr"],
        "high_kr": ax["high_kr"],
        "description_kr": ax["description_kr"],
    }

def get_all_axis_labels() -> dict:
    """프론트에 내려줄 전체 축 라벨."""
    return {name: get_axis_labels(name) for name in AXIS_DEFINITIONS}
```

### 1-5. 검증 체크포인트

```
[ ] compute_coordinates()에 기존 테스트 피처 넣어서 3축 좌표 출력 확인
[ ] 3축 좌표가 모두 [-1, +1] 범위 내
[ ] 피처 누락 시 (brow_eye_distance=None) 정상 fallback
[ ] compute_gap()에 현재/추구 넣어서 gap 벡터 정상 확인
[ ] primary_shift_kr이 AXIS_DEFINITIONS 라벨과 일치
```

---

## Phase 2: 앵커 데이터 교체

> type_anchors.json 전면 교체.
> 8개 앵커, 3축 좌표, 죽은 데이터 전부 삭제.

### 2-1. type_anchors.json 교체

위 ANCHOR_TYPES를 JSON 형식으로 변환하여 교체.

```json
{
  "version": "3axis_v1",
  "axes": ["shape", "volume", "age"],
  "anchors": {
    "type_1": {
      "type_id": 1,
      "name_kr": "따뜻한 첫사랑",
      "coords": {"shape": -0.8, "volume": -0.7, "age": -0.8},
      "quadrant": "Soft Fresh",
      "one_liner": "둥글고 작고 어린 — 순수하고 따뜻한 강아지상",
      "description_kr": "둥근 얼굴형, 부드러운 턱선, 큰 둥근 눈, 도톰한 입술. 작은 이목구비에 어린 비율.",
      "features_bullet": ["둥근 얼굴형과 부드러운 턱선", "작고 온화한 이목구비", "어리고 생기 있는 비율"],
      "aliases": ["첫사랑", "강아지상", "소프트프레시"]
    }
  }
}
```

> coords는 정확히 ±1.0이 아니라 ±0.7~0.8 정도로 설정.
> 이유: 실제 사람 얼굴은 극점에 정확히 위치하지 않음.
> 정확한 값은 AI 이미지 생성 후 InsightFace로 측정하여 캘리브레이션.

### 2-2. 기존 16개 앵커에서 8개로 정리

```
기존 → 신규 매핑:
type_1 (따뜻한 첫사랑) → type_1 유지
type_2 (차갑지만 동안) → type_3 (Sharp+Subtle+Fresh)
type_3 (또렷한데 발랄한) → type_4 (Sharp+Bold+Fresh)
type_4 (날카롭고 시크한) → type_8 (Sharp+Bold+Mature)
type_5 (부드러우면서 성숙한) → type_5 (Soft+Subtle+Mature)
type_6 (강인하면서 따뜻한) → type_6과 type_8 사이 → 가장 가까운 것으로
type_7 (차가운 우아함) → type_7 (Sharp+Subtle+Mature)
type_8 (날카롭고 어린) → type_3과 유사 → 통합

나머지(type_9~16)는 삭제. 사용하지 않음.
```

### 2-3. similarity.py 3축 기반 재작성

```
삭제:
- axis_labels dict 전체
- 4축 기반 거리 계산

생성:
- coordinate.py의 get_axis_labels() import
- 3축 유클리드 거리 기반 앵커 매칭
- 매칭 시 type_anchors.json의 coords 사용
```

### 2-4. 검증 체크포인트

```
[ ] 8개 앵커가 3D 공간 꼭짓점 근처에 고르게 분포
[ ] 테스트 피처 → 가장 가까운 앵커 매칭 결과가 직관적으로 맞는지
[ ] 기존 리포트 재생성 → 유형 매칭 결과 비교 (급격한 변화 없는지)
```

---

## Phase 3: report_formatter + llm.py + action_spec.py 교체

### 3-1. report_formatter.py

```
삭제:
- AXIS_LABELS → coordinate.py에서 import
- 4축 순회 로직 → 3축 순회로 교체
- GAP_RECOMMENDATION_TEMPLATES → 3축 기반으로 재작성

수정:
- get_position_label() → AXIS_DEFINITIONS의 low_kr/high_kr 사용
- _build_gap_analysis() → 3축 direction_items 생성
- gap_summary → 3축 기반

def get_position_label(axis: str, value: float) -> str:
    value = max(-1.0, min(1.0, value if value is not None else 0.0))
    labels = get_axis_labels(axis)
    
    abs_val = abs(value)
    if abs_val < 0.15:
        return "중간"
    
    direction = labels["high_kr"] if value > 0 else labels["low_kr"]
    
    if abs_val < 0.35:
        return f"약간 {direction}"
    elif abs_val < 0.65:
        return direction
    else:
        return f"매우 {direction}"
```

### 3-2. llm.py

```
삭제:
- 4축 설명 프롬프트

수정:
- FACE_INTERPRET_SYSTEM에 3축 설명 반영:
  "외형(Shape): 골격과 이목구비의 형태 — Soft에서 Sharp"
  "존재감(Volume): 이목구비의 크기와 볼륨 — Subtle에서 Bold"  
  "무드(Age): 비율이 주는 나이 인상 — Fresh에서 Mature"
```

### 3-3. action_spec.py

```
삭제:
- 4축 기반 delta_contribution

수정:
- 3축 기반 delta_contribution 재계산
- zone별 기여 축 매핑 (3축 기준)
```

### 3-4. 검증 체크포인트

```
[ ] 리포트 전체 생성 → 3축 디테일 카드 정상 출력
[ ] gap_summary 텍스트에 올바른 라벨 사용
[ ] LLM 해설에 4축 잔재 없음
[ ] action_plan zone별 방향 태그가 3축 기반으로 정상 출력
```

---

## Phase 4: 프론트엔드 교체

### 4-1. gap-scatter-plot.tsx 전면 재작성

```
삭제:
- pickTopTwoAxes()
- AXIS_META
- CONNECTIVE_MAP
- 4축 기반 모든 로직

생성:
- aesthetic_map 기반 고정 2D 렌더링
- X축: Shape (Soft ↔ Sharp)
- Y축: Age (Fresh ↔ Mature)
- 점 크기: Volume (Subtle = 작은 점, Bold = 큰 점)
- 사분면 라벨: Soft Fresh / Sharp Fresh / Soft Mature / Sharp Mature
- 좌표 수치 없음, 거리값 없음
```

### 4-2. gap-analysis.tsx 교체

```
삭제:
- AXIS_END_LABELS
- 4축 direction_items 렌더링

생성:
- 3축 디테일 카드 (백엔드 direction_items 그대로 렌더링)
- 각 카드: 축 이름 + 설명 + 양 끝 라벨 + 슬라이더 + 추천
```

### 4-3. 프론트 하드코딩 전량 삭제

```
삭제 대상:
- AXIS_META (4축 메타)
- AXIS_END_LABELS (4축 양 끝)
- 사분면 라벨 조합 로직

원칙: 프론트는 자체 축 라벨을 갖지 않는다.
모든 라벨은 백엔드 JSON에서 내려온다.
```

### 4-4. 검증 체크포인트

```
[ ] 2D 맵에 현재/추구 점이 정상 표시
[ ] 사분면 라벨 4개 정상 표시
[ ] Volume 점 크기 차이가 시각적으로 구분 가능
[ ] 3축 디테일 카드 정상 렌더링
[ ] 4축 잔재 없음 (검색으로 확인: "structure", "impression", "maturity", "intensity")
```

---

## Phase 5: 앵커 이미지 생성 + 캘리브레이션

### 5-1. AI 이미지 8장 생성

16앵커 가이드의 프롬프트를 8앵커 기준으로 재작성 (별도 문서).
DeeVid AI / Midjourney로 생성.

### 5-2. InsightFace 역검증

생성된 8장 이미지를 파이프라인에 넣어서:
- 12개 피처 추출
- 3축 좌표 계산
- 의도한 극점 근처에 위치하는지 확인

### 5-3. 앵커 좌표 캘리브레이션

역검증 결과에 따라 type_anchors.json의 coords를 실측값으로 교체.

---

## Phase 6: 레거시 완전 삭제 + 최종 검증

### 6-1. 코드베이스 전체 검색

```bash
# 4축 잔재 검색 — 결과 0건이어야 함
grep -r "structure" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "impression" --include="*.py" --include="*.tsx" --include="*.json"  
grep -r "maturity" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "intensity" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "axes_3d" --include="*.json"
grep -r "axis_roles" --include="*.json"

# 허용되는 예외:
# - 이 마이그레이션 문서 자체
# - git history
# - 주석에 "legacy" 표시된 것 (없어야 하지만)
```

### 6-2. 통합 테스트

```
[ ] 신규 사진 업로드 → 전체 파이프라인 정상 작동
[ ] 리포트 전체 렌더링 (8 섹션 + 3축 디테일)
[ ] 유형 매칭 → 8개 중 하나로 정상 매칭
[ ] gap 계산 → 3축 벡터 정상
[ ] 2D 맵 → 점 위치 + 크기 정상
[ ] 액션 플랜 → zone별 방향 태그 3축 기반
[ ] 결제 플로우 → paywall 정상 작동
```

---

# 타임라인 요약

| Phase | 작업 | 의존성 | 예상 |
|-------|------|--------|------|
| 0 | 즉시 핫픽스 (극성 반전, 라벨 불일치) | 없음 | 4/10 전 |
| 1 | coordinate.py 전면 교체 | Phase 0 | 1일 |
| 2 | 앵커 데이터 + similarity.py 교체 | Phase 1 | 1일 |
| 3 | formatter + llm + action_spec 교체 | Phase 1 | 1일 |
| 4 | 프론트엔드 교체 | Phase 2, 3 | 1일 |
| 5 | 앵커 이미지 + 캘리브레이션 | Phase 2 | 2-3일 |
| 6 | 레거시 삭제 + 최종 검증 | 전체 | 0.5일 |

**Phase 1~4는 병렬 불가 — 순차 진행.**
**Phase 5는 Phase 2 이후 병렬 가능.**
**총 예상: 5~7일.**

---

*Generated: 2026-04-09*
*이 문서가 완전히 실행되면:*
*- 4축 코드 잔재 제로*
*- 라벨 소스 1곳 (coordinate.py)*
*- 피처 겹침 제로*
*- 앵커 8개, 3D 공간 꼭짓점*
*- 2D 맵 고정축, 사분면 충돌 없음*