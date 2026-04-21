---
id: SPEC-ONBOARDING-V2
plan_version: "1.0.0"
created: "2026-04-21"
---

# SPEC-ONBOARDING-V2 Implementation Plan

## Overview

2주 스프린트 (Week 1 backend, Week 2 frontend). 일 단위 WBS.

---

## Week 1 — Backend

### D1 (2026-04-22) — DB & 외부 서비스
- Alembic migration: `user_profiles` + `conversations` 테이블 (신규)
- `users` 테이블 ALTER: `birth_date DATE`, `ig_handle VARCHAR(50)`
- Apify 계정 생성 + API key 확보 (파운더 액션)
- 환경변수 추가: `APIFY_API_KEY`, `IG_ENABLED`, `ANTHROPIC_MODEL_HAIKU`, `ANTHROPIC_MODEL_SONNET`

**Deliverable**: migration 파일 + Apify key. Dev DB 반영 완료.
**Review gate**: migration SQL 승인.

### D2 (2026-04-23) — IG 수집 + Profile CRUD + Schemas

**신규 파일 (4)**:
- `sigak/schemas/__init__.py`
- `sigak/schemas/user_profile.py` (Pydantic v2 schemas — D2 contract #4)
  - `StructuredFields`, `IgFeedCache`, `ExtractionResult`, `ConversationMessage`
  - 모든 JSONB 컬럼의 application-level validation
- `sigak/services/ig_scraper.py` (Apify 래퍼, feature flag, 10s timeout, 폴백)
- `sigak/services/user_profiles.py` (CRUD)

**`services/user_profiles.py` 필수 함수**:
```python
def create_profile_on_onboarding(db, user_id, gender, birth_date, ig_handle=None) -> UserProfile
  # D2 contract #1: Step 0 제출 직후 row 생성 (gender/birth_date NOT NULL 보장)

def migrate_v1_user_to_v2(db, user_id, birth_date, ig_handle=None) -> UserProfile
  # D2 contract #2: users.gender 복사 + Step 0 신규 필드

def get_profile(db, user_id) -> Optional[UserProfile]
def upsert_ig_feed_cache(db, user_id, cache: IgFeedCache, status: str) -> None
def merge_structured_fields(db, user_id, fields: StructuredFields) -> None  # shallow merge
def refresh_ig(db, user_id) -> None  # 강제 재수집
def restart_conversation(db, user_id) -> None  # structured_fields 초기화
```

**conversation 라이프사이클 구현 (D2 contract #3)**:
- 아직 route 단 구현은 D3. D2 는 util만:
  - `services/conversations.py` (신규):
    - `create_ended_conversation(db, user_id, conv_id, messages) -> None`
      (INSERT with status="ended", messages=Redis snapshot)
    - `mark_extracted(db, conv_id, result: ExtractionResult) -> None`
    - `mark_failed(db, conv_id) -> None`

**유닛 테스트**:
- Apify mock 응답 (성공 / 비공개 / 실패 / timeout)
- `migrate_v1_user_to_v2` 에서 users.gender 복사 검증
- Pydantic schema valid / invalid payload

**Deliverable**: 4 모듈 + 유닛 테스트.
**Review gate**: IG 수집 스키마 + Pydantic 스키마 확정.

### D3 (2026-04-24) — Sia 대화 엔드포인트 (persona 재작성 반영)

**신규 파일 (4)**:
- `sigak/services/sia_session.py` — Redis 세션 유틸 (sliding TTL 5분)
- `sigak/services/sia_llm.py` — Haiku 4.5 클라이언트 + system prompt injection
- `sigak/routes/sia.py`:
  - `POST /api/v1/sia/chat/start` — Redis session 생성 + 첫 메시지 (오프닝)
  - `POST /api/v1/sia/chat/message` — 다음 턴 처리 (유저 입력 수신 → Sia 응답)
  - `POST /api/v1/sia/chat/end` — 명시 종료 + create_ended_conversation + extraction 큐잉
- `sigak/tests/test_sia_samples.py` — 샘플 대화 자동 검증

**Sia system prompt 완전체 (§4-1 draft 그대로 이식)**:
- Hard Rules 5 (Verdict/판정 단어 금지, 마크다운 금지, 이모지 금지)
- 서술형 정중체 enforcement
- 4지선다 구조 + 주관식 예외 2개 필드
- 구체 숫자 근거 규칙 (데이터 없으면 숫자 생략)
- 호칭 폴백 3단 로직

**샘플 대화 녹화 (본인 검수 대상 3종)**:
1. 오프닝 (1순위 name + IG 성공)
2. 중간 턴 (유저 4지선다 선택 반영 + 주관식 심화)
3. 클로징 ("시각이 본 나" CTA 자연 흡수)

**`test_sia_samples.py` 검증 규칙** (REQ-SIA-002a/b/c + AC-SIA-HR*):
```python
# 각 샘플 응답에 대해:
assert "verdict" not in sample.lower()          # HR1
assert "판정" not in sample                     # HR2
assert not re.search(r"\*\*|##|^>|```", sample) # HR3
assert not re.search(r"^[ \t]*\*", sample, re.M) # HR4 (별표 bullet)
assert not re.search(EMOJI_PATTERN, sample)     # HR5
# 문장당 35자, 턴당 ≤3 문장, 서술형 어미 존재, 금지 어미 부재
```

**Mock 데이터 전략 (D3 → D4 이관)**:
- D3 샘플 녹화 시 IG_FEED_SUMMARY / vision analysis 는 mock 고정값
  (예: post_count=38, dominant_mood="쿨뮤트" 68%, chroma=1.4배)
- D4 Verdict 엔진에서 실 vision analysis 파이프라인 구현
- Sia LLM 은 주입된 숫자를 그대로 사용. Sia 가 직접 숫자 계산하지 않음.

**Deliverable**: 4 신규 파일 + Redis 통합 + 샘플 대화 녹화 3종.
**Review gate**:
  - 샘플 대화 녹화 자동 검증 전부 통과
  - 본인 검수 체크리스트 10 항목 통과 (아래)

**본인 검수 체크리스트 (D3 샘플 대화 리뷰 시)**:
- [ ] "verdict" / "판정" 단어 0건
- [ ] 마크다운 0건 (`**`, `*`, `##`, `>`)
- [ ] 이모지 0건
- [ ] "~네요" / "~같아요" 0건
- [ ] "~합니다" / "~습니다" 사용
- [ ] 확인 요청 없음 ("본인도 그렇게 생각하세요?" X)
- [ ] 4지선다 질문 구조 (주관식 예외 2개 필드 외)
- [ ] 구체적 숫자 포함 (mock OK, 조작 감지 시 알림)
- [ ] 유저 한 문장 정의 포함 (오프닝: "{NAME}님은 X 인 분입니다")
- [ ] "시각이 본 나" CTA 자연 흡수 (클로징, 1 문장 이내)

### D4 (2026-04-25) — Extraction Pipeline
- Sonnet 4.6 extraction 호출 (`services/extraction.py`)
- BackgroundTasks 큐잉 (FastAPI 기본)
- Fallback 턴 로직 (§4-4 of design doc)
- 재시도 1회 정책

**Deliverable**: extraction 동작. conversations.extraction_result 저장 확인.
**Review gate**: extraction 스키마 검증.

### D5 (2026-04-26) — Verdict 2.0 + PI 엔진 수정
- `sigak/routes/verdicts.py` 수정:
  - `POST /api/v1/verdicts` — preview 무료 생성 (토큰 0)
  - `POST /api/v1/verdicts/{id}/unlock-full` — 10토큰 해제
  - `GET /api/v1/verdicts/{id}` — full_unlocked 상태 존중
- preview 생성 prompt (≤30% disclosure) 작성
- `sigak/routes/pi.py` 의 input 소스 변경: `onboarding_data` → `user_profile`
- 토큰 cost 상수 변경: `COST_VERDICT_FULL = 10` (기존 `COST_DIAGNOSIS_UNLOCK` 대체)

**Deliverable**: Verdict 2.0 엔드포인트 3종 + PI v2 호환.
**Review gate**: preview/full 스키마 검증.

### D6-D7 (2026-04-27~28) — 통합 테스트 + 버그 수정
- E2E 시나리오 3종:
  1. 신규 유저 (카톡 한글 name + IG 성공) onboarding 완주 → Verdict → PI
  2. 신규 유저 (한글 name 없음 + IG 실패) onboarding → 재온보딩
  3. 남성 유저 (v2) → onboarding (UI 차단 우회 테스트 계정) → Verdict preview
- 버그 수정 + 성능 측정 (LLM 응답 지연)

**Deliverable**: E2E 3 시나리오 통과 + backend 완성 선언.
**Review gate**: 백엔드 완성 confirmation.

---

## Week 2 — Frontend

### D8 (2026-04-29) — Onboarding 라우트 스켈레톤 + Step 0
- `sigak-web/app/onboarding/basics/page.tsx` (Step 0: 3필드 폼)
- `sigak-web/app/onboarding/fetching/page.tsx` (Step 1: 로딩)
- `sigak-web/app/onboarding/chat/page.tsx` (Step 2: Sia 채팅)
- `sigak-web/app/onboarding/complete/page.tsx` (Step 3: 대시보드)
- Step 0 폼 validation (gender/birth_date 필수, ig_handle 선택)

**Deliverable**: 라우트 구조 + Step 0 기능 동작.
**Review gate**: UI 디자인 승인.

### D9 (2026-04-30) — Step 1 IG 로딩
- `analysis-loader.tsx` 재활용
- 10초 타임아웃 + 순환 메시지 (NAME_PREFIX 변수화)
- 실패 시 non-blocking 토스트

**Deliverable**: Step 1 로딩 UX 완성.

### D10 (2026-05-01) — Step 2 Sia 채팅 UI
- 메시지 스트림 (KakaoTalk 톤)
- Typing indicator
- "이만하면 됐어요" 버튼
- Sia 아바타 + 호칭 라벨
- `useChat` hook (Redis 세션 연동)

**Deliverable**: 채팅 UI 완성 + API 연동.
**Review gate**: Sia 말풍선 디자인 승인.

### D11 (2026-05-02) — Step 3 대시보드 + CTA
- 헤더 (`{NAME_PREFIX}준비됐어요`)
- Sia 추천 카드
- Verdict CTA / PI CTA (Q8 유보 → PI CTA 미노출 버전)

**Deliverable**: 대시보드 완성.
**Review gate**: 카피 리뷰.

### D12 (2026-05-03) — Verdict 2.0 페이지
- 사진 업로드 UI (photo-uploader.tsx 재활용, 3~10장)
- preview 렌더링 (무료 섹션)
- "전체 판정 보기 (10토큰)" CTA
- full 해제 후 full_content 렌더 (기존 리포트 뷰어 재활용)

**Deliverable**: Verdict 2.0 페이지 완성.
**Review gate**: preview UX 승인.

### D13 (2026-05-04) — Legacy 제거
- `sigak-web/app/questionnaire/*` 삭제
- `sigak-web/components/questionnaire/questionnaire-*.tsx` 삭제 (progress-bar / analysis-loader / photo-uploader 제외)
- `sigak-web/lib/constants/questions.ts` 삭제
- `/questionnaire/*` 라우트 → `/onboarding/basics` 리다이렉트

**Deliverable**: 레거시 제거 + smooth redirect.
**Review gate**: 레거시 삭제 승인.

### D14 (2026-05-05) — Full E2E + 배포 리허설
- staging 배포
- 파운더 테스트 계정 (신규 + 기존 v1) 전체 flow
- 프로덕션 배포 gate

**Deliverable**: staging 통과 + 배포 준비.
**Review gate**: 프로덕션 배포 승인.

---

## Critical Path / Dependencies

```
D1 DB 마이그레이션 ─┬─► D2 IG 모듈
                    ├─► D3 Sia 엔드포인트
                    ├─► D4 Extraction
                    └─► D5 Verdict/PI 수정
D5 완료 ─► D6~7 통합 테스트 ─► Week 1 종료 ─► D8 프론트 start
```

Blocking 외부 의존:
- D1 Apify 계약 (파운더 액션, 최소 24h 소요 가정)
- D10 Sia 디자인 승인 (파운더 리뷰)
- D14 프로덕션 배포 승인 (파운더 최종 승인)

---

## Commit Strategy

원칙: 1 커밋 1 논리 단위. 롤백 가능한 granularity.

Week 1 예상 커밋 (backend):
- `feat(db): add user_profiles and conversations tables (Priority 1 D1)`
- `feat(db): add birth_date + ig_handle to users (Priority 1 D1)`
- `feat(ig): Apify scraper service with feature flag (Priority 1 D2)`
- `feat(profile): user profile CRUD service (Priority 1 D2)`
- `feat(sia): conversation endpoints with Redis session (Priority 1 D3)`
- `feat(sia): Haiku 4.5 system prompt + name fallback chain (Priority 1 D3)`
- `feat(sia): Sonnet 4.6 extraction with fallback turns (Priority 1 D4)`
- `feat(verdict): preview/full split with 10-token gating (Priority 1 D5)`
- `feat(pi): migrate input source to user_profile (Priority 1 D5)`
- `test(e2e): onboarding + verdict + pi smoke tests (Priority 1 D6-7)`

Week 2 예상 커밋 (frontend):
- `feat(onboarding): step 0 basics input page (D8)`
- `feat(onboarding): step 1 IG fetching loader (D9)`
- `feat(onboarding): step 2 Sia chat UI with useChat hook (D10)`
- `feat(onboarding): step 3 dashboard with CTAs (D11)`
- `feat(verdict): v2 preview/full UI (D12)`
- `chore(cleanup): remove legacy questionnaire (D13)`
- `test(e2e): staging release checklist (D14)`

---

## Risk Register

| # | Risk | 확률 | 영향 | 대응 |
|---|---|---|---|---|
| R1 | Apify rate limit 도달 | 중 | 중 | Redis Queue + Worker (Priority 2 scale up) |
| R2 | Sia 톤 붕괴 (Haiku 규칙 어김) | 중 | 고 | D3 샘플 검수 게이트 + prompt 강화 반복 |
| R3 | 기존 유저 경험 단절 | 저 | 고 | optional 재온보딩 + 배너 안내 |
| R4 | LLM 비용 예상 초과 | 저 | 중 | 일일 모니터링 + cache 적극 활용 |
| R5 | 대화 중간 이탈율 >30% | 중 | 고 | Q7 QA 트리거 → 프롬프트 즉시 수정 |
| R6 | 대화 세션 복구 불가 (사용자 불만) | 중 | 중 | Priority 2 "이어하기" 기능 |

---

## Success Criteria (Priority 1 완료 기준)

- [ ] DB 마이그레이션 프로덕션 반영 완료
- [ ] 신규 유저 onboarding (Step 0 → Step 3) flow 작동
- [ ] Sia 대화 샘플 10건 수동 검수 통과
- [ ] Verdict 2.0 preview → full 결제 flow 작동
- [ ] PI v2 호환 (user_profile 기반) 검증
- [ ] 기존 questionnaire 라우트 410 Gone (신규 리다이렉트)
- [ ] LLM 비용 <$0.10/유저 실측 확인
- [ ] 프로덕션 배포 승인 완료
