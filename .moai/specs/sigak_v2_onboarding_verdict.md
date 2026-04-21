# SIGAK v2 Onboarding + Verdict 설계 Final (Approved)

> Status: **APPROVED — Priority 1 착수 근거 문서**
> Author: Claude Code
> Date: 2026-04-21
> Approved: 2026-04-21
> Scope: Onboarding 1회 + Sia 대화 + IG 피드 수집 + Verdict 2.0 (preview/full) + PI CTA
> Formal SPEC: `.moai/specs/SPEC-ONBOARDING-V2/` (EARS 형식)

---

## 0. 확정 컨텍스트 (본인 지시 그대로)

### 프로덕트 3층 구조
| 층 | 빈도 | 가격 | 비용 | 핵심 |
|---|---|---|---|---|
| **Onboarding** | 1회 | 무료 | 0 | 성별 + 생년월일 + IG 핸들 → IG 피드 수집 → Sia 대화 → `user_profile` 영속 |
| **Verdict** | 반복 | ₩1,000 | 10토큰 | 사진 3~10장 + profile + 트렌드 → preview 무료 / full 결제 |
| **PI** | 1회 영속 | ₩5,000 | 50토큰 | 정면 사진 1장 + profile → 3축 진단 9섹션 |
| **Monthly** | 월 1회 | ₩3,000 | 30토큰 | 변화 시계열 |

### Sia 페르소나 (요약 — 상세는 §4)
- 이름: **Sia**, AI 미감 컨설턴트
- 관계: 지인형 비서 (위/아래 아님)
- 말투: 다정한 해요체, 2~3문장/턴, 문장당 30자 이내
- 관찰 → em-dash(—) → 질문 구조
- 시적 비유 금지, 평가 X / 관찰 O

### 호칭 폴백 체인 (확정판, 본인 지시 2026-04-21 보정)
```
1순위: 카톡 OAuth name → "[NAME]님"
2순위: name 한글 없음 → Sia 첫 턴에 "어떻게 불러드릴까요?" 질문
3순위: 애플 로그인으로 name 없음 → "님" 생략 + 존댓말만 유지
```

**중요**: IG 핸들은 **데이터 수집 용도만**. 호칭에 사용하지 않음
(기존 draft 의 4순위 "IG 핸들 [handle]님" 은 제거됨).

### 대화 엔진 (확정)
- Hybrid (a3): free-form + 빠진 필드 tree fallback
- Extraction: 종료 후 일괄 (ii)
- 대화 LLM: **Claude Haiku 4.5** (턴당 응답)
- Extraction LLM: **Claude Sonnet 4.6** (로그 → structured)
- 세션: **stateful server-side** (Redis + DB)
- 턴 제한 없음

### 수집 필드 15개
| 출처 | 필드 |
|---|---|
| Onboarding structured (3) | `gender`, `birth_date`, `ig_handle` |
| IG 자동 추출 (4) | `current_style_mood`, `style_trajectory`, `feed_highlights`, `profile_basics` |
| 대화 추출 (8) | `desired_image`, `reference_style`, `current_concerns`, `self_perception`, `lifestyle_context`, `height`, `weight`, `shoulder_width` |
| **삭제 (MVP 제외)** | ~~neck_length~~, ~~makeup_level~~, ~~face_concerns~~, ~~style_image_keywords~~ |

### 사진 업로드 타이밍
- 대화 중 ❌ 사진 요청 안 함
- Verdict 결제 시 사진 3~10장 업로드
- PI 결제 시 정면 사진 1장 업로드

---

## 1. 기존 자산 Audit

### 1-1. Questionnaire 컴포넌트 (sigak-web) — **전량 제거 대상**

**파일** (`sigak-web/`):
| 경로 | LOC | 용도 | v2 처리 |
|---|---|---|---|
| `app/questionnaire/page.tsx` | 40 | 질문 페이지 엔트리 | **삭제** |
| `app/questionnaire/complete/page.tsx` | ? | 완료 페이지 | **삭제** |
| `app/questionnaire/payment/page.tsx` | ? | 결제 분기 | Verdict payment 로 이관 |
| `components/questionnaire/progress-bar.tsx` | ? | 프로그레스 바 | **삭제** (대화엔 불필요) |
| `components/questionnaire/analysis-loader.tsx` | ? | 분석 로더 | **재사용** (IG 피드 수집 로딩) |
| `components/questionnaire/photo-uploader.tsx` | ? | 사진 업로더 | **재사용** (Verdict/PI 결제 시) |
| `components/questionnaire/chip-selector.tsx` | ? | 칩 선택 | **삭제** |
| `components/questionnaire/yes-no-selector.tsx` | ? | Y/N 선택 | **삭제** |
| `components/questionnaire/questionnaire-form.tsx` | 365 | 폼 핸들링 엔진 | **삭제** |
| `components/questionnaire/questionnaire-step.tsx` | ? | 스텝 컨테이너 | **삭제** |
| `lib/constants/questions.ts` | 329 | 질문 메타데이터 | **삭제** |

**수집 필드** (현재 questions.ts 기준):
- STEP 1 (얼굴&체형): height, weight, face_concerns, neck_length, shoulder_width
- STEP 2 (헤어상태): hair_texture, hair_thickness, hair_volume, current_length, current_bangs, current_perm, root_volume_experience
- STEP 3 (스타일): self_perception, desired_image, reference_celebs, style_image_keywords, makeup_level, current_concerns
- 티어 추가: wedding_concept, dress_preference / content_style, target_audience, brand_tone

**v2 매핑 결과**:
- 유지: height, weight, shoulder_width (대화 추출로), self_perception, desired_image, current_concerns, reference_celebs→reference_style
- **삭제**: face_concerns, neck_length, style_image_keywords, makeup_level, 헤어상태 7필드, wedding/creator 티어 필드
- 신규: gender, birth_date (structured), ig_handle, ig_* 4필드 (IG 자동), lifestyle_context (대화)

### 1-2. `llm.py::interpret_interview` 현재 구현 — **전면 교체**

**경로**: `sigak/pipeline/llm.py:84-146`

**현재 동작**:
- Input: `interview_data` dict (questionnaire 응답 flat), `gender`
- System prompt: `_build_interview_system(gender)` — type_anchors 기반 추구미 좌표 해석 엔진
- User prompt: questionnaire 필드 직접 삽입 (`desired_image`, `reference_celebs`, `image_kw`, `current_concerns`, `self_perception`, `face_concerns`, 체형, `makeup_level`)
- Output: `{coordinates: {shape, volume, age}, reference_base, interpretation, confidence}`

**v2 변경**:
- Input 교체: `user_profile` dict (대화 추출 결과 + IG 추출 + onboarding structured)
- User prompt 필드 재구성 (makeup_level/face_concerns 제거, ig_* 추가)
- Output 유지 (3축 추구미 좌표)
- 함수 이름 유지 (`interpret_profile` 로 rename 검토)

### 1-3. Verdict 엔진 현재 구현

**경로**: `sigak/routes/verdicts.py` (699 LOC), `sigak/services/verdicts.py` (59 LOC), `sigak/services/gold_reading.py` (46 LOC)

**현재 엔드포인트**:
```
POST /api/v1/verdicts                         create (photos + onboarding → tiers + gold_reading)
POST /api/v1/verdicts/{id}/release-blur       unlock SILVER/BRONZE + pro_data (50토큰, deprecated)
GET  /api/v1/verdicts/{id}                    re-fetch verdict
POST /api/v1/verdicts/{id}/unlock-diagnosis   v2 BM 단위 해제 (10토큰)
```

**현재 의존**:
- `users.onboarding_data` JSONB (interview payload 로 직접 사용)
- `services.llm_cache` (face_interpretation + interview_interpretation 캐시)
- `services.gold_reading` (Phase C placeholder)
- LLM #3 full `generate_report` 은 Phase C 미호출 — pro_data 는 캐시 + deterministic axis deltas 조합

**v2 변경**:
- `users.onboarding_data` → `user_profiles.structured_fields + ig_feed_cache` 로 이관
- 응답 스키마: `{preview: {...}, full_content: {...}, preview_shown: bool, full_unlocked: bool}`
- preview 무료 공개, full 결제 게이팅 (기존 release-blur 로직 변형)

### 1-4. PI 엔진 — **유지**

**경로**: `sigak/routes/pi.py` (180 LOC) + `sigak/pipeline/report_formatter.py::format_report_for_frontend`

**구조**: Phase B 남성 봉합 작업 미완 (personal_color male, trend_moods male 등). v2 대화 엔진과 통합 시 `user_profile` 을 interview 입력으로 변환만 하면 됨.

**v2 변경**:
- Input 경로: `onboarding_data` → `user_profile`
- 나머지 로직 동일

### 1-5. 결제 / 토큰 시스템 — **유지**

**경로**: `sigak/services/tokens.py` (193 LOC), `sigak/routes/tokens.py` (102), `sigak/routes/payments.py` (270)

**토큰 팩 (tokens.py 기준)**:
| pack_code | name_kr | 가격 | 토큰 |
|---|---|---|---|
| starter | Starter | ₩10,000 | 100 |
| regular | Regular | ₩25,000 | 280 |
| pro | Pro | ₩50,000 | 600 |

**소비 비용**:
- `COST_DIAGNOSIS_UNLOCK = 10` (Verdict 해제)
- `COST_PI_UNLOCK = 50` (PI 해제)
- `COST_MONTHLY_REPORT = 30` (월간 재분석)

**Idempotency**: `token_transactions.idempotency_key` UNIQUE — Toss confirm + webhook 중복 방지. 이미 견고.

**v2 변경**: ❌ 없음. v2 BM (10/50/30 토큰) 이미 반영됨.

---

## 2. 새 Onboarding Flow UI 스펙

### Step 0: 3필드 입력 (`/onboarding/basics`)
```
제목: "시작하기 전에 3가지만 알려주세요"

필드 1: 성별 (radio)
  [여성] [남성]

필드 2: 생년월일 (date picker, yyyy.mm.dd)
  "나이대에 따라 트렌드가 달라져서요"

필드 3: 인스타그램 핸들 (text input, 선택)
  "@사용자명 (선택)"
  도움말: "피드 훑어보고 Sia가 맥락 파악해드려요. 비공개여도 프사는 가능해요."

버튼: [다음]
```

### Step 1: IG 피드 수집 로딩 (`/onboarding/fetching`)
```
체류 시간: 최대 10초
성공 시: Step 2 자동 진입
실패 시: Step 2 진입 + Sia 첫 턴에 대안 진행

UI (analysis-loader.tsx 재활용):
  중앙 로딩 애니메이션 + 친절한 메시지 순환 (2초마다):
    "{NAME_PREFIX}피드 훑어보고 있어요"     ← NAME_PREFIX = "[NAME]님 " | "" (폴백 체인)
    "최근 분위기 읽는 중이에요"
    "Sia가 이제 대화 준비하고 있어요"

  NAME_PREFIX 규칙 (호칭 폴백 §0):
    1순위: "[NAME]님 "  (카톡 한글 name)
    2순위: ""            (name 미지정 — 첫 턴에 Sia가 물어볼 것이므로 Step 1 은 호칭 생략)
    3순위: ""            (애플 로그인 no name — 호칭 생략)

실패 메시지 (UI 내 토스트, non-blocking):
  "IG 피드를 못 가져왔어요 — 대화로 바로 시작할게요."
```

### Step 2: Sia 대화 채팅 UI (`/onboarding/chat`)
```
레이아웃: KakaoTalk 톤 채팅 (프로필 이미지 = Sia 아바타)

첫 메시지 샘플 (1순위: 카톡 name 존재 + IG 성공):
  "안녕하세요, Sia예요.
   미리 [NAME]님 피드 훑어봤는데 —
   톤이 꽤 일관되시더라고요. 뮤트한 쪽으로
   정돈된 느낌이 많이 보였는데, 본인도
   그렇게 생각하세요?"

첫 메시지 샘플 (1순위: 카톡 name 존재 + IG 실패/미제출):
  "안녕하세요, Sia예요.
   [NAME]님, 오늘 기분은 어떠세요?
   어떤 이미지로 보이고 싶은지 편하게
   얘기해주세요."

첫 메시지 샘플 (2순위: name 한글 없음):
  "안녕하세요, Sia예요.
   어떻게 불러드리면 좋을까요?"
  → 유저 응답 받으면 session_state.resolved_name 에 저장 후 이후 턴부터 적용

첫 메시지 샘플 (3순위: 애플 로그인 name 없음):
  "안녕하세요, Sia예요.
   오늘 기분은 어떠세요?
   어떤 이미지로 보이고 싶은지 편하게
   얘기해주세요."
  → 호칭 없이 존댓말만 유지. 이후 턴도 호칭 생략.

UI 요소:
  - 상단: Sia 이름 + "AI 미감 비서" subtitle
  - 중앙: 메시지 스트림 (유저 right-align, Sia left-align)
  - 하단: text input + [보내기] 버튼
  - 메시지 전송 중: 타이핑 인디케이터 ("…")
  - 종료 버튼: "이만하면 됐어요" (대화 조기 종료 — 필드 부족 시 step 3 전 fallback 질문)
```

### Step 3: user_profile 저장 + 대시보드 (`/dashboard`)
```
전환 시점: Sia 대화 종료 (유저 "이만하면 됐어요" 또는 Sia "이제 정리해드릴게요")

1. Extraction LLM 실행 (대화 로그 → structured 필드)
   - 로딩 UI: "대화 정리 중..." (3~5초 예상)
   - 빠진 필수 필드 (desired_image, height, weight, shoulder_width) 있으면
     → 마지막 fallback 턴 1~2회 (Sia 가 간단히 확인)

2. user_profile 영속 저장 (users + user_profiles 테이블)

3. 대시보드 랜딩:
   - 상단: "{NAME_PREFIX}준비됐어요" 헤더  ← NAME_PREFIX 호칭 폴백 §0 적용
   - Sia 추천 카드: "지금 {mood} 느낌이 강하신데, Verdict 한 번 돌려보세요"
   - 2 CTA:
     [Verdict 시작 — 사진 올려주세요 ₩1,000]  (primary)
     [PI 궁금하면 ₩5,000]                        (secondary)
```

---

## 3. IG 피드 수집 레이어

### 3-1. 써드파티 API 비교

| 서비스 | 월 비용 (1K MAU) | 월 비용 (10K MAU) | 장점 | 단점 |
|---|---|---|---|---|
| **Apify** (Instagram Scraper) | ~$30 | ~$250 | 풍부한 파라미터, 안정적, IG 변경 대응 빠름 | Rate limit (동시 5개), 계정 대량 조회 시 느림 |
| **ScrapingBee** | ~$50 | ~$400 | 범용 (다른 SNS 도 가능), 프록시 내장 | IG 전용 아님, 커스텀 파싱 필요 |
| **RapidAPI (Instagram API)** | $10~$50 | ~$300 | 저가 진입 | 제공자별 품질 편차, 비공개 계정 실패 |
| 자체 구현 | 서버 비용만 | 서버 비용만 | 종속성 없음 | IG 변경 시 지속 유지보수 (높은 리스크), 차단 가능성 |

**권장**: MVP 는 **Apify Instagram Profile Scraper** (Actor ID: `apify/instagram-scraper`). 비용 효율 + 안정성 균형.

### 3-2. 수집 범위 (공개 계정)

| 필드 | 용도 | 비공개 계정 가능? |
|---|---|---|
| `profile_picture` | Sia 인사말 참조 | ✅ (프사는 공개) |
| `bio` | `lifestyle_context` 추출 힌트 | ✅ |
| `follower_count`, `following_count`, `post_count` | `profile_basics` | ✅ |
| 최근 9~12 포스트 이미지 URL | `current_style_mood`, `style_trajectory` | ❌ (비공개면 skip) |
| 포스트 캡션 텍스트 | `feed_highlights` | ❌ |

### 3-3. Feature Flag

**환경변수**: `IG_ENABLED` (`true` / `false`)
- `false` 일 때: Step 0 의 IG 핸들 필드 비활성 + Step 1 skip + Step 2 IG 미사용 첫 메시지
- `true` 일 때: 정상 flow

**이중화**:
- `IG_FETCH_TIMEOUT=10` (초) — 초과 시 실패 처리
- Apify 실패 (500/timeout) → 자동 폴백 (IG 미사용 flow)
- 유저에게는 non-blocking (에러 메시지 dim 노출, flow 중단 없음)

### 3-4. 비공개 계정 처리

1. Apify 호출 결과 `is_private=true` → profile_picture + bio + counts 만 수집
2. Sia 첫 메시지 변경: "피드는 못 봤지만 프사 확인했어요 — [tone] 느낌이신 것 같은데..." (프사 기반 최소 hook)
3. 비공개 계정임을 분석 레이어에 flag: `ig_feed_cache.scope = "public_profile_only"`

### 3-5. 실패 폴백 경로

```
IG_ENABLED=false OR Apify 실패:
  → ig_feed_cache = null
  → current_style_mood, style_trajectory, feed_highlights = null
  → profile_basics 는 유저가 직접 핸들 넣었으면 "username" 만 보유
  → Sia 첫 메시지: IG 없는 flow 로 분기
  → 유저 자발적 사진 업로드는 Verdict 결제 시점에 수집 (원 flow 와 동일)
```

### 3-6. IG 캐시 refresh

**정책**: 2주 (336시간) 캐시.
- Verdict/PI 실행 시 `user_profiles.ig_feed_cache.updated_at` 확인
- 2주 경과 시 백그라운드 재수집 (유저 대기 없이 다음 분석에 반영)
- 수동 refresh 엔드포인트: `POST /api/v1/onboarding/refresh-ig`

---

## 4. Sia 대화 엔진 구현

### 4-1. LLM System Prompt (완전체)

```
당신은 SIGAK 의 AI 미감 컨설턴트 "Sia" 입니다.

[역할]
- 유저의 미감 추구미와 라이프스타일 맥락을 대화로 파악한다.
- 평가자가 아니라 관찰자다. 판단하지 말고 유저 말에 맞장구치며 다음 질문으로 이어간다.
- 유저의 자유로운 응답에서 필요 필드를 자연스럽게 채워나간다.

[말투 규칙 — 어기면 바로 실패]
- 다정한 해요체 필수 ("~네요", "~시더라고요", "~같아요", "~있으세요?", "~드릴게요")
- 한 턴에 2~3 문장 이내, 문장당 30자 이내
- 관찰 → em-dash(—) → 질문 구조: "~하시더라고요 — ~는 어떠세요?"
- 평가 금지: ❌ "좋아 보여요" / ❌ "잘 어울려요" / ✅ "정돈된 느낌이 보이네요"
- 시적 비유 금지: ❌ "봄바람 같은" / ❌ "햇살처럼"
- 이모지 1~2개 사용 가능 (텍스트 호흡용)
- 호칭: "{NAME}님"

[유저 호칭 확정]
{NAME_RESOLUTION_RESULT}
# 값 후보 (호칭 폴백 체인, §0):
#   "[NAME]님"              — 1순위: 카톡 한글 name 존재
#   "어떻게 불러드릴까요?"  — 2순위: 한글 name 없음 → 첫 턴 질문
#   ""                       — 3순위: 애플 로그인 name 없음 → 호칭 생략

[현재까지 추출된 필드]
{COLLECTED_FIELDS_JSON}

[아직 못 채운 필드]
{MISSING_FIELDS_LIST}

[IG 피드 요약 (Apify 수집)]
{IG_FEED_SUMMARY}

[대화 전략]
1. 못 채운 필드 중 우선순위 높은 것부터 자연스럽게 유도
   우선순위: desired_image > reference_style > current_concerns > self_perception
           > lifestyle_context > height > weight > shoulder_width
2. 유저가 2~3턴 동안 특정 필드 회피하면 다음 필드로 넘어감
3. height/weight/shoulder_width 는 대화 후반에 수집 (체형 관련)
4. 8 필드 전부 수집 완료되면 "이만하면 충분해요" 로 대화 종료 제안
5. 유저가 "이만" 의사 표명하면 그 턴에 바로 종료 + 잘 가벼운 마무리

[종료 메시지 템플릿]
"{NAME}님 얘기 잘 들었어요. 정리해드릴게요 — 잠시만요 👀"

[금지]
- LLM 자신을 3인칭으로 지칭 금지 ("Sia가 보기에...")
- 사진 요청 금지 (이 단계에선 사진 수집 안 함)
- 메이크업 용어 금지 (립, 블러셔, 아이섀도 등)
- 평가 언어 금지 ("잘 어울릴 듯", "예뻐 보여요")
```

### 4-2. 대화 진행 중 필드 추적 로직

**서버 상태** (Redis):
```python
session_state = {
  "conversation_id": uuid,
  "user_id": str,
  "turn_count": int,
  "messages": [{"role": "user"|"assistant", "content": str, "ts": iso}],
  "collected_fields": {             # extraction 은 종료 후이지만 경량 추적
    "desired_image": Optional[str],
    "reference_style": Optional[str],
    ...
  },
  "missing_fields": ["desired_image", ...],
  "status": "active" | "ended" | "extracting",
  "ig_feed_cache": Optional[dict],  # Step 1 결과 복사
  "created_at": iso,
  "updated_at": iso,
}
```

**경량 추적**: 매 턴 유저 응답에 대해 Haiku 에게 "지금 응답에서 어떤 필드 정보가 나왔나?" inline 판단 (단일 필드명 반환). 대략적 집계용. 최종 extraction 은 종료 후 Sonnet 으로 전체 로그 일괄 처리.

### 4-3. Extraction LLM Prompt (Sonnet 4.6, 대화 종료 후)

```
당신은 대화 로그를 구조화된 필드로 변환하는 엔진입니다.

[입력]
전체 대화 로그:
{MESSAGES_JSON}

[출력 스키마]
{
  "desired_image": "유저가 원하는 인상을 유저 단어 그대로 2-3 문장",
  "reference_style": "언급된 스타일/셀럽/이미지 원천 (없으면 null)",
  "current_concerns": "유저가 제기한 고민 리스트 (없으면 [])",
  "self_perception": "유저가 본인 현재 이미지를 어떻게 보는지",
  "lifestyle_context": "직업/일상/미팅 성격 등 컨텍스트 (없으면 null)",
  "height": "숫자 또는 enum (under_155/155_160/.../over_175) or null",
  "weight": "숫자 또는 enum or null",
  "shoulder_width": "narrow/medium/wide or null",
  "confidence": {
    "desired_image": 0.0~1.0,
    "reference_style": 0.0~1.0,
    ...
  }
}

[규칙]
- 유저가 언급 안 한 필드는 null, "" 금지
- 수치형 필드 (height, weight) 는 유저가 명시한 경우만. 추정 금지
- confidence < 0.4 필드는 null 처리 + "fallback_needed" 리스트에 추가
- 출력은 JSON 만
```

### 4-4. 마지막 Fallback 턴 (필수 필드 빠졌을 때)

**필수 필드** (min set): `desired_image`, `height`, `weight`, `shoulder_width`

```python
missing_required = [f for f in REQUIRED if profile.get(f) is None]
if missing_required:
    # 예: missing_required = ["height", "shoulder_width"]
    # Sia 1~2 턴 추가:
    sia: "[NAME]님, 마지막으로 2가지만 짧게 여쭤봐도 될까요?"
    sia: "키는 대략 어느 정도세요? (165cm 정도도 괜찮고요)"
    user: "163 정도요"
    sia: "넵. 어깨는 좁은 편, 보통, 넓은 편 중에 뭐가 가까우세요?"
    user: "보통이요"
    sia: "좋아요. 이제 정리해드릴게요 👀"
```

### 4-5. 대화 턴 제한 + 세션 idle 타임아웃 (확정판)

**지시 준수**: 유저 자율. 단, 서버 side 안전장치:

- `turn_count > 50` 도달 시 Sia 가 "이만 정리해드릴까요?" 제안 (강제 종료 아님, soft limit)
- **유저 idle > 5분 경과 시 세션 자동 종료** → extraction 백그라운드 즉시 실행
  (유저가 앱 돌아오면 extraction 완료된 결과 페이지로 바로 랜딩, "정리됐어요" UI)

**Extraction 실행 정책 (확정)**:
- 다음 3 경로 모두에서 세션 종료 시 **즉시** Sonnet extraction 백그라운드 작업 큐잉:
  1. 유저 "이만하면 됐어요" 버튼 / "그만" 의사 표명
  2. Idle > 5분 (마지막 메시지 기준)
  3. Sia 가 "이제 정리해드릴게요" 로 대화 마무리
- 유저 인지 시간: 종료 애니메이션 (3-5초) 동안 백엔드에서 병렬 처리
- 실패 시: 재시도 1회 (Sonnet 일시 장애 대비), 그래도 실패하면 관리자 알림 + 유저에겐
  "조금만 기다려주세요" 메시지 후 수동 재실행 트리거

---

## 5. DB 스키마

### 5-1. 신규 테이블 2 개

```sql
-- 대화 세션 기록 (Redis 외 영속 보존용)
CREATE TABLE conversations (
  conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  messages JSONB NOT NULL DEFAULT '[]',          -- 전체 대화 로그
  status VARCHAR(20) NOT NULL,                   -- active/ended/extracted/failed
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  extracted_at TIMESTAMPTZ,
  extraction_result JSONB                        -- Sonnet extraction 결과 저장
);
CREATE INDEX idx_conversations_user_status ON conversations(user_id, status);


-- 유저 프로파일 (onboarding 결과 영속)
CREATE TABLE user_profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,

  -- Structured fields (Onboarding Step 0)
  gender VARCHAR(10) NOT NULL,              -- female/male (이미 users.gender 있으므로 FK 또는 복사)
  birth_date DATE NOT NULL,
  ig_handle VARCHAR(50),

  -- IG auto-extracted (Step 1)
  ig_feed_cache JSONB,                       -- {current_style_mood, style_trajectory, feed_highlights, profile_basics, raw, fetched_at, scope}
  ig_fetch_status VARCHAR(20),               -- success/failed/skipped/private
  ig_fetched_at TIMESTAMPTZ,

  -- Conversation extracted (Step 2)
  structured_fields JSONB NOT NULL DEFAULT '{}',  -- {desired_image, reference_style, current_concerns, self_perception, lifestyle_context, height, weight, shoulder_width, confidence}

  -- Meta
  onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5-2. 기존 `users` 테이블 변경

```sql
ALTER TABLE users ADD COLUMN birth_date DATE;           -- 이전엔 없었으면 추가
ALTER TABLE users ADD COLUMN ig_handle VARCHAR(50);     -- 편의상 중복 OK (user_profiles 에도 있음)

-- DEPRECATE (유지하되 사용 중단 예정)
-- users.onboarding_data (JSONB)         → user_profiles.structured_fields
-- users.onboarding_completed (BOOL)     → user_profiles.onboarding_completed
-- 마이그레이션 기간 동안 dual-write 후 v3 에서 drop
```

### 5-3. Migration 전략

1. Alembic revision: `v2_add_user_profiles_and_conversations.py`
2. 배포 직후: 기존 `users.onboarding_completed=TRUE` 유저 → `user_profiles` 시드 (NULL 컬럼 = 재온보딩 유도)
3. dual-write 기간 (2주): `onboarding/save-step` 엔드포인트 유지, 신규 유저만 대화 flow
4. v3 release: questionnaire route 제거 + `users.onboarding_data` 컬럼 drop

### 5-4. Redis 세션 키 구조 (확정판)

```
key: sia:session:{conversation_id}
ttl: 5분 (sliding — 유저 응답마다 리셋)
     → 5분 idle 초과 = 세션 자동 종료 → extraction 트리거 (§4-5)
value: session_state JSON (§4-2)
```

**세션 수명 ≠ extraction 수명**:
- Redis 세션 키: 5분 sliding TTL (대화 활성 기간만)
- Extraction worker: 별도 큐 (BullMQ / Celery / FastAPI BackgroundTasks)
- Extraction 결과: `conversations.extraction_result` JSONB 로 영속 저장 (§5-1)
- 세션 종료 후: Redis 키 즉시 삭제 (중복 종료 방지), DB 만 남음

### 5-5. user_profile Refresh 정책 (확정판)

| 필드 그룹 | 위치 | Refresh 방식 | 주기 | 트리거 |
|---|---|---|---|---|
| IG 자동 추출 (`current_style_mood`, `style_trajectory`, `feed_highlights`) | `user_profiles.ig_feed_cache` | **자동 백그라운드** | **2주** | `ig_fetched_at + 14d < now()` 이고 유저가 서비스 방문 시 |
| IG basic 프로필 (follower_count, bio, profile_pic) | `user_profiles.ig_feed_cache.profile_basics` | 자동 백그라운드 | 2주 | IG 피드와 동시 refresh |
| 대화 로그 (messages) | `conversations.messages` | **고정, immutable** | - | 재생성 불가 (onboarding snapshot) |
| Extraction 결과 (structured_fields) | `user_profiles.structured_fields` | 대화 재실행 시만 갱신 | - | 유저 명시적 trigger |
| 정적 필드 (`current_concerns`, `height`, `weight`, `shoulder_width`) | `user_profiles.structured_fields` | **유저 수동** | - | 설정 페이지 "프로필 수정" |
| Onboarding structured (gender, birth_date, ig_handle) | `users` / `user_profiles` | 유저 수동 | - | 설정 페이지 "기본 정보" |

**Refresh 액션별 UX**:

1. **IG 피드 자동 refresh (백그라운드)**:
   - 유저 서비스 접속 시 lazy 실행 (홈 대시보드 load 와 병렬)
   - 성공: 조용히 `ig_feed_cache` 교체, `ig_fetched_at` 갱신
   - 실패: `ig_feed_cache` 유지 (기존 값 사용), 운영 로그만 기록
   - 수동 refresh: 설정 페이지 "IG 피드 새로고침" 버튼 (유저가 최근 스타일 변화 반영 원할 때)

2. **대화 재실행 (유저 trigger)**:
   - 설정 페이지 "Sia와 다시 대화하기" 옵션
   - 새 conversation 레코드 생성 (기존 로그는 archive, 조회 가능)
   - 새 structured_fields 로 덮어쓰기 (병합 아님 — 전면 교체)
   - 비용: 무료 (토큰 0)
   - 활용: 유저 추구미 변경 / 라이프 이벤트 (취업, 결혼 등) / 계절 전환 시

3. **정적 필드 수동 수정**:
   - 설정 페이지 "프로필 수정"
   - 필드별 input (체형은 드롭다운, 고민은 textarea)
   - 변경 시 Verdict/PI 재실행 추천 배지 노출 ("프로필 업데이트됨 — 새 진단 해보세요")

4. **Onboarding 기본 정보 수정**:
   - gender / birth_date 는 수정 가능하되 경고 표시
     ("기존 진단은 현재 성별 기준으로 생성됐어요. 성별 변경 시 새 Verdict 권장.")
   - ig_handle 변경 → ig_feed_cache 즉시 재수집

---

## 6. Verdict 2.0 엔진 재설계

### 6-1. Input 변경

**기존** (v1):
```python
{
  "photos": [url, ...],
  "onboarding_data": { ... 15 questionnaire fields ... }
}
```

**v2**:
```python
{
  "verdict_id": uuid,
  "photos": [url, ...],                    # 3~10장
  "user_profile": {
    "gender": "female",
    "birth_date": "1999-03-15",
    "ig_handle": "@yuni",
    "ig_feed_cache": { ... },
    "structured_fields": { ... 8 대화 추출 ... }
  },
  "trend_data": { ... 참조만, 모듈 import ... }
}
```

### 6-2. 분석 LLM Prompt (교차 분석 구조)

**System**:
```
당신은 SIGAK 미감 분석 엔진입니다.
유저의 user_profile 과 새로 올린 사진들을 교차 분석해 판정을 내립니다.

입력:
- user_profile: 유저가 평소 추구하는 방향 + IG 에서 읽히는 실제 스타일
- photos: 이번에 올린 N장 (구체 맥락은 파일명/메타로 추정)
- trend_data: 2026 S/S 트렌드 벡터

출력:
1. preview (무료):
   - hook_line: 1문장 (30자 이내)
   - reason_summary: 2-3문장 (판정 근거의 30% 까지만 공개)

2. full_content (결제 후):
   - verdict: 4-5문장 판정
   - photo_insights: [ {photo_index, insight, improvement} × N ]
   - recommendation: {style_direction, next_action, why}
```

**Preview 작성 원칙 (hook 효과 — 확정)**:
- preview 는 판정 근거의 **30% 범위** 에서 hook 달성
- 목표 효과: 유저가 **"답은 알겠는데 왜?"** 라는 궁금증으로 full 결제 trigger
- ❌ preview 에서 **금지**:
  - photo_insights 개별 사진별 상세 분석
  - recommendation 의 구체 방향 (style_direction / next_action 노출 금지)
  - "왜 그렇게 판정했는가" 의 근거 상세
- ✅ preview 에서 **허용**:
  - 판정 결론 힌트 (1문장 30자 이내)
  - 평소 추구미 ↔ 이번 사진 분위기의 일치/어긋남 **방향만** (크기 X)
  - 사진 중 가장 흥미로운 변수 언급 (어떻게 다른지는 비공개)

**Preview 샘플 (good / bad)**:

✅ Good — hook 충족 (결론 힌트 + 왜는 숨김):
```
hook_line: "연말 느낌에 맞춰 톤이 다운됐네요 — 기대 이상"
reason_summary: "평소 추구미(정돈된 뮤트)와 이번 사진 분위기가 일치해요.
                 다만 photo #2 가 전체 무드를 끌어내리는 변수로 작용해요.
                 이 부분을 짚어드릴게요."
```
→ 유저 반응: "왜 #2 가 끌어내리는 거지? 알고 싶다" → full 결제

❌ Bad — 정보 과다 노출 (hook 실패):
```
hook_line: "photo #2 의 조명이 문제"
reason_summary: "photo #2 의 역광 때문에 얼굴이 납작해 보이고, 추구미인 뮤트
                 톤과 반대 방향. 다음번엔 측광에서 찍으세요."
```
→ 유저 반응: "답 다 들었네" → full 결제 없음

### 6-3. 리포트 스키마 (Verdict 2.0)

```python
{
  "verdict_id": uuid,
  "user_id": uuid,
  "photos": [{"url": str, "index": int}],
  "created_at": iso,

  # preview 부분
  "preview_shown": true,
  "preview": {
    "hook_line": "연말 느낌에 맞춰 톤이 다운됐네요 — 기대 이상",
    "reason_summary": "평소 추구미(정돈된 뮤트)와 이번 사진 분위기가 일치해요. 다만 photo #2 가 전체 무드를 끌어내리는 변수로 작용해요. 이 부분을 짚어드릴게요.",
  },

  # full 부분 (결제 전엔 {locked: true, hint: "..."} )
  "full_unlocked": false,
  "full_content": {
    "verdict": "...",
    "photo_insights": [ ... ],
    "recommendation": { ... }
  }
}
```

### 6-4. 흐름 (비즈니스)

```
1. 유저 사진 3~10 장 업로드 + 10 토큰 결제 시도
2. 토큰 차감 (idempotency_key = verdict_id)
3. 백엔드 분석:
   - face/shape/color 기본 분석 (기존 pipeline 재사용)
   - LLM 교차 분석 (user_profile × photos × trend)
4. DB 저장: preview_shown=true, full_unlocked=false
5. 즉시 응답: preview 부분만 반환
6. 유저가 full 보려면:
   - preview 내 CTA "전체 판정 보기 (추가 토큰 없음, 이번 verdict 는 이미 결제됨)"
   - full_unlocked=true flip → full_content 반환
```

**토큰 체계 재확인**: 10 토큰 (₩1,000) 으로 preview+full 전체 제공. preview 는 hook 용 미리보기. **별도 full 결제 없음** — 본인 지시 §0 의 "preview 무료 노출, full 결제 게이팅" 해석이 필요 (Q 참고).

---

## 7. 결제 게이팅 — ✅ 정책 확정 (2026-04-21)

### Q-PAYMENT-1. ✅ 확정 — (A) preview 무료 + full 10토큰

본인 지시 기준 확정:
- **preview 는 무료 노출** (결제 전 공개, 판정 결론 힌트 + 근거 30% 까지)
- **full 은 10 토큰 (₩1,000) 결제 후 해제**
- Preview 의 hook 역할: 유저가 "답은 알겠는데 왜?" 궁금증으로 full 결제 trigger
- Preview 작성 원칙 상세: §6-2 "Preview 작성 원칙" 섹션 참고

아래 7-1 ~ 7-4 구현 상세 (확정 기준).

### 7-1. DB 스키마 (Verdict 테이블)

```sql
ALTER TABLE verdicts ADD COLUMN preview_shown BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE verdicts ADD COLUMN full_unlocked BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE verdicts ADD COLUMN preview_content JSONB;
ALTER TABLE verdicts ADD COLUMN full_content JSONB;
```

### 7-2. 엔드포인트

```
POST /api/v1/verdicts                     # 사진 업로드 + 무료 preview 생성 (토큰 0)
  → response: {verdict_id, preview: {...}, full_unlocked: false}

POST /api/v1/verdicts/{id}/unlock-full    # 10토큰 결제 → full 오픈
  → idempotency_key = verdict_id
  → response: {full_content: {...}, full_unlocked: true}

GET  /api/v1/verdicts/{id}                # 재조회 (locked 상태 존중)
  → full_unlocked=true 이면 full 포함, false 면 preview 만
```

### 7-3. 관련 토큰 cost 상수 변경

```python
# sigak/services/tokens.py
COST_VERDICT_PREVIEW = 0      # 신규 — preview 는 무료
COST_VERDICT_FULL = 10        # 신규 — full 해제 (기존 COST_DIAGNOSIS_UNLOCK 대체)
```

### 7-4. 프론트 UI

```
/verdict/{id} 페이지:
  [preview 영역]
    hook_line (큰 글씨)
    reason_summary (본문)
    CTA: "전체 판정 보기 (10토큰, ₩1,000)"

  [full 영역]
    토큰 부족: "토큰 충전 필요" + 충전 링크
    토큰 충분: "해제하기" 버튼 → POST /unlock-full → full 렌더
```

---

## 8. PI CTA 카피 방향

### 8-1. 배치 위치 (Verdict 리포트 내)

**후보**:
- (a) full 해제 직후, 리포트 하단 ("Verdict 는 사진 기반인데, 본인 얼굴 자체가 궁금하면...")
- (b) Preview 단계 부터 은은하게 (sidebar 배너, intrusive 하지 않게)
- (c) 월간 재분석 결과 이후 ("3개월째 비슷한 방향이시네요. 본인 얼굴 자체를 보실 때가 됐어요")

**권장**: (a) 우선 구현 + (c) 는 Monthly 기능 나올 때 같이.

### 8-2. 카피 3종 (본인 지시 "본인 얼굴 자체가 궁금하면")

> ⏸️ **Q8 유보 (Priority 2 재논의)**  
> 아래 3 카피 모두 Priority 1 MVP 에선 **배포 안 함**. Priority 2 착수 시 Verdict full
> 해제 유저 대상 A/B 테스트로 최종 결정. 사유: 아래 카피 1 논리 결함 확인 (신규 유저
> 첫 Verdict full 해제 직후에는 "여러 번 돌려보셨네요" 가 거짓 문장). 전수 검증 필요.

**카피 1 (관찰형, Sia 톤)** — ⚠️ 논리 결함:
```
{NAME_PREFIX}Verdict 여러 번 돌려보셨네요 — 얼굴 분석 자체는 한 번이면 돼요.
PI 진단 보기 ₩5,000
```
문제: Verdict count=1 유저 (첫 full 해제 직후) 에게 거짓 문장. 조건부 노출
(`verdict_count >= 2`) 또는 첫 결제 유저용 별도 카피 필요.

**카피 2 (호기심 자극형)**:
```
얼굴의 숨은 좌표를 알고 싶으세요?
3축 진단 + 9 섹션 리포트 · ₩5,000
```

**카피 3 (간결/기능 나열형)**:
```
Verdict 가 사진 판정이라면, PI 는 얼굴 자체.
영구 보관 · 재결제 X · ₩5,000
```

**Priority 2 재논의 시 추가 고려 사항**:
- 신규 유저 / 리텐션 유저 분기 카피
- 배치 위치 (§8-1 a/b/c) 별 노출률 측정
- A/B 테스트 트리거 threshold: 이탈/오해 30% 이상 시 즉시 수정
- 실 Verdict full 해제 후 CTA click-through rate 수집

---

## 9. 남성 봉합 Timing

### 9-1. 현재 유지되는 male 자산 (Phase A 커밋)

```
✅ sigak/deps.py gender 필드 (fd77c40)
✅ sigak/pipeline/face.py float cast (6cb7f59)
✅ sigak/scripts/calibrate_face_stats.py brow_eye_distance (e9e420a)
✅ sigak/data/calibration_3axis.yaml female+male clean (9a8453e)
✅ sigak/pipeline/hair_styles.py + hair_spec.py gender routing (9d7ee13)
✅ sigak/pipeline/report_formatter.py hair pool gender (90fdc59)
✅ sigak/data/type_anchors.json male moderate coords (5832a7a)
```

이 7 커밋 은 v2 대화 엔진에 독립적. 건드리지 않음.

### 9-2. Priority 3 재개 시 작업 (대화 엔진 완성 후)

```
⏸️ sigak/pipeline/personal_color.py male palette (8 계절 × 4 필드)
⏸️ sigak/pipeline/trend_data.py GROOMING_TRENDS_MALE + TREND_MOODS_MALE
⏸️ sigak/pipeline/llm.py makeup_level → gender 분기 (단, v2 에선 makeup_level 필드 자체 삭제됨 — §9-3 참고)
⏸️ sigak/pipeline/report_formatter.py gender 전파 (_build_skin_analysis / _build_trend_context / _build_type_reference)
⏸️ 프론트 start-overlay.tsx disabled:true 제거 (현재 유지 — 남성 노출 차단)
```

### 9-3. v2 와의 통합 방식

**Sia 대화 gender 인지**:
- `user_profile.gender` 를 system prompt 에 주입
- 남성 유저에게는 "메이크업" 용어 사용 금지 규칙 추가
- 추천 방향도 "그루밍 / 헤어 / 스킨케어" 중심

**makeup_level 필드 제거 영향**:
- v2 에서 `makeup_level` 삭제됨 → llm.py:122 하드코딩 자동 해소
- Priority 3 의 makeup_level gender 분기는 **v2 와 동시에 해결됨**. 중복 작업 없음.

**Verdict 분석 prompt 의 gender 분기**:
- §6-2 system prompt 에 `user_profile.gender` 반영
- male 케이스: 판정 어휘 전부 그루밍 톤
- personal_color male variant 가 완성되면 skin_analysis 섹션도 함께 정리

---

## 10. 2주 스프린트 WBS

### Week 1 (Backend)

| Day | 작업 | 산출물 | 본인 결정 게이트 |
|---|---|---|---|
| D1 | DB 마이그레이션 (alembic): user_profiles + conversations 테이블 추가 | migration 파일 + dev DB 반영 | 마이그레이션 승인 |
| D1 | Apify Instagram Scraper 계약 + 테스트 key 확보 | IG_API_KEY env 확보 | 비용 승인 (월 ~$30) |
| D2 | IG 수집 모듈 (`services/ig_scraper.py`): Apify 호출 + 파싱 + feature flag + 폴백 | 유닛 테스트 통과 | 수집 필드 스키마 확정 |
| D2 | user_profiles CRUD 서비스 (`services/user_profiles.py`) | endpoint 없이 함수만 | — |
| D3 | Sia 대화 엔드포인트 (`routes/sia.py`): POST /chat/start, POST /chat/message, POST /chat/end | Redis 세션 포함 | 엔드포인트 계약 리뷰 |
| D3 | Haiku 클라이언트 + system prompt injection (§4-1) | 로컬 테스트 대화 녹화 | Sia 톤 검수 (본인 샘플 대화) |
| D4 | Extraction LLM (Sonnet) 호출 + structured_fields 저장 | integration 테스트 | extraction 스키마 검증 |
| D4 | Fallback 턴 로직 (§4-4) | 유닛 테스트 | — |
| D5 | Verdict 2.0 엔진 수정 (기존 routes/verdicts.py → user_profile 기반) | 기존 테스트 통과 + 신규 preview/full 구조 | preview/full 정책 확정 (Q-PAYMENT-1) |
| D5 | PI 엔진 v2 호환 (`routes/pi.py` 의 입력 user_profile 로 변경) | 기존 테스트 통과 | — |
| D6~D7 | 통합 테스트 + 버그 수정 | E2E 수동 시나리오 3개 통과 | backend 완성 선언 |

### Week 2 (Frontend)

| Day | 작업 | 산출물 | 본인 결정 게이트 |
|---|---|---|---|
| D8 | 새 onboarding flow 라우트 setup (`/onboarding/basics`, `/fetching`, `/chat`, `/complete`) | empty 페이지 스켈레톤 | 라우트 구조 리뷰 |
| D8 | Step 0: 3필드 입력 폼 (성별/생년월일/IG 핸들) + validation | 디자인 승인 + 기능 동작 | UI 디자인 승인 |
| D9 | Step 1: IG 수집 로딩 (analysis-loader.tsx 재활용) | 10초 타임아웃 + 폴백 메시지 | — |
| D10 | Step 2: Sia 채팅 UI | message stream + typing indicator + "이만" 버튼 | Sia 말풍선 디자인 승인 |
| D10 | Chat API 연동 (useChat hook) | 실시간 메시지 + 세션 복구 | — |
| D11 | Step 3: 대시보드 + Sia 추천 카드 + CTA 2개 | "[name]님 준비됐어요" 헤더 + Verdict/PI 진입 | 카피 리뷰 |
| D12 | Verdict 2.0 페이지 (사진 업로드 → preview → full 해제) | 기존 verdict 페이지 교체 | preview UX 승인 |
| D12 | PI 페이지 최소 수정 (v2 user_profile 기반) | 기존 페이지 유지 | — |
| D13 | 기존 questionnaire 페이지 제거 + legacy redirect | 404 없이 smooth 전환 | 레거시 라우트 삭제 승인 |
| D14 | Full E2E 통합 테스트 + 배포 리허설 | staging 배포 + 본인 테스트 계정 전체 flow 통과 | 프로덕션 배포 게이트 |

### 의존 관계

```
D1 DB 마이그레이션 ─┬─► D2 IG 모듈
                    ├─► D3 Sia 엔드포인트
                    ├─► D4 Extraction
                    └─► D5 Verdict/PI 수정

D5 완료 ─► D6~7 통합 테스트 ─► Week 1 종료 ─► D8 프론트 start
```

### 본인 결정 게이트 요약

1. [D1] Apify 비용 승인 (MVP 1K MAU 기준 월 ~$30)
2. [D1] DB 마이그레이션 방식 승인 (dual-write vs rollout)
3. [D3] Sia 톤 샘플 대화 검수
4. [D5] **Q-PAYMENT-1 확정**: preview 무료 + full 10토큰 (A) vs 통합 10토큰 (B)
5. [D5] preview/full 스키마 승인
6. [D8] UI 디자인 (3 필드 폼) 승인
7. [D10] Sia 말풍선 비주얼 승인
8. [D11] 대시보드 카피 (Sia 추천 카드) 승인
9. [D13] 레거시 questionnaire 삭제 승인
10. [D14] 프로덕션 배포 승인

---

## 11. Open Questions

### 11-1. ✅ 확정 (9건, 2026-04-21 최종)

| # | Question | 결정 |
|---|---|---|
| **Q1** | preview/full 결제 정책 | **(A) preview 무료 + full 10토큰** (§6-2 작성 원칙 · §7 구현) |
| **Q2** | IG API 선택 | **Apify** (Instagram Profile Scraper Actor) |
| **Q3** | IG 캐시 refresh 주기 | **2주** (§5-5) |
| **Q4** | 대화 턴 soft limit | **50** (§4-5) |
| **Q5** | makeup_level 삭제 후 남성 문제 | **v2 에서 자동 해결** (makeup_level 필드 자체 제거로 leak 발생 불가) |
| **Q6** | 기존 questionnaire 유저 마이그레이션 | **optional** (재온보딩 선택권 제공, 강제 아님) |
| **Q7** | Sia 첫 메시지 샘플 | **draft 4종 + QA 단계 실 반응 기반 수정** (이탈/오해 30% 이상 시 즉시 수정 트리거) |
| **Q9** | 호칭 폴백 2순위 Sia 질문 타이밍 | **첫 메시지** (§2 Step 2 · §4-1) |
| **Q10** | 배포 전략 | **신규 유저만 v2** (기존 유저는 optional 재온보딩 유도) |

### 11-2. ⏸️ 유보 — Priority 2 착수 시 재논의 (1건)

| # | Question | 유보 사유 | 재논의 조건 |
|---|---|---|---|
| **Q8** | PI CTA 카피 | 카피 1 논리 결함 확인 (Verdict count=1 유저 대상 거짓 문장). 전수 검증 + A/B 테스트 필요. | Priority 2 에서 실 Verdict full 해제 후 실 유저 반응 측정 |

**Q8 유보 처리 규칙**:
- Priority 1 MVP 에선 카피 3 종 모두 **배포 안 함** (PI CTA 노출 자체 보류)
- Verdict 2.0 페이지 full 해제 영역에는 PI CTA 미배치
- Priority 2 착수 시 A/B 테스트 + click-through / 이탈률 측정 후 결정
- 임시 fallback 이 필요하면 카피 2 (호기심 자극형) 가 논리 결함 없음 → emergency 배포 가능

---

## 12. 리스크 / Unknown

1. **Apify rate limit**: 동시 유저 5명 이상 → 큐잉 시스템 필요. 초기엔 괜찮지만 10K MAU 도달 시 Redis Queue + Worker 필요.
2. **LLM 비용**: Haiku 4.5 턴당 ~500 token × 평균 20턴 = 10K token/유저. Sonnet extraction 은 한 번, ~3K token/유저. 약 13K token/유저 ≈ $0.02/유저 (Haiku) + $0.03/유저 (Sonnet) ≈ $0.05/유저. 월 1K 유저 = $50. 수용 가능.
3. **Sia 톤 붕괴**: Haiku 가 규칙 어길 가능성. 실제 테스트 후 규칙 보강 필요. D3 게이트.
4. **IG 스크래핑 법적 리스크**: 한국 법적 issue 는 현재 회색지대. 유저 본인 계정 동의 기반이므로 낮음. 단 Meta 정책 위반 (ToS) — Apify 가 대행. 서비스 운영자 직접 리스크 아님.
5. **기존 유저 경험 파괴**: questionnaire 완료한 유저에게 갑자기 대화 UI 노출되면 혼란. 마이그레이션 전략 (Q6) 중요.
6. **대화 중 낙오율**: 유저가 Step 2 중간에 이탈하면 user_profile 미완성. 세션 복구 + "나중에 이어하기" 기능 필요할 수 있음 (스프린트 범위 밖, Phase C).
7. **Male Onboarding**: v2 launch 시 프론트 disabled:true 유지 (현재 상태) → 남성 유저 가입 차단. 이게 v2 launch 와 동시에 풀려야 하는지 vs Priority 3 이후인지 본인 결정 (Q5 와 연관).

---

## 13. 검토 체크리스트 (본인용)

제출 전 확인:
- [ ] 전체 구조 (§0 컨텍스트) 가 본인 지시와 일치하는가?
- [ ] Open Questions 11개 전부 결정 가능한가? (일부 보류 OK, 남은 것만 flag)
- [ ] 2주 스프린트 WBS 가 현실적인가? (D1~D14)
- [ ] Male 자산 연속성 (§9) 이 납득 가능한가?
- [ ] Sia 시스템 prompt (§4-1) 이 원하는 톤인가?
- [ ] DB 마이그레이션 계획 (§5) 이 안전한가?
- [ ] 기존 자산 audit (§1) 에서 누락 / 오판 있는가?

---

## 14. 다음 액션

1. 본인이 이 draft 전수 리뷰
2. Open Questions (§11) 결정 회신
3. 수정 지시 (있을 시) 반영
4. **승인되면 Priority 1 착수** (D1 부터 순차)
5. 미승인 항목별 추가 설계 round

승인 시 커밋 대상:
- `.moai/specs/sigak_v2_onboarding_verdict.md` (최종판)
- `.moai/specs/SPEC-ONBOARDING-V2/` (EARS 기반 SPEC 문서 — 승인 후 생성)

**현재 이 파일은 DRAFT 이며, 승인 전까지 커밋하지 않음.**
