# SIGAK 파이프라인 문제 진단서

> 작성: 2026-04-09
> 목적: 3축 마이그레이션 전, 현재 코드베이스의 모든 문제를 실무 관점에서 기록
> 대상 독자: 프로젝트 의사결정자

---

## A. 치명적 — 소비자에게 잘못된 정보를 보여주는 문제

### A-1. similarity.py 극성 반전 — 유형 매칭이 반대로 됨

**위치**: `sigak/pipeline/similarity.py:409-413`

```python
# 현재 코드 (잘못됨)
axis_labels = {
    "structure": {-1: "날카로운", 1: "부드러운"},   # ← coordinate.py와 반대!
    "impression": {-1: "따뜻한", 1: "쿨한"},        # ← 4축에 없는 "톤" 라벨
}
```

```python
# coordinate.py 정의 (정확함)
structure: soft(-1) ↔ sharp(+1)   # -1이 부드러운, +1이 날카로운
impression: soft(-1) ↔ sharp(+1)
```

**영향**: 이 axis_labels는 LLM 인터뷰 프롬프트에 넣는 앵커 설명에 사용됨.
LLM이 "부드러운 인상의 유형"이라고 읽으면 +1 방향으로 해석하지만,
실제 coordinate.py에서 +1은 "날카로운". **LLM이 추구미 좌표를 반대로 찍을 수 있음.**

**소비자 경험**: "부드러운 인상을 원해요" → LLM이 +1로 해석 → 실제로는 날카로운 방향 → 날카로운 유형 매칭 → **원하는 것과 반대 결과**.

---

### A-2. gap_summary에 옛 라벨 노출

**위치**: `sigak/pipeline/coordinate.py:293-298` → `report_formatter.py:845`

```python
# coordinate.py에서 생성 (옛 라벨)
"primary_shift_kr": "날카로운"   # ← AxisDefinition.positive_label_kr

# report_formatter.py에서 사용 (새 라벨 기대)
gap_summary = f"가장 큰 변화는 더 {primary_shift_kr} 방향으로..."
# → "더 날카로운 방향으로"
```

하지만 프론트 UI는 "각진"이라고 표시 (AXIS_LABELS 기반).
같은 리포트 안에서 **"날카로운"과 "각진"이 공존**. 소비자는 이게 같은 건지 다른 건지 모름.

**소비자 경험**: "요약에서는 '날카로운'이라고 했는데 아래 디테일에서는 '각진'? 뭐가 맞는 거지?"

---

### A-3. 라벨 소스 5곳 — 전부 다른 라벨

같은 축, 같은 방향인데 파일마다 다른 단어:

| 소스 파일 | structure -1 | structure +1 | impression -1 | impression +1 |
|-----------|---|---|---|---|
| coordinate.py AxisDef | 부드러운 | 날카로운 | 부드러운 | 선명한 |
| report_formatter AXIS_LABELS | 둥근 | 각진 | 온화한 | 선명한 |
| similarity.py axis_labels | **날카로운** (-1!) | **부드러운** (+1!) | **따뜻한** | **쿨한** |
| llm.py 프롬프트 | 둥글고 부드러운 | 날카롭고 선명한 | 부드럽고 온화한 | 시원하고 선명한 |
| 프론트 AXIS_META | 둥근 | 각진 | 온화한 | 선명한 |

**5곳이 전부 다른 단어를 사용하고, 1곳(similarity.py)은 극성까지 뒤집혀있음.**
이건 어떤 패치로도 해결 불가. 각 파일이 자체 dict를 가지고 있으므로 하나를 고치면 다른 곳과 또 불일치.

---

## B. 통계/AI 관점 — 의미 없거나 오도하는 지표

### B-1. 피처 커플링 — 축 독립성 위반

좌표계의 핵심 전제: **각 축은 독립적이어야 함**. 그래야 "라인은 부드러운데 존재감은 강한" 같은 조합이 가능.

현재 현실:

```
eye_width_ratio:
  maturity 축 → -0.30 가중치 (작으면 성숙)
  intensity 축 → +0.30 가중치 (크면 존재감)
  
lip_fullness:
  impression 축 → -0.15 가중치 (도톰→부드러운)
  intensity 축 → +0.25 가중치 (도톰→존재감)
```

**통계적 의미**: 눈이 큰 사람은 **자동으로** maturity↓ + intensity↑. 이 두 축이 역상관 강제됨. "큰 눈이면서 성숙한" 좌표가 물리적으로 나올 수 없음.

이건 좌표계가 아니라 **같은 피처를 다른 이름으로 두 번 측정**하는 것. 4축이라고 하지만 실질 자유도는 4보다 작음.

**소비자 경험**: "존재감이 강하다고 나왔는데 왜 자동으로 '프레시'한 걸로 나오죠? 전 성숙한 느낌인데..."

---

### B-2. brow_eye_distance — 영원히 N/A인 유령 피처

`coordinate.py` intensity 축에 `brow_eye_distance` weight 0.20 배정.
하지만 `face.py FaceFeatures`에 **이 필드가 없음**. 계산도 안 함.

```python
# coordinate.py
if _has_valid(features, "brow_eye_distance"):  # 항상 False
    ...  # 절대 실행 안 됨
```

**통계적 의미**: intensity 축은 설계상 4피처인데 실제로는 항상 3피처. weight 0.20이 나머지 3개로 재분배. 설계 의도와 실제 동작이 다름.

---

### B-3. face_length_ratio의 모호한 위치

```
4축 시스템: structure 축에 배치 (길수록 sharp)
feedback.md 3축 시스템: age 축에 배치 (길수록 mature)
```

동일 피처가 "날카로운 골격"과 "성숙한 인상" 중 어디에 속하는지 일관되지 않음. 사실 둘 다 일리가 있지만, **같은 파이프라인 안에서 의미가 바뀌면 해석 불가**.

---

### B-4. OBSERVED_RANGES 캘리브레이션 vs 실 유저 분포 괴리

SCUT-FBP5500 (중국 여성 주도) 2000장으로 캘리브레이션했지만:
- 타겟 유저: **한국 20대 여성**
- 데이터셋: 중국인 혼합, 연령대 넓음, 남성 포함 (AF=Asian Female만 사용했지만 표본 편향)

특히 `jaw_angle` 범위 (90.1~117.2)가 한국 20대 여성에 맞는지 검증 없음.
범위가 틀리면 정규화가 왜곡되고, 좌표 전체가 틀어짐.

**현실적 리스크**: 낮음 (현재 대안 없음, MVP에서는 수용 가능). 하지만 유저 50명+ 축적 시 재캘리브레이션 필요.

---

## C. 구조적 — 유지보수/확장 불가능한 설계

### C-1. 가중치가 Python 코드에 하드코딩

```python
# coordinate.py — 가중치 변경하려면 코드 배포 필요
components.append((val, 0.40))  # jaw_angle weight
components.append((val, 0.30))  # cheekbone weight
```

A/B 테스트, 가중치 튜닝, 사용자군별 조정이 불가능.
config 파일로 분리되어야 운영 단계에서 조정 가능.

---

### C-2. 3축 잔해가 4축 코드와 공존

`type_anchors.json` 안에:
```json
"axes_3d_definition": {          // ← 옛 3축 정의 (죽은 코드)
    "impression": {"0": "소프트", "1": "샤프"},
    "tone": {"0": "웜·내추럴", "1": "쿨·글램"},
    "mood": {"0": "프레시·큐트", "1": "성숙·시크"}
},
"axes_3d": [0.2, 0.2, 0.2],     // ← 옛 3축 좌표 (아무도 안 읽음)
"reference_coords": {"structure": -0.7, ...}  // ← 현재 4축 좌표 (실사용)
"axis_roles": {"structure": "negative", ...}  // ← 4축 기반
```

파이프라인 코드에서 `axes_3d`를 읽는 곳: **0건**.
하지만 JSON에 남아있으므로 새 개발자가 보면 "이 3축이 뭐지? 이걸 써야 하나?" 혼란.

---

### C-3. action_spec.py의 4축 규칙 테이블 — 3축 전환 시 대규모 재작성

```python
AXIS_ACTION_RULES = {
    "structure": { "increase": [...], "decrease": [...] },    # 6 rules
    "impression": { "increase": [...], "decrease": [...] },   # 6 rules
    "maturity": { "increase": [...], "decrease": [...] },     # 6 rules
    "intensity": { "increase": [...], "decrease": [...] },    # 6 rules
}  # 총 24개 규칙
```

```python
TYPE_MODIFIERS = {
    "type_1": { zone_boost, avoid_override, ... },
    "type_2": ...,
    "type_4": ...,
    "type_5": ...,
    "type_6": ...,
}  # 5개 타입만 정의, type_3/7/8 없음 → 공통 룰만 적용
```

3축 전환 시:
- 24개 규칙 → 18개로 재작성 (3축×2방향×3규칙)
- AXIS_ZONE_MAP 전면 재정의
- TYPE_MODIFIERS 8개 타입 전부 재정의
- zone 이름은 유지 가능하지만 어떤 축에 연결되는지 전부 바뀜

이 규칙들이 하드코딩이므로 축 변경 = 규칙 전량 재작성.

---

### C-4. LLM 인터뷰 해석이 좌표계에 강결합

```python
# llm.py
"4축 좌표계:
- structure [-1, +1]: soft ↔ sharp
- impression [-1, +1]: soft ↔ sharp
- maturity [-1, +1]: fresh ↔ mature
- intensity [-1, +1]: natural ↔ bold"
```

LLM이 이 프롬프트를 보고 유저 답변을 4축 좌표로 변환.
축이 바뀌면 프롬프트만 바꾸는 게 아니라 **LLM이 새 축 체계를 이해하는지 검증**해야 함.

특히 "volume: subtle ↔ bold"는 LLM에게 익숙하지 않은 개념. "이목구비 크기와 볼륨"을 LLM이 정확히 수치화할 수 있는지 테스트 필요.

---

## D. 프론트엔드 — UI가 백엔드 라벨을 신뢰하지 않는 구조

### D-1. 프론트에 자체 축 라벨이 3곳

```typescript
// gap-scatter-plot.tsx
const AXIS_META = {
  structure: { label: "라인", minLabel: "둥근", maxLabel: "각진" },
  ...
};

// gap-analysis.tsx  
const AXIS_LABELS = { structure: "라인", impression: "인상", ... };
const AXIS_END_LABELS = { structure: { low: "둥근", high: "각진" }, ... };
```

백엔드가 `label_low`, `label_high`, `axis_description` 등을 이미 내려보내는데,
프론트는 그걸 **무시하고 자체 const를 사용**. 백엔드에서 라벨을 바꿔도 프론트에서 안 바뀜.

---

### D-2. 2D 차트 동적 축 선택 — 볼 때마다 다른 차트

```typescript
function pickTopTwoAxes(current, aspiration) {
  // delta가 가장 큰 2축을 X, Y로 선택
}
```

같은 사람이라도 **추구미에 따라 차트의 X축과 Y축이 바뀜**. 
첫 리포트는 structure×maturity, 재진단은 impression×intensity. 
사분면 라벨도 달라지니 비교 불가.

**소비자 경험**: "지난번이랑 차트가 완전 달라보이는데 뭐가 바뀐 건지 모르겠어요."

---

### D-3. Coordinates 타입 — 프론트가 4축을 가정

```typescript
interface Coordinates {
  structure: number;
  impression: number;
  maturity: number;
  intensity: number;
}
```

이게 gap-scatter-plot.tsx, gap-analysis.tsx 양쪽에 하드코딩. 
3축 전환 시 TypeScript 컴파일 에러로 즉시 감지되긴 하지만, 
**인터페이스가 백엔드 스키마를 수동으로 미러링**하는 구조 자체가 취약.

---

## E. 가장 큰 파이프라인 문제 (종합)

### 단일 최대 문제: "축 정의의 Single Source of Truth가 없다"

coordinate.py에 AxisDefinition이 있지만, 그걸 참조하는 파일이 **단 1곳** (coordinate.py 자체).
나머지 파일은 전부 자체 dict를 만들어서 사용.

```
coordinate.py  →  AxisDefinition (부드러운/날카로운)     ← 계산 기준
similarity.py  →  axis_labels (날카로운/부드러운, 반전!)  ← LLM 프롬프트
report_formatter.py → AXIS_LABELS (둥근/각진)            ← 리포트 텍스트
llm.py         →  인라인 문자열 (soft/sharp)             ← LLM 프롬프트
프론트          →  AXIS_META, AXIS_END_LABELS, AXIS_LABELS ← UI 렌더링
```

이 5곳이 동기화되어야 하는데, 동기화 메커니즘이 없음. 한 곳을 고치면 나머지는 옛 라벨.
극성 반전(similarity.py)은 이 문제의 가장 심각한 증상.

### 해결 방향

1. 축 정의를 **단일 파일** (coordinate.py 또는 config YAML)에만 두기
2. 다른 모든 파일은 `from coordinate import get_axis_labels` 같은 함수로만 접근
3. 프론트는 백엔드 JSON에서 내려온 라벨만 사용, 자체 const 삭제
4. 축 이름/라벨 변경 시 **한 파일만 수정하면 전체 반영**

이것이 feedback.md 3축 마이그레이션의 핵심 설계 원칙이기도 함.

---

## F. 리스크 대비 우선순위

| 등급 | 문제 | 소비자 영향 | 수정 복잡도 |
|------|------|------------|------------|
| 🔴 치명 | A-1 극성 반전 | 유형 매칭 반대 | 1줄 수정이지만 근본 해결은 SSOT |
| 🔴 치명 | A-3 라벨 5곳 불일치 | 리포트 내 용어 혼란 | SSOT 전환 필요 |
| 🟠 높음 | B-1 피처 커플링 | 축 독립성 위반 → 부정확한 진단 | 3축 전환으로 해결 |
| 🟠 높음 | D-2 동적 축 선택 | 비교 불가능한 차트 | 고정축 전환으로 해결 |
| 🟡 중간 | A-2 gap_summary 옛 라벨 | 용어 혼란 | coordinate.py 라벨 통일 |
| 🟡 중간 | C-1 가중치 하드코딩 | 튜닝 불가 | config 분리 |
| 🟡 중간 | C-3 action_spec 24규칙 | 3축 전환 시 대규모 재작성 | Phase 3에서 처리 |
| 🟢 낮음 | B-2 유령 피처 | 축 정확도 미세 영향 | 추가 or 제거 |
| 🟢 낮음 | B-4 캘리브레이션 편향 | 현재 대안 없음 | 유저 데이터 축적 후 |
| 🟢 낮음 | C-2 3축 잔해 | 개발자 혼란 | 삭제 |

---

*이 문서의 모든 문제는 feedback.md의 3축 마이그레이션을 통해 해결됩니다.*
*마이그레이션 실행 전에 이 문서를 기준으로 "모든 항목이 해결되었는지" 최종 검증합니다.*
