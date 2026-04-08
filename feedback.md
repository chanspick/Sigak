# SIGAK 파이프라인 리팩토링 — Claude Code 실행 지시서 (Final)

> 이 문서를 CLAUDE.md와 함께 참조하여 실행.
> 전체 목표: 최소 변경으로 리포트 품질의 최대 체감 개선.
> 절대 금지: 새 모델 도입, 인프라 변경, 대규모 리팩토링.

---

## 실행 순서

```
Day 0   버그픽스 (B-1~B-5)
Day 0   Feature availability 점검 (F-0, F-0.5)
Day 1   Phase 1: 좌표 안정화 + interpret_interview 축 보정
Day 1   앵커 좌표 재계산 (상위 5개 타입)
Day 2   Phase 2: build_action_spec() + build_overlay_plan()
Day 2   Phase 3: Claude 입력 축소 + 출력 구조화 + parse fallback
Day 3   Phase 4: run_analysis() 연결
Day 3   검증 + 샘플 리포트 QA
```

---

## Phase 0: 버그픽스 + 사전 점검

### B-1. 중복 텍스트 렌더링 버그
- `llm.py` 프롬프트 placeholder 확인
- `report_formatter.py`에서 같은 필드를 여러 섹션에 재사용하는지 확인
- 강도/구조/성숙도 설명이 동일 텍스트로 반복 출력되는 원인 특정 후 수정

### B-2. Action Plan 달성률 % 제거
- 21% × 4 = 84% 표기 삭제
- "우선순위 1/2/3/4" 순서 표기로 대체하거나 % 자체 제거

### B-3. raw delta 직접 노출 제거
- "추 거리 0.62", "delta 0.43" 등 프론트 노출 중단
- `report_formatter.py`에서 raw score 필터링
- API response에서도 기본 숨김. debug mode에서만 포함

### B-4. "강도(Intensity)" 워딩 변경
- "존재감(Presence)"으로 변경 ("대비감"은 색/명암으로 오해 가능)
- UI 텍스트 + 프롬프트 양쪽 반영

### B-5. Action Spec ↔ 리포트 일치 검증
- Phase 2 완료 후 적용
- 개수 일치 + zone 일치까지 검증:
```python
assert len(report["action_tips"]) == len(action_spec.recommended_actions)
for tip, rec in zip(report["action_tips"], action_spec.recommended_actions):
    assert tip["zone"] == rec.zone, f"zone mismatch: {tip['zone']} != {rec.zone}"
```
- `generate_report()` 직후, `format_report_for_frontend()` 이전에 배치

---

### F-0. Feature availability 점검

Phase 1에서 새로 사용할 feature가 안정적으로 존재하는지 확인.

```python
REQUIRED_FEATURES = [
    "eye_tilt",           # 눈꼬리 각도
    "brow_arch",          # 눈썹 아치 — ⚠️ 불안정 가능성
    "eye_ratio",          # 눈 높이/너비
    "lip_fullness",       # 입술 두께
    "nose_bridge_height", # 코 높이 — ⚠️ 불안정 가능성
    "eye_width_ratio",    # 눈 너비 비율
]

OPTIONAL_FEATURES = [
    "brow_eye_distance",  # 눈-눈썹 거리 — 없을 수 있음
]

# v1에 있었으나 v2에서 제외: symmetry_score
# 이유: intensity를 "존재감" 중심으로 재정의하면서 대칭성은 별도 축에 더 적합
```

**체크리스트:**
- [ ] 각 feature가 `FaceFeatures` dataclass에 존재하는가
- [ ] InsightFace 경로와 MediaPipe 경로 모두에서 값이 나오는가
- [ ] null, 추정치, 하드코딩이 섞이지 않는가
- [ ] 메이크업 유무에 따라 추정 편차가 큰 feature가 있는가 (특히 `lip_fullness`, `brow_arch`)

**불안정한 feature가 있으면:**
해당 feature를 축 정의에서 제외. 나머지 feature로 가중치 자동 재분배 (2-4의 fallback reweighting 패턴 적용).

---

### F-0.5. normalize range 샘플 기반 설정

```python
# 내부 테스트 이미지 20~30장으로 실행
for feature_name in REQUIRED_FEATURES:
    values = [getattr(analyze_face(img), feature_name) for img in sample_images]
    print(f"{feature_name}: min={min(values):.3f} max={max(values):.3f} "
          f"median={sorted(values)[len(values)//2]:.3f} "
          f"p10={sorted(values)[len(values)//10]:.3f} "
          f"p90={sorted(values)[9*len(values)//10]:.3f}")
```

**규칙:**
- normalize range는 p10 ~ p90 기준
- 범위 밖 값은 clamp (최종 축에 `clip(score, -1, 1)` 적용)

이 결과로 Phase 1의 `OBSERVED_RANGES`를 확정.

---

## Phase 1: 좌표 안정화

### 대상 파일: `sigak/coordinate.py`

### 1-0. 전축 CLIP 의존도 제거

```python
AXIS_WEIGHTS = {
    "structure":  {"structural": 1.0, "clip": 0.0},
    "impression": {"structural": 1.0, "clip": 0.0},
    "maturity":   {"structural": 1.0, "clip": 0.0},
    "intensity":  {"structural": 1.0, "clip": 0.0},
}
# CLIP 정상화 후 점진적 복원을 위해 config/환경변수로 분리 권장
```

### 1-1. impression 축 재정의

**내부 의미:** soft ↔ sharp (이목구비가 주는 인상의 부드러움 vs 날카로움)
**외부 UI 라벨:** "인상 방향성" (임시 중립 표현, 다음 스프린트에서 정식 확정)

```python
def compute_impression(features: dict) -> float:
    """
    soft(-1) ↔ sharp(+1)
    눈매 방향성 + 눈썹 형태 + 눈 비율 + 입술 볼륨이 만드는 전체 인상.
    """
    components = []

    # 눈꼬리 각도: 올라갈수록 sharp
    if _has_valid(features, "eye_tilt"):
        val = _normalize(features["eye_tilt"], OBSERVED_RANGES["eye_tilt"])
        components.append((val, 0.35))

    # 눈썹 아치: 높을수록 sharp
    if _has_valid(features, "brow_arch"):
        val = _normalize(features["brow_arch"], OBSERVED_RANGES["brow_arch"])
        components.append((val, 0.25))

    # 눈 비율(높이/너비): 가로로 길수록(값이 작을수록) sharp
    if _has_valid(features, "eye_ratio"):
        raw = _normalize(features["eye_ratio"], OBSERVED_RANGES["eye_ratio"])
        val = -(raw * 2 - 1)  # 반전: 작을수록 sharp
        components.append((val, 0.25))

    # 입술 두께: 도톰할수록 soft
    if _has_valid(features, "lip_fullness"):
        val = -_normalize(features["lip_fullness"], OBSERVED_RANGES["lip_fullness"])
        components.append((val, 0.15))

    return _weighted_fallback(components)
```

### 1-2. intensity 축 재정의

```python
def compute_intensity(features: dict) -> float:
    """
    natural(-1) ↔ bold(+1)
    이목구비의 존재감. symmetry_score는 이 축에서 제외 (별도 축에 더 적합).
    """
    components = []

    # 눈 크기: 클수록 bold
    if _has_valid(features, "eye_width_ratio"):
        val = _normalize(features["eye_width_ratio"], OBSERVED_RANGES["eye_width_ratio"])
        components.append((val, 0.30))

    # 입술 두께: 도톰할수록 bold
    if _has_valid(features, "lip_fullness"):
        val = _normalize(features["lip_fullness"], OBSERVED_RANGES["lip_fullness"])
        components.append((val, 0.25))

    # 코 높이: 높을수록 bold
    if _has_valid(features, "nose_bridge_height"):
        val = _normalize(features["nose_bridge_height"], OBSERVED_RANGES["nose_bridge_height"])
        components.append((val, 0.25))

    # 눈-눈썹 거리: 가까울수록 bold (optional feature)
    if _has_valid(features, "brow_eye_distance"):
        val = -_normalize(features["brow_eye_distance"], OBSERVED_RANGES["brow_eye_distance"])
        components.append((val, 0.20))

    return _weighted_fallback(components)
```

### 1-2.5. 공통 헬퍼 함수

```python
def _has_valid(features: dict, key: str) -> bool:
    """feature가 존재하고 None이 아닌지 확인"""
    return key in features and features[key] is not None

def _normalize(value: float, observed_range: tuple[float, float]) -> float:
    """관측 범위 기반 정규화. 범위 밖 값은 clamp."""
    lo, hi = observed_range
    if hi <= lo:
        return 0.0
    value = min(max(value, lo), hi)
    return (value - lo) / (hi - lo) * 2 - 1  # → [-1, 1]

def _weighted_fallback(components: list[tuple[float, float]]) -> float:
    """
    사용 가능한 component만으로 가중 평균. 
    feature 미존재 시 나머지로 가중치 자동 재분배.
    """
    if not components:
        return 0.0
    weight_sum = sum(w for _, w in components)
    score = sum(v * w for v, w in components) / weight_sum
    return max(-1.0, min(1.0, score))

# normalize range — F-0.5에서 확정한 실측값으로 교체할 것
OBSERVED_RANGES: dict[str, tuple[float, float]] = {
    "eye_tilt": (0.0, 10.0),          # placeholder, 실측값으로 교체
    "brow_arch": (0.0, 1.0),
    "eye_ratio": (0.2, 0.5),
    "lip_fullness": (0.3, 0.8),
    "eye_width_ratio": (0.2, 0.35),
    "nose_bridge_height": (0.0, 1.0),
    "brow_eye_distance": (0.1, 0.4),
}
```

### 1-3. interpret_interview() 축 정의 보정

**대상: `sigak/llm.py` → `interpret_interview()` system prompt**

```python
AXIS_DEFINITIONS_FOR_INTERVIEW = """
4축 좌표계:
- structure [-1, +1]: soft(둥글고 부드러운 골격) ↔ sharp(날카롭고 선명한 골격)
- impression [-1, +1]: soft(부드럽고 온화한 인상) ↔ sharp(시원하고 선명한 인상)
- maturity [-1, +1]: fresh(어리고 생기있는) ↔ mature(성숙하고 정돈된)
- intensity [-1, +1]: natural(자연스럽고 담백한) ↔ bold(강렬하고 존재감 있는)
"""
```

기존 system prompt의 축 정의 부분만 이것으로 교체. 나머지 프롬프트 구조는 유지.

### 1-4. 앵커 좌표 재계산

**착수 전 확인:**
- [ ] 15개 타입 앵커 좌표의 저장 위치 (type_anchors.json? DB? 하드코딩?)
- [ ] 수동 정의 vs 데이터 기반
- [ ] 수정 난이도

**우선 재계산 대상:**
```python
PRIORITY_ANCHOR_TYPES = [
    "warm_first_love",
    "cool_goddess",
    "fresh_face",
    "elegant_classic",
    "bold_queen",
]
```

**나머지 10개 타입 정책:**
- temporary legacy anchor로 유지
- 새 좌표계와 옛 앵커 사이에 왜곡 가능성 있음
- QA는 상위 5개 빈도 케이스 중심으로 진행
- debug trace에 `anchor_version: "v2" | "legacy"` 표시 권장

---

## Phase 2: Action Spec 레이어 추가

### 대상: 신규 파일 `sigak/action_spec.py`

### 2-0. 설계 원칙

**의사결정 우선순위 (코드와 문서에 명시):**
1. 유저 목표 방향은 `gap`이 결정
2. 어느 부위를 우선할지는 `type_delta` + `TYPE_MODIFIERS`가 보정
3. 실행 강도는 `TYPE_MODIFIERS.shading_intensity`가 조정

**함수 분리:**
- `build_action_spec()` → 의미 레이어 (방향 + 부위 + 강도)
- `build_overlay_plan()` → 시각 레이어 (zone name + 색상 + 투명도)

### 2-1. 데이터 구조

```python
from dataclasses import dataclass, field

@dataclass
class VisualPriority:
    zone: str
    importance: float
    reason: str
    axis: str
    delta_direction: str  # "increase" | "decrease"

@dataclass
class RecommendedAction:
    zone: str
    method: str
    goal: str
    priority: int  # 1, 2, 3, 4

@dataclass
class AvoidAction:
    zone: str
    method: str
    reason: str

@dataclass
class ActionSpec:
    matched_type_id: str
    matched_type_label: str
    primary_gap_axis: str
    visual_priorities: list[VisualPriority]       # 최대 3개
    recommended_actions: list[RecommendedAction]   # 2~4개 (최소 2개 보장)
    avoid_actions: list[AvoidAction]               # 최대 2개
    expected_effects: list[str]                    # 2~3문장
    report_mode: str                               # "makeup_female_v0"
    _debug_trace: dict = field(default_factory=dict, repr=False)
```

### 2-2. 축별 공통 Action 룰 테이블

```python
AXIS_ACTION_RULES: dict[str, dict[str, list[dict]]] = {
    "structure": {
        "increase": [
            {"zone": "jawline", "method": "contour_shading", "goal": "턱선 정리로 윤곽 선명화", "base_score": 0.9},
            {"zone": "temple", "method": "light_shading", "goal": "관자놀이 정리로 상안부 균형", "base_score": 0.7},
            {"zone": "nose_bridge", "method": "highlight", "goal": "코 중심축 강조", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "mid_cheek", "method": "soft_blush", "goal": "볼 중심 볼륨감으로 부드러운 인상", "base_score": 0.9},
            {"zone": "jawline", "method": "highlight", "goal": "턱선 경계 완화", "base_score": 0.7},
            {"zone": "forehead_center", "method": "highlight", "goal": "이마 중앙 볼륨으로 부드러움", "base_score": 0.6},
        ],
    },
    "impression": {
        "increase": [
            {"zone": "outer_eye", "method": "upward_line", "goal": "눈꼬리 방향 정리로 시원한 눈매", "base_score": 0.9},
            {"zone": "brow_tail", "method": "sharp_draw", "goal": "눈썹 끝 정리로 선명한 인상", "base_score": 0.75},
            {"zone": "lip_corner", "method": "slight_upturn", "goal": "입꼬리 각도 정리", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "under_eye", "method": "soft_highlight", "goal": "눈 아래 밝기로 부드러운 눈매", "base_score": 0.9},
            {"zone": "brow_arch", "method": "rounded_draw", "goal": "눈썹 곡선화로 부드러운 인상", "base_score": 0.75},
            {"zone": "lip_center", "method": "volume_highlight", "goal": "입술 중앙 볼륨감", "base_score": 0.6},
        ],
    },
    "maturity": {
        "increase": [
            {"zone": "cheekbone", "method": "contour_shading", "goal": "광대 음영으로 성숙한 윤곽", "base_score": 0.85},
            {"zone": "brow", "method": "straight_draw", "goal": "일자 눈썹으로 정돈된 인상", "base_score": 0.7},
            {"zone": "lip", "method": "defined_line", "goal": "립라인 정리로 단정한 느낌", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "cheek_apple", "method": "round_blush", "goal": "볼 사과존 블러셔로 어려 보이는 효과", "base_score": 0.85},
            {"zone": "under_eye", "method": "bright_concealer", "goal": "눈 밑 밝기로 동안 느낌", "base_score": 0.7},
            {"zone": "lip_center", "method": "gloss_highlight", "goal": "입술 중앙 광택으로 생기", "base_score": 0.6},
        ],
    },
    "intensity": {
        "increase": [
            {"zone": "eye_crease", "method": "shadow_depth", "goal": "눈두덩 음영으로 깊은 눈매", "base_score": 0.85},
            {"zone": "lip", "method": "full_color", "goal": "립 컬러 강조로 존재감", "base_score": 0.75},
            {"zone": "nose_tip", "method": "subtle_shadow", "goal": "코끝 음영으로 오목한 느낌", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "overall", "method": "matte_base", "goal": "전체 매트 베이스로 차분한 느낌", "base_score": 0.85},
            {"zone": "lip", "method": "nude_tone", "goal": "자연스러운 립 톤으로 부담감 완화", "base_score": 0.75},
            {"zone": "brow", "method": "feathered_draw", "goal": "자연스러운 눈썹결로 힘 빼기", "base_score": 0.6},
        ],
    },
}

MAX_TARGET_AXES = 3
MIN_RECOMMENDED_ACTIONS = 2
MAX_RECOMMENDED_ACTIONS = 4
```

### 2-3. 타입별 modifier (v0: 5개만)

```python
TYPE_MODIFIERS: dict[str, dict] = {
    "warm_first_love": {
        "style_tone": "부드럽고 따뜻한",
        "shading_intensity": "light",
        "zone_boost": {"under_eye": 0.2, "cheek_apple": 0.15},
        "avoid_override": [
            {"zone": "jawline", "method": "hard_contour", "reason": "타입의 부드러운 인상과 충돌"}
        ],
    },
    "cool_goddess": {
        "style_tone": "선명하고 시크한",
        "shading_intensity": "medium",
        "zone_boost": {"outer_eye": 0.2, "cheekbone": 0.15},
        "avoid_override": [],
    },
    "fresh_face": {
        "style_tone": "맑고 생기있는",
        "shading_intensity": "minimal",
        "zone_boost": {"cheek_apple": 0.2, "lip_center": 0.1},
        "avoid_override": [
            {"zone": "cheekbone", "method": "contour_shading", "reason": "동안 인상이 깎일 수 있음"}
        ],
    },
    "elegant_classic": {
        "style_tone": "정돈되고 우아한",
        "shading_intensity": "medium",
        "zone_boost": {"brow": 0.15, "lip": 0.15},
        "avoid_override": [],
    },
    "bold_queen": {
        "style_tone": "강렬하고 존재감 있는",
        "shading_intensity": "strong",
        "zone_boost": {"eye_crease": 0.2, "lip": 0.15, "cheekbone": 0.1},
        "avoid_override": [],
    },
}
# 나머지 10개 타입: 공통 룰만 적용, modifier 없음
```

### 2-4. build_action_spec()

```python
def build_action_spec(
    face_features,  # FaceFeatures
    current_coords: dict[str, float],
    matched_type: dict,
    type_delta: dict[str, float],
    gap: dict,
    interview_intent: dict[str, str] | None = None,
) -> ActionSpec:
    """
    Layer 1: gap → 목표 방향 결정
    Layer 2: type_delta + modifier → 부위 우선순위 보정
    """
    debug_trace = {}

    # ── Layer 1: gap에서 target axes 추출 ──
    sorted_axes = sorted(gap["vector"].items(), key=lambda x: abs(x[1]), reverse=True)
    target_axes = []
    for axis, delta_val in sorted_axes:
        if abs(delta_val) < 0.1:
            continue
        direction = "increase" if delta_val > 0 else "decrease"
        target_axes.append((axis, direction, abs(delta_val)))
    target_axes = target_axes[:MAX_TARGET_AXES]

    primary_axis = target_axes[0][0] if target_axes else "structure"
    debug_trace["target_axes"] = [(a, d, round(m, 3)) for a, d, m in target_axes]

    # ── Layer 1.5: 공통 룰에서 action 후보 + base_score 수집 ──
    candidates = []
    for axis, direction, magnitude in target_axes:
        rules = AXIS_ACTION_RULES.get(axis, {}).get(direction, [])
        for rule in rules:
            score = rule["base_score"] * magnitude
            candidates.append({
                **rule, "axis": axis, "direction": direction, "score": score,
            })

    # ── Layer 2: type_delta로 zone importance 보정 ──
    type_zone_bonus = _derive_zone_bonus(type_delta)
    for c in candidates:
        c["score"] += type_zone_bonus.get(c["zone"], 0.0)
    debug_trace["type_zone_bonus"] = type_zone_bonus

    # ── Layer 2.5: 타입 modifier 적용 ──
    type_id = matched_type.get("key", "")
    modifier = TYPE_MODIFIERS.get(type_id, {})

    for c in candidates:
        c["score"] += modifier.get("zone_boost", {}).get(c["zone"], 0.0)

    avoid_actions = []
    for override in modifier.get("avoid_override", []):
        avoid_actions.append(AvoidAction(**override))
        candidates = [
            c for c in candidates
            if not (c["zone"] == override["zone"] and c["method"] == override["method"])
        ]
    debug_trace["modifier_applied"] = type_id or "none"

    # ── 최종 선택: score 기반 정렬 + zone 중복 제거 ──
    candidates.sort(key=lambda x: x["score"], reverse=True)

    visual_priorities = []
    recommended = []
    seen_zones = set()

    for c in candidates:
        if c["zone"] in seen_zones:
            continue
        seen_zones.add(c["zone"])

        if len(visual_priorities) < 3:
            visual_priorities.append(VisualPriority(
                zone=c["zone"], importance=round(c["score"], 2),
                reason=c["goal"], axis=c["axis"], delta_direction=c["direction"],
            ))
        if len(recommended) < MAX_RECOMMENDED_ACTIONS:
            recommended.append(RecommendedAction(
                zone=c["zone"], method=c["method"],
                goal=c["goal"], priority=len(recommended) + 1,
            ))

    # ── 최소 action 보장 (gap이 작거나 후보 부족 시) ──
    if len(recommended) < MIN_RECOMMENDED_ACTIONS:
        fallback_rules = AXIS_ACTION_RULES.get(primary_axis, {}).get("increase", [])
        for rule in fallback_rules:
            if rule["zone"] not in seen_zones and len(recommended) < MIN_RECOMMENDED_ACTIONS:
                recommended.append(RecommendedAction(
                    zone=rule["zone"], method=rule["method"],
                    goal=rule["goal"], priority=len(recommended) + 1,
                ))
                seen_zones.add(rule["zone"])

    debug_trace["final_actions"] = [r.zone for r in recommended]

    # ── 기대 효과 ──
    type_label = matched_type.get("name_kr", "")
    style_tone = modifier.get("style_tone", "")
    expected_effects = _generate_expected_effects(primary_axis, type_label, style_tone)

    return ActionSpec(
        matched_type_id=type_id,
        matched_type_label=type_label,
        primary_gap_axis=primary_axis,
        visual_priorities=visual_priorities,
        recommended_actions=recommended,
        avoid_actions=avoid_actions,
        expected_effects=expected_effects,
        report_mode="makeup_female_v0",
        _debug_trace=debug_trace,
    )


def _derive_zone_bonus(type_delta: dict[str, float]) -> dict[str, float]:
    """
    타입 대비 delta가 큰 축 → 관련 zone에 bonus.
    magnitude 기반 (v0). 방향 필터링은 다음 스프린트에서 정교화.
    """
    AXIS_ZONE_MAP = {
        "structure": ["jawline", "temple", "cheekbone", "nose_bridge"],
        "impression": ["outer_eye", "brow_tail", "under_eye", "brow_arch"],
        "maturity": ["cheekbone", "brow", "cheek_apple"],
        "intensity": ["eye_crease", "lip", "nose_tip"],
    }
    zone_bonus = {}
    for axis, delta in type_delta.items():
        if abs(delta) < 0.1:
            continue
        bonus = abs(delta) * 0.3
        for zone in AXIS_ZONE_MAP.get(axis, []):
            zone_bonus[zone] = zone_bonus.get(zone, 0) + bonus
    return zone_bonus


def _generate_expected_effects(
    primary_axis: str, type_label: str, style_tone: str
) -> list[str]:
    """deterministic 기대 효과 문장 생성"""
    axis_effect = {
        "structure": "얼굴 윤곽이 더 정돈돼 보입니다",
        "impression": "눈매와 인상이 더 선명해집니다",
        "maturity": "전체적인 분위기가 달라져 보입니다",
        "intensity": "이목구비의 존재감이 조정됩니다",
    }
    effects = [axis_effect.get(primary_axis, "전체 인상이 개선됩니다")]
    if type_label and style_tone:
        effects.append(f"{type_label} 타입의 {style_tone} 매력이 더 살아납니다")
    effects.append("적용 순서대로 하나씩 시도해보세요")
    return effects
```

### 2-5. build_overlay_plan()

```python
@dataclass
class OverlayZone:
    zone_name: str     # semantic name (landmark indices 없음)
    zone_type: str     # "shading" | "blush" | "highlight"
    color_hex: str
    opacity: float

def build_overlay_plan(
    action_spec: ActionSpec,
    face_features,  # FaceFeatures
) -> list[OverlayZone]:
    """
    recommended_actions → 시각적 오버레이 계획.
    zone name(semantic)까지만 확정. landmark 변환은 렌더러에서 source_model 확인 후 수행.
    """
    modifier = TYPE_MODIFIERS.get(action_spec.matched_type_id, {})
    intensity = modifier.get("shading_intensity", "medium")
    mult = {"minimal": 0.6, "light": 0.8, "medium": 1.0, "strong": 1.2}[intensity]

    # zone_type은 v0에서 시각 계열 분류 (렌더링 정밀 분류 아님)
    # "lip"은 임시로 "tint"로 처리. 향후 렌더러에서 별도 타입으로 분리 가능.
    ZONE_VISUAL = {
        "jawline":         ("shading",   "#8B6914", 0.25),
        "temple":          ("shading",   "#8B6914", 0.20),
        "cheekbone":       ("shading",   "#8B6914", 0.22),
        "mid_cheek":       ("blush",     "#D4707A", 0.28),
        "outer_cheek":     ("blush",     "#D4707A", 0.28),
        "cheek_apple":     ("blush",     "#E8909A", 0.30),
        "outer_eye":       ("shading",   "#9B7653", 0.20),
        "under_eye":       ("highlight", "#F5E6D0", 0.25),
        "nose_bridge":     ("highlight", "#F5E6D0", 0.30),
        "forehead_center": ("highlight", "#F5E6D0", 0.25),
        "brow_tail":       ("shading",   "#7B6544", 0.18),
        "eye_crease":      ("shading",   "#8B7355", 0.22),
        "lip":             ("tint",      "#C4616C", 0.30),
        "lip_center":      ("highlight", "#F0D0C8", 0.25),
        "lip_corner":      ("shading",   "#A0705A", 0.15),
        "nose_tip":        ("shading",   "#9B8060", 0.18),
        "brow":            ("shading",   "#6B5A3A", 0.20),
        "brow_arch":       ("shading",   "#6B5A3A", 0.18),
    }

    zones = []
    for action in action_spec.recommended_actions:
        visual = ZONE_VISUAL.get(action.zone)
        if not visual:
            continue
        ztype, color, opacity = visual
        zones.append(OverlayZone(
            zone_name=action.zone, zone_type=ztype,
            color_hex=color, opacity=min(opacity * mult, 0.5),
        ))
    return zones
```

**landmark 매핑은 렌더러에서 (이번 스프린트 후반 또는 다음):**
```python
def resolve_landmarks(zone_name: str, source_model: str) -> list[int]:
    """렌더링 직전에 source_model 확인 후 인덱스 변환"""
    if source_model == "insightface":
        return INSIGHTFACE_ZONE_LANDMARKS[zone_name]
    else:
        return MEDIAPIPE_ZONE_LANDMARKS[zone_name]
    # MediaPipe 468 → dlib 68 매핑 참고:
    # https://github.com/google-ai-edge/mediapipe/issues/4490
```

---

## Phase 3: Claude 입력 축소 + 출력 구조화

### 대상 파일: `sigak/llm.py`

### 3-1. Claude 입력

```python
def generate_report(action_spec: ActionSpec, user_context: dict) -> dict:
    prompt_payload = {
        "user_name": user_context["name"],
        "face_shape": user_context["face_shape"],
        "tier": user_context["tier"],
        "matched_type": action_spec.matched_type_label,
        "primary_change_direction": action_spec.primary_gap_axis,
        "recommended_actions": [
            {"순서": a.priority, "영역": a.zone, "방법": a.method, "효과": a.goal}
            for a in action_spec.recommended_actions
        ],
        "avoid_actions": [
            {"영역": a.zone, "이유": a.reason}
            for a in action_spec.avoid_actions
        ],
        "expected_effects": action_spec.expected_effects,
    }
    # Claude API 호출 후 parse_or_fallback() 적용
```

**안 넘기는 것:** raw FaceFeatures, 4축 좌표값, 타입 상세 delta, comparison dump, 클러스터 수치

### 3-2. Claude system prompt

```
역할: 당신은 스타일링 해설가입니다.
아래 이미 결정된 추천을 유저 친화적으로 설명하세요.

규칙:
- 추천 항목을 임의로 추가하거나 삭제하지 마세요
- action_tips는 recommended_actions의 순서를 그대로 유지하세요
- 축 점수나 delta 수치를 직접 언급하지 마세요
- "~할 수 있습니다" 대신 "~해보세요" 직접 안내
- 같은 내용을 다른 표현으로 반복하지 마세요
- 해요체를 사용하세요
- action_tips 각 항목의 zone 필드는 입력값을 그대로 복사하세요 (번역/의역 금지)

각 추천에 대해:
1. 왜 이 영역인지 한 줄 이유
2. 초보자용 적용 팁 1개 (구체적, 실행 가능)
3. 주의할 점 (avoid가 있으면)
```

### 3-3. Claude 출력 JSON 구조

```python
OUTPUT_FORMAT = """
반드시 아래 JSON 구조로만 응답하세요. 다른 텍스트를 포함하지 마세요.

{
  "summary": "전체 요약 2~3문장",
  "action_tips": [
    {
      "zone": "영역명 (입력 그대로)",
      "title": "추천 제목",
      "description": "설명 2~3문장",
      "beginner_tip": "초보자 팁 1문장"
    }
  ],
  "avoid_tip": "주의할 점 1~2문장 (없으면 null)",
  "closing": "마무리 한 줄"
}
"""
```

### 3-4. JSON parse fallback

```python
import json
import re

def parse_or_fallback(raw_text: str, action_spec: ActionSpec) -> dict:
    """Claude JSON 파싱. 실패 시 deterministic fallback."""
    # 1차: 직접 파싱
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2차: fenced code block 제거 후 재시도
    try:
        cleaned = re.sub(r'^```(?:json)?\s*', '', raw_text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    # 3차: deterministic fallback
    return _build_fallback_report(action_spec)


def _build_fallback_report(action_spec: ActionSpec) -> dict:
    """Claude 파싱 실패 시 Action Spec으로 직접 리포트 생성"""
    return {
        "summary": " ".join(action_spec.expected_effects[:2]),
        "action_tips": [
            {
                "zone": a.zone,
                "title": a.goal,
                "description": f"{a.zone} 영역에 {a.method}을 적용해보세요.",
                "beginner_tip": "거울을 보면서 소량부터 시작해보세요.",
            }
            for a in action_spec.recommended_actions
        ],
        "avoid_tip": (
            action_spec.avoid_actions[0].reason if action_spec.avoid_actions else None
        ),
        "closing": "한 가지씩 천천히 시도해보세요.",
    }
```

---

## Phase 4: run_analysis() 오케스트레이션

### 대상 파일: `sigak/main.py`

```python
async def run_analysis(image_bytes, interview_data, user_context):
    # Step 1: 얼굴 분석 (기존 유지)
    features = analyze_face(image_bytes)

    # Step 2: CLIP (mock 유지, 좌표에 영향 없음)
    clip_embedding = extract_clip(image_bytes, features.bbox) if not USE_MOCK_CLIP else None

    # Step 3: 좌표 산출 (Phase 1 변경 적용)
    coords = compute_coordinates(features.to_dict(), clip_embedding, projector)

    # Step 4: 타입 매칭 (기존 유지)
    similar_types = find_similar_types(clip_embedding, coords, user_context["gender"])

    # Step 5: 핀포인트 비교 (기존 유지)
    type_comparisons = compare_with_top_anchors(
        features.to_dict(), similar_types, user_context["gender"]
    )

    # Step 6: 클러스터 (기존 유지, 커버 페이지용)
    cluster = classify_user(coords, user_context["gender"])

    # Step 7: 인터뷰 해석 (축 정의 보정 완료)
    aspiration = interpret_interview(interview_data, user_context["gender"])

    # Step 7.5: 갭 계산
    gap = compute_gap(coords, aspiration["coordinates"])

    # Step 8: Action Spec 생성 ★
    top_type = similar_types[0] if similar_types else {
        "key": "fresh_face", "name_kr": "프레시 페이스",
        "similarity": 0.5, "mode": "coord",
    }
    action_spec = build_action_spec(
        face_features=features,
        current_coords=coords,
        matched_type=top_type,
        type_delta=type_comparisons[0]["axis_impacts"] if type_comparisons else {},
        gap=gap,
        interview_intent=aspiration.get("intent_tags"),
    )

    # Step 8.5: Overlay Plan 생성 ★
    overlay_plan = build_overlay_plan(action_spec, features)

    # Step 9: 리포트 생성 (축소된 입력) ★
    raw_report = generate_report(action_spec, {
        "name": user_context["name"],
        "face_shape": features.face_shape,
        "tier": user_context["tier"],
        "gender": user_context["gender"],
    })
    report = parse_or_fallback(raw_report, action_spec)

    # Step 9.5: Action Spec ↔ 리포트 일치 검증 ★
    assert len(report["action_tips"]) == len(action_spec.recommended_actions), \
        f"action count mismatch: {len(report['action_tips'])} != {len(action_spec.recommended_actions)}"
    for tip, rec in zip(report["action_tips"], action_spec.recommended_actions):
        assert tip["zone"] == rec.zone, f"zone mismatch: {tip['zone']} != {rec.zone}"

    # Step 10: 포매팅
    return format_report_for_frontend(
        report, features, coords, action_spec, overlay_plan, cluster
    )
```

---

## 범위 밖 (이번 스프린트에서 하지 않음)

- CLIP 모델 실제 활성화
- 인터뷰 해석 slot filling 전환
- 풀 파이프라인 로깅 시스템
- 남성 리포트 분기 (v0은 메이크업 관심 여성 타겟)
- 오버레이 프론트 인터랙티브화
- 타입별 modifier 15개 완성
- 클러스터 역할 재정의
- 변수명 정리
- 축 라벨 프론트 정식 변경
- overlay landmark indices 확정
- `_derive_zone_bonus` 방향 필터링 정교화

---

## 검증 기준

### Phase 1
- [ ] impression/intensity 값이 CLIP mock 상태와 무관하게 일관
- [ ] 같은 사진 → 같은 좌표 (deterministic)
- [ ] feature 미존재 시 KeyError 없이 fallback 작동
- [ ] interpret_interview가 새 축 정의로 aspiration 산출
- [ ] 상위 5개 타입 앵커 좌표 재계산 완료

### Phase 2
- [ ] `build_action_spec()`이 동일 입력 → 동일 출력
- [ ] 추천 action이 얼굴형/타입에 따라 실제로 달라짐
- [ ] type_delta가 zone 우선순위에 영향 (_debug_trace로 확인)
- [ ] 최소 2개 action 보장 (gap이 작아도)
- [ ] avoid_actions가 타입 modifier에 따라 적용

### Phase 3
- [ ] Claude 프롬프트 토큰 수 50% 이상 감소
- [ ] Claude 출력이 JSON 구조를 따름
- [ ] JSON 파싱 실패 시 fallback 리포트 정상 생성
- [ ] 리포트 내 동일 내용 반복 없음
- [ ] action_tips 개수 == recommended_actions 개수
- [ ] action_tips[i].zone == recommended_actions[i].zone

### 전체
- [ ] 기존 대비 리포트에 raw 수치 노출 없음
- [ ] 기존 대비 리포트 추천이 더 구체적 (zone + method 명시)
- [ ] 기존 대비 리포트 반복 텍스트 감소