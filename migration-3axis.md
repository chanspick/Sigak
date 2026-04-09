# SIGAK 3축 마이그레이션 — 실행 스펙

> 생성일: 2026-04-09
> 기반: feedback.md + roadmap.md + 코드베이스 전수 조사
> 원칙: 4축 핫픽스 스킵, 3축 직행. 레거시 전량 삭제.

---

## 현재 코드베이스 실상 (감사 결과)

### 파이프라인 데이터 흐름

```
사진(bytes) → face.py → FaceFeatures(24필드)
  → coordinate.py → 4축 좌표 {structure, impression, maturity, intensity}
  → similarity.py → similar_types [{key, similarity_pct, axis_delta}]
  → cluster.py → {cluster_id, label_kr, confidence}
인터뷰(text) → llm.py → aspiration_coords {4축}
  → coordinate.py compute_gap() → {vector, magnitude, primary_direction}
  → action_spec.py → ActionSpec {visual_priorities, actions}
  → report_formatter.py → ReportData (프론트 JSON)
  → 프론트 렌더링
```

### 피처 → 축 매핑 (4축, 현재)

| 축 | 피처 (가중치) | 문제 |
|---|---|---|
| structure | jaw_angle(0.40), cheekbone(0.30), face_length_ratio(0.30) | 없음 |
| impression | eye_tilt(0.35), brow_arch(0.25), eye_ratio(0.25), lip_fullness(0.15) | lip_fullness 커플링 |
| maturity | forehead(0.35), philtrum(0.35), eye_width_ratio(0.30) | eye_width_ratio 커플링 |
| intensity | eye_width_ratio(0.30), lip_fullness(0.25), nose_bridge(0.25), brow_eye_distance(0.20) | 2개 커플링 + 유령 피처 |

### 검증된 이슈 목록

| ID | 이슈 | 위치 | 심각도 |
|---|---|---|---|
| I-1 | eye_width_ratio가 maturity(-0.30)와 intensity(+0.30)에 동시 배치 → 축 독립성 위반 | coordinate.py:213,229 | 🔴 |
| I-2 | lip_fullness가 impression(-0.15)과 intensity(+0.25)에 동시 배치 | coordinate.py:189,234 | 🔴 |
| I-3 | brow_eye_distance: face.py FaceFeatures에 필드 없음 → intensity 항상 3/4피처로 동작 | face.py:26-53, coordinate.py:243 | 🟠 |
| I-4 | cluster.py _SIGN_TO_LABEL 극성 반전 (negative="sharp", positive="soft") | cluster.py:524-529 | 🟡 내부용 |
| I-5 | 라벨 소스 5곳 분산 (coordinate/similarity/formatter/llm/프론트) | 전체 | 🔴 |
| I-6 | config.py coordinate_axes=3 (실제 4) | config.py:33 | 🟢 |
| I-7 | type_anchors.json 죽은 필드 (axes_3d, axes_3d_definition, community_score) | type_anchors.json | 🟡 |
| I-8 | 프론트 AXIS_META/AXIS_LABELS/AXIS_END_LABELS 하드코딩 | gap-scatter-plot.tsx, gap-analysis.tsx | 🔴 |
| I-9 | pickTopTwoAxes() 동적 축 선택 → 재진단 시 차트 변경 | gap-scatter-plot.tsx:59-71 | 🟠 |
| I-10 | app/page.tsx AXES가 3축만 표시 (4축과 불일치) | app/page.tsx:30-34 | 🟡 |

---

## 새 3축 시스템

### 축 정의 (SSOT — axis_config.yaml)

| 축 | name_kr | -1 (low) | +1 (high) | 피처 | 해소하는 이슈 |
|---|---|---|---|---|---|
| shape | 외형 | Soft (소프트) | Sharp (샤프) | jaw_angle(0.25), cheekbone(0.25), eye_tilt(0.20), brow_arch(0.15), eye_ratio(0.15, 반전) | — |
| volume | 존재감 | Subtle (서틀) | Bold (볼드) | eye_width_ratio(0.30), lip_fullness(0.25), nose_bridge_height(0.25), brow_eye_distance(0.20) | I-1, I-2 해소 |
| age | 무드 | Fresh (프레시) | Mature (매추어) | forehead_ratio(0.35), philtrum_ratio(0.35), face_length_ratio(0.30) | — |

피처 겹침: **0건** (12피처가 3축에 배타적 배치)

### 용어 주의: "따뜻한" = 온화한 인상

> 앵커 이름의 "따뜻한"은 **색채 warm tone이 아니라 온화한/편안한 인상**을 의미한다.
> 프론트 카피, LLM 설명, skin tone 추천, type description 등에서
> "따뜻한"을 색채 warm으로 잘못 해석하지 않도록 주의.
> 색채 warm/cool은 스킨톤 모듈(skin_analysis)에서만 사용한다.

### 8 앵커 유형

| type | name_kr | coords | one_liner |
|---|---|---|---|
| 1 | 따뜻한 첫사랑 | shape:-0.8, volume:-0.7, age:-0.8 | 둥글고 작고 어린 |
| 2 | 사랑스러운 인형 | shape:-0.8, volume:+0.7, age:-0.8 | 둥글고 크고 어린 |
| 3 | 차갑지만 동안 | shape:+0.8, volume:-0.7, age:-0.8 | 날카롭고 작고 어린 |
| 4 | 또렷한 에너지 | shape:+0.8, volume:+0.7, age:-0.8 | 날카롭고 크고 어린 |
| 5 | 편안한 우아함 | shape:-0.8, volume:-0.7, age:+0.8 | 둥글고 작고 성숙한 |
| 6 | 부드러운 카리스마 | shape:-0.8, volume:+0.7, age:+0.8 | 둥글고 크고 성숙한 |
| 7 | 절제된 시크 | shape:+0.8, volume:-0.7, age:+0.8 | 날카롭고 작고 성숙한 |
| 8 | 날카로운 카리스마 | shape:+0.8, volume:+0.7, age:+0.8 | 날카롭고 크고 성숙한 |

### 2D 미적 맵 (고정)

```
X축: Shape (Soft ↔ Sharp) — 고정
Y축: Age (Fresh 아래 ↔ Mature 위) — 고정
점 크기: Volume (Subtle 작 ↔ Bold 큼)

사분면: Soft Fresh / Sharp Fresh / Soft Mature / Sharp Mature
```

---

## 삭제 대상 전수 인벤토리

### 백엔드

| 파일 | 삭제 대상 | 라인 |
|---|---|---|
| coordinate.py | AxisDefinition 클래스 | 22-29 |
| coordinate.py | AXES 리스트 (4축) | 31-52 |
| coordinate.py | _AXES_BY_NAME | 59 |
| coordinate.py | compute_structure() | 139-161 |
| coordinate.py | compute_impression() | 164-192 |
| coordinate.py | compute_maturity() | 195-217 |
| coordinate.py | compute_intensity() | 220-247 |
| coordinate.py | compute_coordinates() 내부 4축 호출 | 254-270 |
| coordinate.py | compute_gap() 내부 4축 로직 | 277-325 |
| similarity.py | axis_labels dict | 411-416 |
| similarity.py | 4축 axes 리스트 참조 | 186, 263 |
| cluster.py | _SIGN_TO_LABEL (4축, 극성 반전) | 524-529 |
| cluster.py | 4축 순회 루프 | 535, 745 |
| report_formatter.py | _AXIS_DISPLAY_OVERRIDES | 330-347 |
| report_formatter.py | GAP_RECOMMENDATION_TEMPLATES (4축) | 259-276 |
| report_formatter.py | DIRECTION_STYLING_TIPS (4축) | 280-289 |
| llm.py | _build_interview_system 내 4축 프롬프트 | 44-72 |
| action_spec.py | AXIS_ACTION_RULES (4축 24규칙) | 71-120 |
| action_spec.py | TYPE_MODIFIERS (4축 5타입) | 전체 |
| config.py | coordinate_axes: 3 | 33 |

### 데이터

| 파일 | 삭제 대상 |
|---|---|
| type_anchors.json | 전면 교체 (16→8앵커, 4→3축, 죽은 필드 제거) |
| cluster_labels.json | 재생성 (3축 centroid_coords, 시그니처) |
| celeb_anchors.json | 3축 reference_coords 교체 또는 미사용 시 제거 |

### 프론트엔드

| 파일 | 삭제 대상 | 라인 |
|---|---|---|
| gap-scatter-plot.tsx | Coordinates 인터페이스 (4축) | 5-10 |
| gap-scatter-plot.tsx | AXIS_META (4축 라벨) | 14-22 |
| gap-scatter-plot.tsx | CONNECTIVE_MAP | 25-33 |
| gap-scatter-plot.tsx | pickTopTwoAxes() | 59-71 |
| gap-analysis.tsx | Coordinates 인터페이스 (중복) | 8-14 |
| gap-analysis.tsx | AXIS_LABELS | 52-57 |
| gap-analysis.tsx | AXIS_END_LABELS | 74-79 |
| mock-report.ts | 4축 좌표 데이터 전부 | 169-305 |
| app/page.tsx | AXES 상수 (3축 불완전) | 30-34 |

---

## Phase 계획

### Phase 0: 선행 준비 (0.5일)

#### 0-1. face.py에 brow_eye_distance 추가

```python
# FaceFeatures에 이미 없는 필드 → 계산 로직 추가
# InsightFace 106 landmarks 기반:
#   눈썹 중심: landmarks[38:43] 중앙
#   눈 중심: landmarks[33:38] 중앙
#   거리 = dist(brow_center, eye_center) / face_height
```

face.py의 _build_features_insightface()에 brow_eye_distance 계산 추가.
FaceFeatures dataclass에 필드 추가 (Optional[float], 기본값 None).

#### 0-2. 설정 파일 생성 (2파일 분리)

> **원칙**: 축 정의(axis_config.yaml)와 통계값(calibration_3axis.yaml)을 분리한다.
> axis_config.yaml은 축/피처/가중치/방향만 담고, observed_ranges는 캘리브레이션 산출물에서만 로드.
> 이렇게 하면 캘리브레이션 재실행 시 axis_config.yaml을 건드리지 않아도 되고,
> 여러 모듈이 잘못된 임시 range를 참조하는 사고를 방지한다.

**sigak/data/axis_config.yaml** — 축 정의 전용 (통계값 없음)

```yaml
version: "3axis_v1"
axes:
  shape:
    name_kr: "외형"
    low: "Soft"
    high: "Sharp"
    low_kr: "소프트"
    high_kr: "샤프"
    description_kr: "골격과 이목구비가 만드는 전체적인 형태"
    features:
      jaw_angle: {weight: 0.25, direction: "low_is_positive"}       # 각도 낮을수록 sharp(+1)
      cheekbone_prominence: {weight: 0.25, direction: "high_is_positive"}  # 돌출 높을수록 sharp(+1)
      eye_tilt: {weight: 0.20, direction: "high_is_positive"}       # 올라갈수록 sharp(+1)
      brow_arch: {weight: 0.15, direction: "high_is_positive"}      # 아치 높을수록 sharp(+1)
      eye_ratio: {weight: 0.15, direction: "low_is_positive"}       # h/w 비율. 낮을수록(가로 긴 눈) sharp(+1). 높으면 둥근 눈=soft.
  volume:
    name_kr: "존재감"
    low: "Subtle"
    high: "Bold"
    low_kr: "서틀"
    high_kr: "볼드"
    description_kr: "이목구비의 크기와 볼륨이 만드는 존재감"
    features:
      eye_width_ratio: {weight: 0.30, direction: "high_is_positive"}  # 클수록 bold(+1)
      lip_fullness: {weight: 0.25, direction: "high_is_positive"}     # 도톰할수록 bold(+1)
      nose_bridge_height: {weight: 0.25, direction: "high_is_positive"}  # 높을수록 bold(+1)
      brow_eye_distance: {weight: 0.20, direction: "low_is_positive", fallback: "reweight"}  # 가까울수록 bold(+1)
  age:
    name_kr: "무드"
    low: "Fresh"
    high: "Mature"
    low_kr: "프레시"
    high_kr: "매추어"
    description_kr: "얼굴 비율이 주는 나이 인상과 분위기"
    features:
      forehead_ratio: {weight: 0.35, direction: "high_is_positive"}   # 클수록 mature(+1)
      philtrum_ratio: {weight: 0.35, direction: "high_is_positive"}   # 길수록 mature(+1)
      face_length_ratio: {weight: 0.30, direction: "high_is_positive"}  # 길수록 mature(+1)
```

**sigak/data/calibration_3axis.yaml** — 통계값 전용 (Phase 0-3 산출물)

```yaml
# Phase 0-3 캘리브레이션 산출물.
# coordinate.py는 이 파일에서만 observed_ranges를 로드한다.
# 재캘리브레이션 시 이 파일만 교체하면 전체 반영.

observed_ranges:
  jaw_angle: [90.1, 117.2]           # SCUT-FBP5500 AF p10~p90 (2026-04-08)
  cheekbone_prominence: [0.522, 0.746]
  eye_tilt: [-1.06, 5.50]
  brow_arch: [0.026, 0.037]
  eye_ratio: [0.284, 0.41]
  eye_width_ratio: [0.178, 0.214]
  lip_fullness: [0.003, 0.106]
  nose_bridge_height: [0.472, 0.573]
  brow_eye_distance: [0.1, 0.4]      # 추정값. Phase 0-3에서 실측 후 교체.
  forehead_ratio: [0.354, 0.465]
  philtrum_ratio: [0.206, 0.339]
  face_length_ratio: [1.158, 1.293]

# 아래는 캘리브레이션 스크립트가 채우는 영역 (Phase 0-3 산출물)
axis_distribution: {}   # {shape: {mean, std}, volume: {...}, age: {...}}
axis_correlation: {}    # {shape_volume: r, shape_age: r, volume_age: r}
sigma: 1.0              # similarity 거리 계산용 sigma
```

#### 0-3. 캘리브레이션 실행

기존 calibrate_face_stats.py를 확장:
- brow_eye_distance 포함하여 12피처 전체 재캘리브레이션
- 3축 좌표 계산 (임시 compute) → 축 분포 + 축간 상관계수 출력

산출물: `sigak/data/calibration_3axis.yaml`
```yaml
observed_ranges:
  brow_eye_distance: {p10: TBD, p90: TBD}  # 핵심: 이 값으로 axis_config.yaml 업데이트

axis_distribution:
  shape: {mean, std, min, max}
  volume: {mean, std, min, max}
  age: {mean, std, min, max}

axis_correlation:
  shape_volume: TBD   # |r| < 0.30 필수
  shape_age: TBD
  volume_age: TBD
```

**검증 게이트**:
- [ ] 12피처 전부 추출 성공률 > 95%
- [ ] brow_eye_distance 관측 범위 산출 완료
- [ ] 축간 |상관계수| < 0.30
- [ ] 3축 좌표 분포가 한쪽으로 과도 치우침 없음 (|mean| < 0.3)

---

### Phase 1: coordinate.py 전면 교체 (0.5일)

#### 변경 내용

1. AxisDefinition 클래스 삭제 → axis_config.yaml에서 로드
2. AXES 리스트 삭제 → YAML 파싱 결과 사용
3. compute_structure/impression/maturity/intensity 4개 함수 삭제
4. 새 compute_coordinates():
   ```python
   def compute_coordinates(features: dict) -> dict[str, float]:
       axis_config = _load_axis_config()       # axis_config.yaml
       cal = _load_calibration()               # calibration_3axis.yaml
       coords = {}
       for axis_name, axis_def in axis_config["axes"].items():
           components = []
           for feat_name, feat_def in axis_def["features"].items():
               raw = features.get(feat_name)
               if raw is None:
                   continue
               obs_range = cal["observed_ranges"][feat_name]
               normalized = _normalize(raw, obs_range)
               if feat_def["direction"] == "low_is_positive":
                   normalized = -normalized
               components.append((normalized, feat_def["weight"]))
           coords[axis_name] = _weighted_fallback(components)
       return coords
   ```
5. compute_gap() 3축 기반 재작성
6. get_axis_labels() → axis_config.yaml에서 읽도록 변경
7. OBSERVED_RANGES 삭제 → calibration_3axis.yaml에서 로드 (_load_calibration())

#### 유지하는 코드

- _has_valid(), _normalize(), _weighted_fallback() — 범용 유틸, 그대로 사용
- get_axis_labels(), get_all_axis_labels() — 시그니처 유지, 내부만 YAML 로드로 변경

**검증 게이트**:
- [ ] compute_coordinates() → 3축 좌표 출력 {"shape", "volume", "age"}
- [ ] 전 축 [-1, +1] 범위
- [ ] brow_eye_distance=None 시 volume 축 나머지 3피처로 정상 fallback
- [ ] compute_gap() → 3축 벡터, primary_shift_kr이 YAML 라벨과 일치
- [ ] get_axis_labels("shape") → {"name_kr": "외형", "low": "소프트", "high": "샤프", ...}

---

### Phase 2: 데이터 + similarity + cluster 교체 (0.5일)

#### 2-1. type_anchors.json 전면 교체

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
      "description_kr": "...",
      "features_bullet": ["...", "...", "..."],
      "aliases": ["첫사랑", "강아지상", "소프트프레시"]
    }
  }
}
```

삭제 필드: axes_3d, axes_3d_definition, axis_roles, community_score, anchor_version, reference_coords
추가 필드: coords (3축), quadrant, one_liner, features_bullet

#### 2-2. similarity.py 교체

- axis_labels dict 삭제 → `from pipeline.coordinate import get_axis_labels` import
- 4축 axes 리스트 → `list(config["axes"].keys())` 또는 하드코딩 `["shape", "volume", "age"]`
- 3축 유클리드 거리 기반 매칭 (기존 로직 구조 유지, 축만 변경)

#### 2-3. cluster.py 최소 범위 교체

> **판단**: cluster.py는 main.py:274에서 호출되며 결과가 리포트에 포함됨 (user-facing).
> coordinate.py가 3축을 출력하면 cluster.py의 `for axis in ["structure", ...]` 루프가 즉시 깨지므로
> Phase 2에서 같이 가야 함. 단, **클러스터링 알고리즘 자체(K-Means, PCA)는 구조 피처 기반이라 축과 무관** — 건드리지 않음.
> 교체 범위: 축 이름 참조 + 시그니처 매칭만. 나머지는 그대로.

변경 항목:
- _SIGN_TO_LABEL → 3축 기반 재정의 (극성을 coordinate.py 기준으로 통일)
  ```python
  _SIGN_TO_LABEL = {
      "shape": {"negative": "soft", "positive": "sharp", "any": "any"},
      "volume": {"negative": "subtle", "positive": "bold", "any": "any"},
      "age": {"negative": "fresh", "positive": "mature", "any": "any"},
  }
  ```
- `for axis in ["structure", "impression", "maturity", "intensity"]` → `["shape", "volume", "age"]` (line 535, 745)
- LABEL_CANDIDATES → 8앵커 시그니처로 재작성

**변경하지 않는 것**: K-Means 로직, PCA loadings, 구조 피처 기반 클러스터링, 거리 계산

#### 2-4. celeb_anchors.json → 즉시 삭제

> **감사 결과**: 파이프라인 전체(similarity.py, cluster.py, face_comparison.py, main.py)에서
> celeb_anchors.json을 로드하는 코드가 **0건**. db.py의 테이블명만 참조.
> 따라서 즉시 삭제. 나중에 필요하면 3축 기반으로 재생성.

**검증 게이트**:
- [ ] 8앵커 JSON 정상 로드
- [ ] 테스트 좌표 → 가장 가까운 앵커 매칭 직관적
- [ ] cluster 시그니처 매칭 정상

---

### Phase 3: LLM + formatter + action_spec 교체 (1일)

#### 3-1. llm.py

인터뷰 시스템 프롬프트 교체:
```
3축 좌표계:
- shape [-1, +1]: Soft(둥글고 부드러운 골격) ↔ Sharp(날카롭고 선명한 골격)
- volume [-1, +1]: Subtle(작고 섬세한 이목구비) ↔ Bold(크고 존재감 있는 이목구비)
- age [-1, +1]: Fresh(어리고 생기있는 비율) ↔ Mature(성숙하고 정돈된 비율)
```

출력 포맷: `{"coordinates": {"shape": 0.1, "volume": 0.3, "age": -0.3}, ...}`

#### 3-2. report_formatter.py

- _AXIS_DISPLAY_OVERRIDES 삭제 → get_axis_labels()로 통합
- GAP_RECOMMENDATION_TEMPLATES → 3축 기반 재작성 (6→6 템플릿, 3축×2방향)
- DIRECTION_STYLING_TIPS → 3축 기반 재작성
- direction_items 생성 → 3축 순회
- aesthetic_map JSON 생성 로직 추가:
  ```python
  aesthetic_map = {
      "current": {"x": coords["shape"], "y": coords["age"], "size": coords["volume"]},
      "aspiration": {"x": asp["shape"], "y": asp["age"], "size": asp["volume"]},
      "x_axis": get_axis_labels("shape"),
      "y_axis": get_axis_labels("age"),
      "size_axis": get_axis_labels("volume"),
      "quadrants": {
          "top_left": "Soft Mature", "top_right": "Sharp Mature",
          "bottom_left": "Soft Fresh", "bottom_right": "Sharp Fresh",
      },
  }
  ```

#### 3-3. action_spec.py

AXIS_ACTION_RULES → 3축 기반 18규칙 (3축×2방향×3규칙):

```python
AXIS_ACTION_RULES = {
    "shape": {
        "increase": [  # → Sharp
            {"zone": "jawline", "method": "contour_shading", "goal": "턱선 정리로 윤곽 선명화", "base_score": 0.9},
            {"zone": "nose_bridge", "method": "highlight", "goal": "코 중심축 강조", "base_score": 0.7},
            {"zone": "brow_tail", "method": "sharp_draw", "goal": "눈썹 끝 정리로 선명한 인상", "base_score": 0.6},
        ],
        "decrease": [  # → Soft
            {"zone": "cheek_apple", "method": "round_blush", "goal": "볼 중심 볼륨감으로 부드러운 인상", "base_score": 0.9},
            {"zone": "jawline", "method": "highlight", "goal": "턱선 경계 완화", "base_score": 0.7},
            {"zone": "brow_arch", "method": "rounded_draw", "goal": "눈썹 곡선화로 부드러운 인상", "base_score": 0.6},
        ],
    },
    "volume": {
        "increase": [  # → Bold
            {"zone": "eye_crease", "method": "shadow_depth", "goal": "눈두덩 음영으로 깊은 눈매", "base_score": 0.9},
            {"zone": "lip", "method": "full_color", "goal": "립 컬러 강조로 존재감", "base_score": 0.75},
            {"zone": "nose_tip", "method": "subtle_shadow", "goal": "코끝 음영으로 오목한 느낌", "base_score": 0.6},
        ],
        "decrease": [  # → Subtle
            {"zone": "overall", "method": "matte_base", "goal": "전체 매트 베이스로 차분한 느낌", "base_score": 0.9},
            {"zone": "lip", "method": "nude_tone", "goal": "자연스러운 립 톤으로 부담감 완화", "base_score": 0.75},
            {"zone": "brow", "method": "feathered_draw", "goal": "자연스러운 눈썹결로 힘 빼기", "base_score": 0.6},
        ],
    },
    "age": {
        "increase": [  # → Mature
            {"zone": "cheekbone", "method": "contour_shading", "goal": "광대 음영으로 성숙한 윤곽", "base_score": 0.85},
            {"zone": "brow", "method": "straight_draw", "goal": "일자 눈썹으로 정돈된 인상", "base_score": 0.7},
            {"zone": "lip", "method": "defined_line", "goal": "립라인 정리로 단정한 느낌", "base_score": 0.6},
        ],
        "decrease": [  # → Fresh
            {"zone": "cheek_apple", "method": "bright_blush", "goal": "볼 사과존 블러셔로 어려 보이는 효과", "base_score": 0.85},
            {"zone": "under_eye", "method": "bright_concealer", "goal": "눈 밑 밝기로 동안 느낌", "base_score": 0.7},
            {"zone": "lip_center", "method": "gloss_highlight", "goal": "입술 중앙 광택으로 생기", "base_score": 0.6},
        ],
    },
}
```

TYPE_MODIFIERS → 하드코딩 삭제, type_anchors.json coords에서 자동 파생.

```python
# type_anchors.json 로드 → coords 값으로 modifier 자동 결정
def _derive_type_modifier(anchor_coords: dict) -> dict:
    """앵커 좌표에서 스타일 톤, 쉐딩 강도, zone 부스트를 파생."""
    shape_val = anchor_coords.get("shape", 0)
    volume_val = anchor_coords.get("volume", 0)
    age_val = anchor_coords.get("age", 0)
    
    # shading_intensity: soft일수록 minimal, sharp일수록 strong
    if shape_val < -0.3:
        shading = "minimal"
    elif shape_val < 0.3:
        shading = "light"
    else:
        shading = "medium"
    
    # zone_boost: 좌표에서 자동 결정
    zone_boost = {}
    if volume_val > 0.3:
        zone_boost["eye_crease"] = 0.2
        zone_boost["lip"] = 0.2
    if shape_val > 0.3:
        zone_boost["jawline"] = 0.2
    
    return {"shading_intensity": shading, "zone_boost": zone_boost, ...}
```

> 핵심: 8앵커를 수동으로 재정의하지 않는다. type_anchors.json의 coords가 SSOT.
> 새 앵커가 추가되거나 좌표가 보정돼도 modifier가 자동으로 따라간다.

> **주의**: action_spec.py 구현은 본 문서의 축 방향과 규칙 초안을 따르되,
> 세부 zone-to-axis 기여표는 Phase 3 착수 직전에 별도 상세 설계서로 확정한다.
> 18규칙의 zone/method/goal은 현재 초안이며, 오버레이 렌더러와의 정합성을 확인 후 최종 확정.

**검증 게이트**:
- [ ] 리포트 전체 생성 → 3축 디테일 카드 정상 출력
- [ ] gap_summary에 올바른 라벨 사용 (axis_config.yaml 기준)
- [ ] LLM 해설에 structure/impression/maturity/intensity 잔재 없음
- [ ] aesthetic_map JSON이 리포트에 포함됨
- [ ] action_plan zone별 방향 태그가 3축 기반

---

### Phase 4: 프론트엔드 교체 (0.5일)

#### 4-1. 타입 정의 변경

```typescript
// 기존 (삭제)
interface Coordinates { structure: number; impression: number; maturity: number; intensity: number; }

// 신규
interface Coordinates { shape: number; volume: number; age: number; }
```

#### 4-2. gap-scatter-plot.tsx 전면 재작성

- AXIS_META, CONNECTIVE_MAP, pickTopTwoAxes() 전량 삭제
- aesthetic_map 기반 고정 2D 렌더링:
  - X축: Shape (Soft ↔ Sharp), Y축: Age (Fresh ↔ Mature)
  - 점 크기: Volume (Subtle = 작은 점, Bold = 큰 점)
  - 사분면 라벨: 백엔드 aesthetic_map.quadrants에서 읽음
  - 축 라벨: 백엔드 aesthetic_map.x_axis / y_axis에서 읽음

#### 4-3. gap-analysis.tsx 교체

- AXIS_LABELS, AXIS_END_LABELS 전량 삭제
- direction_items 렌더링: 백엔드가 내려주는 필드를 직접 사용
- fallback 없음 — 백엔드가 항상 라벨을 포함하도록 보장

**백엔드 → 프론트 API 계약: direction_items 스키마**

> 백엔드 report_formatter.py가 생성하는 direction_items의 각 아이템은
> 반드시 아래 필드를 **전부** 포함해야 한다. 프론트는 이 필드만 읽으며 자체 fallback을 갖지 않는다.

```typescript
interface DirectionItem {
  axis: string;              // "shape" | "volume" | "age"
  name_kr: string;           // "외형" | "존재감" | "무드"
  axis_description: string;  // "골격과 이목구비가 만드는 전체적인 형태"
  label_low: string;         // "소프트" | "서틀" | "프레시"
  label_high: string;        // "샤프" | "볼드" | "매추어"
  from_score: number;        // 현재 좌표 [-1, 1]
  to_score: number;          // 추구미 좌표 [-1, 1]
  delta: number;             // |to - from|
  from_label: string;        // "약간 소프트"
  to_label: string;          // "샤프"
  difficulty: string;        // "작은 변화" | "중간 변화" | "큰 변화"
  recommendation: string;    // 축별 추천 텍스트
}
```

이 계약은 report_formatter.py의 direction_items 생성 로직 (현재 line 873-886)과 정합해야 한다.

#### 4-4. mock-report.ts 업데이트

4축 좌표 → 3축으로 전면 교체.

#### 4-5. app/page.tsx

AXES 상수를 3축 시스템과 일치시킴.

**검증 게이트**:
- [ ] pnpm build 에러 0
- [ ] tsc 에러 0
- [ ] lint 에러 0
- [ ] 2D 맵에 현재/추구 점 정상
- [ ] 사분면 라벨 4개 정상
- [ ] Volume 점 크기 시각적 구분 가능
- [ ] 3축 디테일 카드 정상 렌더링

---

### Phase 5: 레거시 청소 + E2E (0.5일)

#### 5-1. 코드베이스 전체 검색 — 전부 0건 필수

```bash
grep -r "\"structure\"" --include="*.py" --include="*.tsx" --include="*.ts" --include="*.json" sigak/ sigak-web/
grep -r "\"impression\"" --include="*.py" --include="*.tsx" --include="*.ts" --include="*.json" sigak/ sigak-web/
grep -r "\"maturity\"" --include="*.py" --include="*.tsx" --include="*.ts" --include="*.json" sigak/ sigak-web/
grep -r "\"intensity\"" --include="*.py" --include="*.tsx" --include="*.ts" --include="*.json" sigak/ sigak-web/
grep -r "axes_3d" --include="*.json" sigak/
grep -r "AXIS_META" --include="*.tsx" sigak-web/
grep -r "AXIS_END_LABELS" --include="*.tsx" sigak-web/
grep -r "CONNECTIVE_MAP" --include="*.tsx" sigak-web/
grep -r "pickTopTwoAxes" --include="*.tsx" sigak-web/
```

허용 예외: 이 migration-3axis.md 문서, feedback.md/roadmap.md/problems.md (삭제 또는 아카이브)

#### 5-2. 빌드 검증

- pnpm build 에러 0
- tsc 에러 0
- lint 에러 0

#### 5-3. E2E 테스트

- [ ] 사진 업로드 → face.py → 12피처 + brow_eye_distance 추출
- [ ] coordinate.py → 3축 좌표 정상
- [ ] similarity → 8앵커 매칭 정상
- [ ] cluster → 시그니처 라벨링 정상
- [ ] LLM → 3축 기반 인터뷰 해석
- [ ] report_formatter → 리포트 JSON (aesthetic_map 포함)
- [ ] 프론트 → 전 섹션 렌더링 (2D맵 + 디테일 카드 + 액션플랜)
- [ ] 결제 플로우 정상

#### 5-4. 레거시 문서 처리

- feedback.md → 이 문서로 대체 (삭제 또는 archive/ 이동)
- roadmap.md → Phase 7~12만 별도 파일로 분리
- problems.md → 이슈 전부 해결 확인 후 삭제

---

## 타임라인

| Phase | 작업 | 예상 | 의존성 |
|---|---|---|---|
| 0 | 선행 준비 (brow_eye_distance + YAML + 캘리브레이션) | 0.5일 | 없음 |
| 1 | coordinate.py 전면 교체 | 0.5일 | Phase 0 |
| 2 | 데이터 + similarity + cluster | 0.5일 | Phase 1 |
| 3 | LLM + formatter + action_spec | 1일 | Phase 1 |
| 4 | 프론트엔드 | 0.5일 | Phase 2, 3 |
| 5 | 레거시 청소 + E2E | 0.5일 | Phase 4 |

**총 예상: 3~4일**

```
Day 1: Phase 0 + Phase 1
Day 2: Phase 2 + Phase 3 (formatter/llm)
Day 3: Phase 3 (action_spec) + Phase 4
Day 4: Phase 5 (E2E + cleanup)
```

Phase 2와 3은 Phase 1 완료 후 병렬 시작 가능 (파일 충돌 없음).

---

*이 문서가 feedback.md, roadmap.md(Phase 0~6), problems.md를 대체합니다.*
*roadmap.md Phase 7~12 (오버레이, 스킨톤, 확장)는 별도 문서로 분리합니다.*
*Generated: 2026-04-09*
