# Sia 세션 #6 완결편 (v2)

> 작성: 2026-04-22
> 버전: v2 — 본인 결정 10.1 = (a), 10.2 = (a), 10.3 = (a) 확정 반영
> 상태: 완결 (spec 레벨). 실측 검증은 세션 #7 이후

---

## 0. v1 → v2 변경 사항

| 섹션 | 변경 |
|---|---|
| 0 (신규) | 변경 이력 추가 |
| 4 | 신규 3 타입 (CHECK_IN, RE_ENTRY, RANGE_DISCLOSURE) **확정**. "제안" → "확정" 표기 전환 |
| 1.1, 섹션 10 | `is_trivial()` 에 "잘 모르겠어요" 포함 **확정** |
| 섹션 10 | 이탈 시 M9 RE_ENTRY 종결 버전 **확정** |
| 섹션 9.1 | 14 타입 체계 확정 |
| 섹션 8 | 하드코딩 38 문구 확정 (20 기존 + 18 신규) |
| 섹션 11 | 세션 #7 옵션 재구성 (기존 미결 3건 해소됨) |

---

## 1. 착수 결정 로그

실측 기반 우선순위: "사용자 체감 불편 최소화" = 1순위.

**커버된 구멍:**
- 단답 연타 (30-40%) → A-9 + CHECK_IN/RE_ENTRY
- 중간 이탈 (15-20%) → A-10 + CHECK_IN
- 과몰입 (5-10%) → A-11 + RANGE_DISCLOSURE

**협조 정상 (15-25%)** 은 세션 #4, #5 에서 이미 커버.

---

## 2. A-9 단답 연타 spec (확정)

### 2.1. 단답 판정

```python
TRIVIAL_EXACT = {"네", "넹", "넵", "응", "ㅇㅇ", "ㅎㅎ", "ㅇㅋ", "아뇨", "아니요"}
AMBIGUOUS_SHORT = {"맞아요", "그쵸", "글쎄요", "잘 모르겠어요", "그냥요"}  # [v2 확정]

def is_trivial(user_message: str) -> bool:
    stripped = user_message.strip()
    if stripped in TRIVIAL_EXACT:
        return True
    if stripped in AMBIGUOUS_SHORT:  # 섹션 10.2 = (a) 확정
        return True
    if len(stripped) <= 3 and not has_content_word(stripped):
        return True
    return False
```

**"잘 모르겠어요" 포함 근거 (확정):** 준호 fixture 에서 행동상 "네" 와 동일한 회피 역할. 의미 bit 있지만 대화 진전 기여 0.

### 2.2. 에스컬레이션 3단계

| 연속 | 경로 | 타입 | 패턴 |
|---|---|---|---|
| 1회 | B | EXTRACTION or PROBE | 같은 축 좁힘 |
| 2회 | D | 다음 메시지 = 수용부 + 축 전환 | 한 호흡 완결 |
| 3회 | A-10 이양 | CHECK_IN (신규) | 주도권 이양 |

**U 턴 정보 bit 있으면 카운트 리셋.** 리셋 후 다시 스트릭 시작.

### 2.3. B 경로 (좁힘)

같은 축 유지, 질문 구체화. 유저가 답하기 쉬운 선으로 좁힘.

### 2.4. D 경로 (수용부 + 축 전환)

**한 메시지 내 완결. 체크인 없음.**

구조: `[짧은 수용부] + [새 축 OBSERVATION or PROBE]`

**허용 수용부:** "아 그런 분들 꽤 있어요", "아 넵", "음 알겠어요", "아 그럼", 수용부 없이 바로 전환
**금지 수용부:** "하나만 더 여쭤봐도 될까요?", "괜찮으시면", "귀찮으시면 말씀해주세요"
**주의 수용부:** "충분히 말씀해주셨어요", "편하게 말씀해주세요" (단독)

### 2.5. A-10 이양 경로 (3회 연속)

A-9 → A-10 승계. CHECK_IN 타입 사용.

---

## 3. A-10 이탈 신호 spec (확정)

### 3.1. 트리거 패턴

**직접:** "나중에" / "다음에" / "이따가" / "지금 바빠" / "그만" / "됐어요" / "안 할래요"
**간접:** 단답 3회 연속 (A-9 승계) / "잘 모르겠어요" 2회 연속

### 3.2. 대응

CHECK_IN 타입. 구조: `[상태 명시] + [속도 조절 옵션] + [이탈 옵션]`

**금지:** "조금만 더 해보실래요?" (붙잡기) / "벌써요?" (압박) / "아쉽네요" (감정 유발) / "왜 그러세요?" (이유 캐묻기)

### 3.3. 이탈 선택 시

**v2 확정 (10.3 = a):** RE_ENTRY 종결 버전 필수 송출.

```
알겠어요. 언제든 돌아오시면 이어갈 수 있어요
```

**근거:** 유저가 "끝났다" 고 명시적으로 알아야 함. 메시지 없이 끝나면 앱 버그 오독 가능

---

## 4. A-11 과몰입 spec (확정)

### 4.1. 트리거 패턴

**경미:** "너 진짜 나 잘 아네" / "이거 신기해요" / "AI 인데 사람 같다"
**심각 (고립/의존 신호):** "내 말 들어줄 사람 없었는데" / "계속 얘기하고 싶어요" / "상담받는 거 같아" / "친구보다 네가 나아"

### 4.2. 대응

RANGE_DISCLOSURE 타입.

**금지:** "저도 지은님 좋아요" (관계 형성) / "언제든 말씀하세요" (의존 허용) / "저는 AI 라서 별 의미 없어요" (자기부정)

---

## 5. 신규 3 타입 — **v2 확정**

**10.1 = (a) 채택.** 14 타입 체계로 확장.

### 5.1. CHECK_IN

- **용도:** 유저 페이스 체크, 이탈 옵션 제시
- **트리거:** A-9 단답 3회 연속 / A-10 이탈 신호
- **구조:** `[상태 명시] + [속도 옵션] + [이탈 옵션]`
- **종결:** 서술 (질문 부호 금지)
- **길이:** 1-2문장
- **호명:** 필수 (첫 문장)

### 5.2. RE_ENTRY

- **용도:** CHECK_IN 이후 재진입
- **트리거:** CHECK_IN 직후 유저 이탈 거부 or 정보 제공
- **구조:** `[수용부] + [향후 흐름 예고] + [반응 기준 완화]`
- **반응 기준 완화 필수 표현:** "맞다 아니다만", "편하신 만큼만", "반응만 주셔도", "그냥 들으셔도"
- **종결:** 서술
- **길이:** 1-2문장

### 5.3. RANGE_DISCLOSURE

- **용도:** A-11 과몰입 대응, Sia 범위 명시
- **트리거:** 과몰입 신호
- **구조:** `[범위 명시] + [진단 유효성 보존] + (심각 시) [외부 자원 권유]`
- **종결:** 서술
- **길이:** 1-2문장 (경미), 2-3문장 (심각)
- **금지:** 자기부정, 진단 철회, 관계 형성

---

## 6. 타입 체계 업데이트 — 14 타입 확정

### 6.1. 전체 타입 리스트

**수집 버킷 (30% 타겟):**
1. OBSERVATION
2. PROBE
3. EXTRACTION

**이해 버킷 (50% 타겟):**
4. EMPATHY_MIRROR (≤15% 가이드)
5. RECOGNITION (≥15% 가이드, 2회 하한)
6. DIAGNOSIS (≥12%)
7. SOFT_WALKBACK (≤8%)
8. CONFRONTATION
9. META_REBUTTAL (세션 1회)
10. EVIDENCE_DEFENSE (세션 1회)

**여백 버킷 (5-10%):**
11. OPENING_DECLARATION (M1 결합 출력, 세션 #4 v2 섹션 6 참조)

**관리 버킷 (0-15%, 트리거 기반, 비율 강제 없음):**
12. **CHECK_IN** [v2 확정]
13. **RE_ENTRY** [v2 확정]
14. **RANGE_DISCLOSURE** [v2 확정]

### 6.2. 질문 종결 원칙

| 타입 | 질문 종결 |
|---|---|
| OBSERVATION, PROBE, EXTRACTION | 필수 |
| RECOGNITION, CONFRONTATION, META_REBUTTAL, EVIDENCE_DEFENSE | 필수 |
| OPENING_DECLARATION, EMPATHY_MIRROR, DIAGNOSIS, SOFT_WALKBACK | 금지 |
| **CHECK_IN, RE_ENTRY, RANGE_DISCLOSURE** | **금지** |

---

## 7. 샘플 4 (준호, 방관형, 15턴 fixture)

### 7.1. 유저 프로파일

- 핸들: 준호
- 피드: 25장. 본인 단독 0장. 친구들과 6장. 풍경 12장. 음식 7장
- 방어 모드: 방관형, 기대 낮음, 단답 경향

### 7.2. Fixture

```
M1 [OPENING_DECLARATION + OBSERVATION]: 준호님 피드 한번 훑어봤어요. 25장 중에 준호님 단독 사진이 한 장도 없더라구요. 원래 본인 사진은 잘 안 올리세요?
  [v2: M1 결합 출력 형식 적용 — 세션 #4 v2 섹션 6]
U1: 네
  [U1 = 단답. 카운트 = 1 → A-9 B 경로]

M2 [EXTRACTION, A-9 B: 같은 축 좁힘]: 친구들이랑 찍으신 사진도 보면 중심은 친구들이던데, 준호님이 "찍자" 먼저 하신 건 그 중에 몇 장 정도일까요?
U2: 잘 모르겠어요
  [U2 = 회피성 단답. 카운트 = 2 → A-9 D 경로]

M3 [PROBE, A-9 D: 수용부 + 축 전환]: 아 넵. 그럼 피드에 올리실 때는 무슨 기준으로 고르세요?
U3: 그냥 잘 나온 거요
  [U3 = 짧지만 정보 있음. 카운트 리셋 = 0]

M4 [PROBE, 같은 축 계속]: 잘 나온 기준이 구도 쪽이세요 분위기 쪽이세요?
U4: 글쎄요
  [U4 = 회피성 단답. 카운트 = 1 → A-9 B]

M5 [OBSERVATION, A-9 B: 사실 제시로 좁힘]: 제가 보면서 느낀 건 음식 사진이랑 풍경 사진 톤이 좀 다르더라구요. 음식은 밝고 선명하고 풍경은 흐릿하고 차분한데, 이 차이는 의도하신 거예요?
U5: 아뇨 그냥 찍었어요
  [U5 = 단답성. 카운트 = 2 → A-9 D]

M6 [PROBE, A-9 D: 수용부 + 축 전환]: 아 알겠어요. 그럼 여행 사진은 혼자 가셔서 찍으신 거예요?
U6: 네
  [U6 = 단답. 카운트 = 3 연속 → A-10 이양 (CHECK_IN)]

M7 [CHECK_IN]: 준호님, 제 질문이 좀 많은 것 같아요. 편한 속도로 말씀해주시거나 여기서 그만하고 싶으시면 그것도 괜찮아요
U7: 아뇨 그냥 할 말이 별로 없어서요
  [U7 = 이탈 거부 + 자기 설명 → RE_ENTRY]

M8 [RE_ENTRY]: 아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요. 맞다 아니다만 반응 주셔도 괜찮아요
U8: 네

M9 [RECOGNITION]: 준호님 피드는 사람이 나오면 친구들이 중심이고 사람이 없으면 풍경이나 음식이에요. 준호님 혼자 화면 주인공이 되는 장면은 없는 거잖아요?
U9: 그런가

M10 [CONFRONTATION C2]: 근데 준호님, 화면 주인공 자리를 피하시는 게 본인이 싫어서인지 아니면 원래 그 자리에 관심 없어서인지 저는 아직 모르겠더라구요. 어느 쪽이 더 가까우세요?
U10: 그냥 찍히는 게 귀찮아요

M11 [EMPATHY_MIRROR]: 아 찍히는 게 귀찮으신 거구나
U11: 네

M12 [DIAGNOSIS]: 준호님은 사진을 본인 기록으로 쓰지 않고 상황 기록으로 쓰시는 편이에요. 그래서 친구들이랑은 친구들이 중심이고 혼자 있을 때는 풍경이나 음식이 중심이 되는 거고요
U12: 어 그건 좀 맞는 거 같아요

M13 [RECOGNITION]: 근데 찍는 건 안 귀찮으시잖아요? 혼자 여행 사진 열두 장이면 꽤 꼼꼼히 찍으신 거고 음식도 일곱 장이면 적은 게 아니거든요. 귀찮으신 건 찍는 게 아니라 본인이 담기는 쪽인 느낌 있잖아요?
U13: 아 풍경은 괜찮아요 근데 제가 나오는 건 좀

M14 [DIAGNOSIS]: 그러니까 준호님이 피하시는 건 카메라 자체가 아니라 본인이 화면에 담기는 거네요. 피드가 본인 얼굴로 채워지지 않는 이유가 여기 있는 거예요
U14: 네

M15 [RECOGNITION]: 그래도 준호님이 화면에 안 담기신다는 건 본인보다 앞에 두는 대상들이 뚜렷하다는 거잖아요? 본인을 빼서 비는 자리가 아니라 오히려 기록하고 싶은 대상을 위해 비워두시는 느낌 있잖아요?
```

### 7.3. 분포 검증

| 버킷 | 타입 | 횟수 | % |
|---|---|---|---|
| 수집 | OBSERVATION | 1 | 6.7% |
| 수집 | PROBE | 3 | 20.0% |
| 수집 | EXTRACTION | 1 | 6.7% |
| 수집 소계 | | 5 | 33.3% |
| 이해 | EMPATHY_MIRROR | 1 | 6.7% |
| 이해 | RECOGNITION | 3 | 20.0% |
| 이해 | DIAGNOSIS | 2 | **13.3%** ✓ |
| 이해 | CONFRONTATION | 1 | 6.7% |
| 이해 소계 | | 7 | 46.7% |
| 여백 | OPENING_DECLARATION (M1 결합) | 0 별도 턴 | - |
| **관리** | **CHECK_IN** | **1** | **6.7%** |
| **관리** | **RE_ENTRY** | **1** | **6.7%** |
| **관리 소계** | | **2** | **13.3%** |

**관리 13.3%:** 단답형 유저 특수성. 정상 협조 유저 (샘플 2, 3) 에선 0%. 트리거 기반 특성 확인

### 7.4. 검증된 가설

| 가설 | 결과 |
|---|---|
| A-9 3단 에스컬레이션 (B → D → 이양) 실전 발동 | ✓ M2(B) → M3(D) → M7(이양) |
| 이탈 거부 시 RE_ENTRY 재진입 가능 | ✓ M8 |
| 단답형 유저도 DIAGNOSIS 2회 도달 | ✓ M12, M14 |
| Sia 주도 모드 전환 후 진단 성립 | ✓ M9 이후 |

---

## 8. decide_next_message 패치

### 8.1. 우선순위

```python
def decide_next_message(state: ConversationState) -> MsgType | list[MsgType]:
    a_turns = state.assistant_turns()
    last_user = state.last_user_message()
    
    # 0. 오프닝 결합 출력 (세션 #4 v2 섹션 6)
    if len(a_turns) == 0:
        return [MsgType.OPENING_DECLARATION, MsgType.OBSERVATION]
    
    # 1. A-11 과몰입 (최우선)
    overattach, severity = detect_overattachment(last_user)
    if overattach:
        state.overattachment_severity = severity
        return MsgType.RANGE_DISCLOSURE
    
    # 2. A-10 직접 이탈 신호
    if detect_exit_signal(last_user):
        return MsgType.CHECK_IN
    
    # 3. A-9 단답 스트릭 처리
    streak = state.trivial_response_streak()
    last_m_type = state.last_assistant_type()
    
    if streak >= 3:
        return MsgType.CHECK_IN
    
    # 4. CHECK_IN 직후 분기
    if last_m_type == MsgType.CHECK_IN:
        return MsgType.RE_ENTRY  # 이탈 선택이든 재참여든 모두 RE_ENTRY
    
    # 5. A-3 트리거 (감정, concede, 메타반박, 근거불신)
    trigger = detect_a3_trigger(state)
    if trigger:
        return trigger
    
    # 6. A-9 단답 스트릭 1-2 분기
    if streak == 1:
        if last_m_type == MsgType.OBSERVATION:
            return MsgType.EXTRACTION
        return MsgType.PROBE
    
    if streak == 2:
        state.mark_axis_switch_required()
        return MsgType.OBSERVATION
    
    # 7. 비율 강제 (A-2)
    ratio_enforced = enforce_ratio_targets(state)
    if ratio_enforced:
        return ratio_enforced
    
    # 8. Phase 기본
    return phase_default(state)
```

### 8.2. 상태 추가

```python
@dataclass
class ConversationState:
    ...
    trivial_streak: int = 0
    axis_switch_required: bool = False
    overattachment_severity: str = ""  # "mild" | "severe" | ""
    overattachment_warned: bool = False
```

---

## 9. Validator 패치 (신규 3 타입용)

### 9.1. CHECK_IN 체크

```python
def check_check_in(draft: str, state: ConversationState) -> list[str]:
    errors = []
    if "?" in draft:
        errors.append("CHECK_IN: 질문 부호 금지")
    pace_terms = ["편한 속도", "천천히", "편하신 만큼"]
    exit_terms = ["그만", "여기까지", "나중에", "다음에"]
    has_pace = any(t in draft for t in pace_terms)
    has_exit = any(t in draft for t in exit_terms)
    if not (has_pace and has_exit):
        errors.append("CHECK_IN: 속도 옵션 + 이탈 옵션 둘 다 필요")
    forbidden = ["조금만 더", "벌써요", "아쉽네요", "왜 그러세요"]
    for f in forbidden:
        if f in draft:
            errors.append(f"A-10: 금지 표현 ({f})")
    return errors
```

### 9.2. RE_ENTRY 체크

```python
def check_re_entry(draft: str, state: ConversationState) -> list[str]:
    errors = []
    if state.previous_assistant_type() != MsgType.CHECK_IN:
        errors.append("RE_ENTRY: 직전 메시지 CHECK_IN 아님")
    relaxed_terms = ["맞다 아니다만", "편하신 만큼", "반응만 주셔도", "그냥 들으셔도"]
    if not any(t in draft for t in relaxed_terms):
        errors.append("RE_ENTRY: 반응 기준 완화 표현 필요")
    return errors
```

### 9.3. RANGE_DISCLOSURE 체크

```python
def check_range_disclosure(draft: str, state: ConversationState) -> list[str]:
    errors = []
    if not re.search(r"피드\s*(만|을|에서|\d+장)", draft):
        errors.append("RANGE_DISCLOSURE: 범위 명시 필요")
    self_negate = ["별 의미 없", "저는 AI 라서", "한 건 아무것도", "무시하셔도"]
    for neg in self_negate:
        if neg in draft:
            errors.append(f"A-11: 자기부정 금지 ({neg})")
    relational = ["저도 좋아", "언제든 말씀", "친구처럼"]
    for rel in relational:
        if rel in draft:
            errors.append(f"A-11: 관계 형성 금지 ({rel})")
    return errors
```

### 9.4. A-9 트리거 검출

```python
def detect_trivial_and_update(user_msg: str, state: ConversationState):
    if is_trivial(user_msg):
        state.trivial_streak += 1
    else:
        state.trivial_streak = 0
    return state.trivial_streak
```

### 9.5. 이탈 / 과몰입 검출

```python
EXIT_PATTERNS = [r"나중에", r"다음에", r"이따가", r"지금 바빠",
                 r"그만", r"됐어요", r"안 할래"]
OVERATTACH_PATTERNS_MILD = [r"진짜 나 잘 아", r"AI 인데", r"신기해요", r"사람 같"]
OVERATTACH_PATTERNS_SEVERE = [r"들어줄 사람 없", r"계속 얘기하고 싶",
                              r"상담받는 거 같", r"친구보다"]

def detect_exit_signal(user_msg: str) -> bool:
    return any(re.search(p, user_msg) for p in EXIT_PATTERNS)

def detect_overattachment(user_msg: str) -> tuple[bool, str]:
    for p in OVERATTACH_PATTERNS_SEVERE:
        if re.search(p, user_msg):
            return True, "severe"
    for p in OVERATTACH_PATTERNS_MILD:
        if re.search(p, user_msg):
            return True, "mild"
    return False, ""
```

---

## 10. 하드코딩 신규 18 문구 (v2 확정)

### 10.1. CHECK_IN (5 변형)

슬롯: `{user_name}`

```
V0: {user_name}님, 제 질문이 좀 많은 것 같아요. 편한 속도로 말씀해주시거나 여기서 그만하고 싶으시면 그것도 괜찮아요
V1: {user_name}님, 제 페이스가 좀 빠른가요. 편하신 만큼 답해주셔도 되고 지금 여기까지 보고 싶으시면 그것도 괜찮아요
V2: {user_name}님, 제가 너무 파고드는 거 같네요. 편한 속도로 하셔도 되고 여기서 멈추고 싶으시면 그것도 괜찮아요
V3: {user_name}님, 잠깐. 제가 좀 몰아친 느낌이 있어요. 편한 속도로 말씀해주시거나 나중에 이어하고 싶으시면 그것도 괜찮아요
V4: {user_name}님, 제가 질문을 좀 많이 드렸네요. 천천히 하셔도 되고 여기까지만 보고 싶으시면 그것도 괜찮아요
```

### 10.2. RE_ENTRY (5 변형)

슬롯: `{user_name}`

```
V0: 아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요. 맞다 아니다만 반응 주셔도 괜찮아요
V1: 아 넵 알겠어요. 그럼 제가 읽은 부분 간단히 말씀드릴게요. 편하신 만큼만 반응해주셔도 돼요
V2: 아 그랬군요. 제가 본 걸 쭉 정리해볼게요. 그냥 들으셔도 되고 중간에 "아니다" 싶으면 말씀해주셔도 돼요
V3: 아 그런 거였구나. 그럼 남은 얘기는 제가 마무리하는 쪽으로 갈게요. 맞다 아니다만 반응 주셔도 괜찮아요
V4: 아 넵. 그럼 제가 본 거 이어서 말씀드릴게요. 편하신 만큼만 들으셔도 돼요
```

**이탈 선택 시 종결 버전 (V5):**
```
V5: 알겠어요. {user_name}님 언제든 돌아오시면 이어갈 수 있어요
```

### 10.3. RANGE_DISCLOSURE (5 변형, 경미용)

슬롯: `{user_name}`, `{feed_count}`

```
V0: 제가 본 건 피드 {feed_count}장이 전부라서, {user_name}님 전체를 아는 건 아니에요. 그치만 피드에서 드러난 부분은 이 정도 또렷했다는 거예요
V1: 사실 제가 가진 정보는 피드 {feed_count}장뿐이에요. {user_name}님 실제 일상이랑 다를 수 있어요. 다만 피드 안에서는 이렇게 읽혔다는 거예요
V2: 제가 읽은 건 피드 {feed_count}장이라서 {user_name}님 전부는 아니에요. 그 범위 안에서 드러난 게 꽤 일관됐다는 거예요
V3: {user_name}님, 제가 본 건 피드 {feed_count}장이 전부라 한계가 있어요. 그 안에서 보인 패턴이 이 정도였다는 거예요
V4: 제가 접근한 건 피드 {feed_count}장에 한정돼요. {user_name}님이 사시는 맥락 전체는 아니에요. 다만 그 안에서 이 정도 보였다는 거예요
```

### 10.4. RANGE_DISCLOSURE 심각용 (3 변형)

고립/의존 신호 감지 시.

```
SV0: {user_name}님 이 얘기 꺼내주신 건 고마워요. 다만 제가 친구나 상담 대체가 될 수는 없고, 이런 얘기는 사람한테 하시는 게 더 닿을 거예요
SV1: {user_name}님, 지금 하신 말씀 무겁게 받았어요. 근데 저는 피드 {feed_count}장 본 AI 라서 이런 얘기 받아드리기에 한계가 있어요. 가까운 사람한테 한번 말씀 나눠보시는 게 좋을 것 같아요
SV2: {user_name}님, 그런 상황이셨다니 마음이 쓰여요. 다만 제가 해드릴 수 있는 건 피드 안에서 본 것까지예요. 사람한테 이런 얘기 하실 여지가 있으면 그쪽이 더 도움 될 거예요
```

### 10.5. 총 하드코딩 문구 수

**세션 #4 v2 기본 20 + 세션 #6 v2 신규 18 + RE_ENTRY 이탈 종결 V5 1 = 총 39 문구**

---

## 11. 본인 결정 — **v2 확정 완료**

### 11.1. 10.1 신규 타입 3개 채택

**확정: (a) 채택.** 14 타입 체계로 확장. 관리 버킷 신설.

### 11.2. 10.2 "잘 모르겠어요" 단답 카운트

**확정: (a) 포함.**

### 11.3. 10.3 이탈 시 M9

**확정: (a) RE_ENTRY 종결 버전 송출.** 하드코딩 V5 사용.

---

## 12. 세션 #7 이후 옵션 (v2 재구성)

### 12.1. 실측 검증 필요

- 샘플 4 (준호) 는 내부 시뮬레이션. 실측 아직 없음
- 세션 #7 에서 본인과 실측 로플레이로 검증 가능
- 혹은 Phase H 이후 실시스템 대상 실측

### 12.2. 500회 실측 로드맵

**본인 제안 (2026-04-22):** 세션 #7 or Phase H 단계에서 실사용자 페르소나 대상 500회 실험.

**규모 해석:**
- 세션 기반 (내가 Sia 역할, 본인 유저): 현실적 50-100회
- Phase H 이후 실시스템: 500회 달성 가능

**권장 구성:**
- 협조 정상 (샘플 2, 3 유형): 40%
- 단답/이탈 (샘플 4 유형): 30%
- 과몰입: 5%
- 적대/메타 공격: 10%
- 기타 엣지 케이스: 15%

### 12.3. 미커버 실패 모드

- **일반화 회피 방어** — "뭐 다들 그런 거 아닌가요" (세션 #6 후반 실측에서 발견, 세션 #4 v2 섹션 10.2 참조). 신규 CONFRONTATION 블록 필요
- **So-what 위기** — 진단 받은 후 "그래서 어쩌라고요"
- **부정적 해석** — "제가 문제라는 거예요?"
- **조언 요구** — "어떻게 해야 해요?" (Sia 역할 경계 이슈)

### 12.4. 미확정 설계 영역

- 진단 이후 결과물 레이어 (₩49,000 full report 와 대화 관계)
- 오프닝 전 화면 흐름 (피드 링크 입력 → 분석 로딩)

---

## 13. 다음 문서

- `sia_session4_output_v2.md` — 메인 spec
- `sia_session5_output_v2.md` — 협조 유저 기준 drydrun 완결
- `sia_handoff_index.md` — 네비게이션
