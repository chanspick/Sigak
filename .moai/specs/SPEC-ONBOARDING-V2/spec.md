---
id: SPEC-ONBOARDING-V2
version: "1.0.0"
status: "planned"
created: "2026-04-21"
updated: "2026-04-21"
author: "chanspick"
priority: "critical"
lifecycle: "spec-anchored"
related:
  - SPEC-COORD-003
supersedes:
  - "questionnaire-v1 (sigak-web/lib/constants/questions.ts)"
  - "onboarding-v1 (sigak/routes/onboarding.py)"
design_doc: ".moai/specs/sigak_v2_onboarding_verdict.md"
---

# SPEC-ONBOARDING-V2: SIGAK v2 Onboarding + Verdict 2.0

## HISTORY

- 2026-04-21: 초안 생성 (approved design doc 기반)

---

## Environment

### 현재 상태 (v1)

- `sigak-web/components/questionnaire/*` (7 컴포넌트, 365 LOC questionnaire-form)
- `sigak-web/app/questionnaire/` (3 라우트)
- `sigak-web/lib/constants/questions.ts` (329 LOC, 3 step × 15+ 필드)
- `sigak/routes/onboarding.py` (187 LOC, 4-step save-step API)
- `users.onboarding_data` JSONB + `users.onboarding_completed` BOOL
- `sigak/pipeline/llm.py::interpret_interview` (hardcoded `[메이크업 레벨]` 필드)
- `sigak/routes/verdicts.py` (699 LOC, 단일 release-blur 로직)
- 토큰 시스템: 10 (Verdict) / 50 (PI) / 30 (Monthly) — 유지
- Apify 계정 미보유

### 목표 상태 (v2)

- 대화형 Onboarding (questionnaire 폐기)
- Sia AI 컨설턴트 (Haiku 4.5 대화 + Sonnet 4.6 extraction)
- IG 피드 자동 수집 (Apify) + 2주 refresh
- Verdict 2.0: preview 무료 + full 10토큰 (판정 30% hook)
- user_profile 영속 저장 (신규 `user_profiles` 테이블)
- Conversation 이력 영속 (신규 `conversations` 테이블)
- 호칭 폴백 3단 (카톡 name → Sia 질문 → 생략)

### 기술 환경

- 백엔드: FastAPI, SQLAlchemy 2.0, PostgreSQL 16 + Alembic, Redis
- 프론트엔드: Next.js 16 (App Router), React 19, TypeScript 5.9+
- LLM: Anthropic SDK (Claude Haiku 4.5 / Sonnet 4.6), prompt caching
- IG 수집: Apify Instagram Profile Scraper Actor (`apify/instagram-scraper`)
- 세션: Redis sliding TTL 5분
- Background worker: FastAPI BackgroundTasks (phase 1) → BullMQ/Celery (scale up)

### 핵심 제약

- **2주 스프린트**: Week 1 backend + Week 2 frontend
- **대화 엔진 톤**: Sia 페르소나 규칙 위반 시 유저 이탈 → 샘플 대화 검수 필수
- **신규 유저만 v2**: 기존 questionnaire 완료 유저는 optional 재온보딩
- **Male 자산 유지**: Phase A 7 커밋 건드리지 않음. Priority 3 후속 재개
- **Q8 보류**: PI CTA 미노출 (Priority 2 A/B 테스트)

---

## Requirements (EARS)

### 1. Onboarding Structured Input (Step 0)

**REQ-ONBD-001** (Ubiquitous):
The system SHALL collect three structured fields at onboarding Step 0:
- `gender` (enum: female / male)
- `birth_date` (date: YYYY-MM-DD)
- `ig_handle` (string: @username, OPTIONAL)

**REQ-ONBD-002** (Event-driven):
WHEN the user submits Step 0 form,
THE system SHALL persist `gender`, `birth_date` to `users` table and `ig_handle` to both `users` and `user_profiles`.

**REQ-ONBD-002a** (Ubiquitous) — D2 contract #1:
THE `user_profiles` row SHALL be created **at Step 0 submission** (not lazy-created later).
This guarantees `gender` and `birth_date` are NOT NULL in `user_profiles` by the time Step 1/2/3 execute.

**REQ-ONBD-003** (Unwanted):
IF `ig_handle` is empty OR `IG_ENABLED=false`,
THEN the system SHALL skip Step 1 IG fetching and proceed directly to Step 2.

---

### 2. IG Feed Collection (Step 1)

**REQ-IG-001** (Event-driven):
WHEN Step 0 is submitted with a non-empty `ig_handle`,
THE system SHALL invoke Apify Instagram Scraper Actor with a 10-second timeout.

**REQ-IG-002** (Ubiquitous):
THE system SHALL persist the Apify response to `user_profiles.ig_feed_cache` JSONB with keys: `current_style_mood`, `style_trajectory`, `feed_highlights`, `profile_basics`, `raw`, `fetched_at`, `scope`.

**REQ-IG-003** (Unwanted):
IF Apify returns `is_private=true`,
THEN the system SHALL persist `scope="public_profile_only"` and populate only `profile_picture`, `bio`, counts (no posts).

**REQ-IG-004** (Unwanted):
IF Apify times out (>10s) OR returns 5xx error,
THEN the system SHALL set `ig_fetch_status="failed"`, skip cache population, and proceed to Step 2 with a non-blocking toast notification.

**REQ-IG-005** (Event-driven):
WHEN `ig_fetched_at + 14 days < now()` AND the user visits the service,
THE system SHALL refresh `ig_feed_cache` in the background without blocking user interaction.

**REQ-IG-006** (State-driven):
WHILE `IG_ENABLED=false`,
THE system SHALL disable the `ig_handle` input field on Step 0 and skip Step 1 entirely.

---

### 3. Sia Conversational AI (Step 2)

**REQ-SIA-001** (Ubiquitous):
THE Sia agent SHALL use Claude Haiku 4.5 for per-turn responses.

**REQ-SIA-002** (Ubiquitous) — 2026-04-22 persona 재작성:
THE Sia system prompt SHALL enforce 서술형 정중체 tone:
  - 어미: "~합니다" / "~습니다" / "~있습니다" / "~인 분입니다" / "~하는 경향이 있습니다"
  - 금지 어미: "~네요", "~같아요", "~거든요", "~이더라고요", "~시더라고요"
  - 유저 단정문: "{NAME}님은 X 인 분입니다" (질문 X, 확인 요청 X)
  - 관찰 → 데이터 숫자 → 해석 → 4지선다 질문 structure
  - 턴당 2-3 sentences (오프닝만 4 허용), sentence ≤35 chars
  - 평가 금지 ("좋아 보입니다", "잘 어울립니다")
  - 시적 비유 금지 ("봄바람 같은")
  - 확인 요청 금지 ("본인도 그렇게 생각하세요?")

**REQ-SIA-002a** (Ubiquitous) — Hard Rules (위반 시 응답 무효):
THE Sia output SHALL contain ZERO occurrences of the following:
  1. "Verdict" / "verdict" (case-insensitive) — 유저 노출은 "피드 분석" 만
  2. "판정"
  3. Markdown syntax: `**`, `*`, `##`, `>`, backtick code fence
  4. Asterisk bullet points (hyphen "-" only)
  5. Emoji (any Unicode emoji range)

**REQ-SIA-002b** (Ubiquitous) — Question format:
THE Sia agent SHALL use 4-option multiple choice as the default question format,
with each option containing concrete situational context (time/place/person/emotion).
ONLY the core fields `desired_image` and `current_concerns` MAY be collected via
short open-ended input (after 4-option framing has already set direction).

**REQ-SIA-002c** (Ubiquitous) — Number grounding:
WHEN the Sia output contains numeric claims (e.g., "피드 38장", "쿨뮤트 68%",
"채도 1.4배"), the numbers SHALL be grounded in actual data from:
  - IG_FEED_SUMMARY (post_count, current_style_mood ratios)
  - Vision analysis of uploaded photos (Verdict context)
  - User selection statistics within the conversation

IF no real data backs a number, THE Sia agent SHALL omit the numeric claim entirely
rather than fabricating. Fabricated numbers = trust collapse (운영 incident).

**REQ-SIA-003** (Event-driven):
WHEN `user.name` contains Korean characters (한글),
THE Sia agent SHALL address the user as "[NAME]님".

**REQ-SIA-004** (Event-driven):
WHEN `user.name` is empty or non-Korean,
THE Sia agent SHALL ask "어떻게 불러드릴까요?" as the first message and persist the user's response to `session_state.resolved_name`.

**REQ-SIA-005** (Event-driven):
WHEN the user has Apple login with null name AND does not respond to the naming question,
THE Sia agent SHALL omit 호칭 and maintain 존댓말 throughout the conversation.

**REQ-SIA-006** (Ubiquitous) — D2 contract #3:
THE conversation session SHALL be stored in Redis (key `sia:session:{conversation_id}`,
sliding TTL 5 minutes reset on each user message) **while active**.
**THE system SHALL NOT write any row to `conversations` DB table during the active phase** —
Redis is the single source of truth for active sessions.

**REQ-SIA-007** (Event-driven) — D2 contract #3:
WHEN the Redis session TTL expires (5-minute idle),
THE system SHALL perform the following atomic sequence:
  1. INSERT new row into `conversations` with `status="ended"`, `messages` = Redis snapshot
  2. Delete Redis session key
  3. Trigger Sonnet extraction in background (REQ-EXT-001)
  4. On extraction success: UPDATE row SET `status="extracted"`, `extraction_result=...`, `extracted_at=NOW()`

**REQ-SIA-008** (Event-driven) — D2 contract #3:
WHEN the user clicks "이만하면 됐어요" OR Sia issues the closing message,
THE system SHALL execute the same atomic sequence as REQ-SIA-007 (end → DB insert → Redis delete → extraction trigger).

**REQ-SIA-009** (Event-driven):
WHEN `turn_count > 50` is reached,
THE Sia agent SHALL proactively ask "이만 정리해드릴까요?" without forcing termination.

---

### 4. Extraction Pipeline

**REQ-EXT-001** (Event-driven):
WHEN a conversation ends,
THE system SHALL invoke Claude Sonnet 4.6 with the full message log to extract structured fields: `desired_image`, `reference_style`, `current_concerns`, `self_perception`, `lifestyle_context`, `height`, `weight`, `shoulder_width`.

**REQ-EXT-002** (Ubiquitous):
THE extraction output SHALL include confidence scores (0.0–1.0) per field; fields with confidence <0.4 SHALL be stored as `null` and added to `fallback_needed` list.

**REQ-EXT-003** (Event-driven):
WHEN required fields (`desired_image`, `height`, `weight`, `shoulder_width`) are missing or null after extraction,
THE Sia agent SHALL ask 1-2 fallback turns before final storage.

**REQ-EXT-004** (Unwanted):
IF Sonnet extraction fails (API error),
THE system SHALL retry once and, on second failure, preserve the conversation for manual re-run and notify operations.

**REQ-EXT-005** (Ubiquitous) — D2 contract #3:
THE extraction result SHALL be persisted in this order:
  1. `conversations.extraction_result` (JSONB) with `status="extracted"`, `extracted_at=NOW()`
  2. `user_profiles.structured_fields` (JSONB) via shallow merge (not replace — existing
     manually-edited fields preserved)
  3. `user_profiles.onboarding_completed = TRUE`

**Status lifecycle** (conversations.status 값 전이):
  - (Redis only — DB row 없음)
  - → INSERT `status="ended"` (대화 종료 시점)
  - → UPDATE `status="extracted"` (Sonnet 성공 시)
  - → UPDATE `status="failed"` (Sonnet 재시도 최종 실패 시)

---

### 5. Verdict 2.0 Preview/Full Split

**REQ-VERDICT-001** (Event-driven):
WHEN the user uploads 3-10 photos at `POST /api/v1/verdicts`,
THE system SHALL generate a free preview (no token charge) containing `hook_line` (≤30 chars) and `reason_summary` (2-3 sentences, ≤30% of judgment reasoning).

**REQ-VERDICT-002** (Ubiquitous):
THE preview SHALL disclose ONLY the judgment conclusion hint and direction of alignment; it SHALL NOT disclose per-photo insights, recommendation details, or specific reasoning.

**REQ-VERDICT-003** (Event-driven):
WHEN the user invokes `POST /api/v1/verdicts/{id}/unlock-full` with sufficient token balance (≥10),
THE system SHALL deduct 10 tokens (idempotency_key = verdict_id), set `full_unlocked=true`, and return `full_content`.

**REQ-VERDICT-004** (Unwanted):
IF the user's token balance <10,
THE unlock-full endpoint SHALL return HTTP 402 with a link to the token purchase page.

**REQ-VERDICT-005** (Event-driven):
WHEN the user fetches `GET /api/v1/verdicts/{id}`,
THE system SHALL return `preview` regardless of unlock state, AND return `full_content` ONLY when `full_unlocked=true`.

---

### 6. PI (Persistent Identity)

**REQ-PI-001** (Ubiquitous):
THE PI engine SHALL consume `user_profile` (gender, structured_fields, ig_feed_cache) as the input interview context.

**REQ-PI-002** (Event-driven):
WHEN the user invokes `POST /api/v1/pi/unlock` with ≥50 tokens,
THE system SHALL charge 50 tokens, generate 9-section report via `format_report_for_frontend(gender, user_profile, ...)`, and persist `pi_report` for permanent access.

**REQ-PI-003** (Ubiquitous):
THE PI report SHALL use the 3-axis coordinate system (shape/volume/age) computed from `user_profile` + primary photo analysis.

---

### 7. User Profile Management

**REQ-PROFILE-001** (Ubiquitous):
THE `user_profiles` table SHALL hold per-user onboarding data with: `gender`, `birth_date`, `ig_handle`, `ig_feed_cache`, `structured_fields`, `onboarding_completed`, timestamps.

**REQ-PROFILE-002** (Event-driven):
WHEN a user invokes `POST /api/v1/user/refresh-ig`,
THE system SHALL force-refresh `ig_feed_cache` regardless of `ig_fetched_at` age.

**REQ-PROFILE-003** (Event-driven):
WHEN a user invokes `POST /api/v1/user/restart-conversation`,
THE system SHALL archive the current `conversations` row (keep readable), create a new `conversations` row, and clear `user_profiles.structured_fields` for re-extraction. No token charge.

**REQ-PROFILE-004** (Ubiquitous):
THE settings page SHALL allow manual editing of `current_concerns`, `height`, `weight`, `shoulder_width` via form inputs.

---

### 8. Legacy Migration

**REQ-MIGRATION-001** (State-driven):
WHILE the v1→v2 transition period is active (2 weeks post-release),
THE system SHALL support both `users.onboarding_data` (read) AND `user_profiles.structured_fields` (read/write) via a dual-read compatibility shim.

**REQ-MIGRATION-002** (Event-driven):
WHEN an existing v1 user (onboarding_completed=true) logs in,
THE system SHALL offer optional re-onboarding via a dashboard banner ("Sia와 대화해보기") but NOT force it.

**REQ-MIGRATION-003** (Event-driven):
WHEN the user accepts re-onboarding,
THE system SHALL preserve `users.onboarding_data` as archive and start fresh v2 flow.

**REQ-MIGRATION-004** (Event-driven) — D2 contract #2:
WHEN a v1 user accepts re-onboarding AND no `user_profiles` row exists yet,
THE system SHALL create the `user_profiles` row by copying `users.gender` into
`user_profiles.gender`. `birth_date` and `ig_handle` are collected fresh in Step 0
(no v1 equivalent exists).

---

### 9. Male Path Compatibility

**REQ-MALE-001** (Ubiquitous):
THE v2 pipeline SHALL preserve all Phase A male commits (fd77c40, 6cb7f59, e9e420a, 9a8453e, 9d7ee13, 90fdc59, 5832a7a) without regression.

**REQ-MALE-002** (Ubiquitous):
THE Sia system prompt SHALL inject `user_profile.gender` and for `gender="male"` SHALL prohibit makeup vocabulary (메이크업/립/블러셔/아이섀도 etc.) in Sia responses.

**REQ-MALE-003** (Ubiquitous):
THE `user_profiles.structured_fields` SHALL NOT contain `makeup_level` field (v2 deletion resolves v1 silent-female-default leak).

**REQ-MALE-004** (Ubiquitous):
THE male UI gate (`start-overlay.tsx:disabled=true` or equivalent) SHALL remain active until Priority 3 male grooming implementation is complete.

---

### 10. Quality & Telemetry

**REQ-QUAL-001** (Event-driven):
WHEN Sia conversation ends,
THE system SHALL log turn count, total duration, idle timeouts, fallback turns, and extraction confidence averages.

**REQ-QUAL-002** (Event-driven):
WHEN conversation abandonment (user leaves mid-session) exceeds 30% rolling 24h average,
THE system SHALL flag the Sia prompt for review (QA trigger per Q7).

**REQ-QUAL-003** (Ubiquitous):
THE system SHALL track per-field extraction confidence; fields below 0.4 confidence SHALL be surfaced in operations dashboard for prompt tuning.

---

### 10-a. SIGAK Naming System (유저 노출 vs 내부 코드)

**REQ-NAMING-001** (Ubiquitous):
THE system SHALL use the following user-facing names in ALL user-visible surfaces
(Sia output, frontend copy, error messages, payment pages, marketing, push notifications):

| 내부 코드 | 유저 노출 이름 |
|---|---|
| Verdict | 피드 분석 |
| PI      | 시각이 본 나 |
| Monthly | 이달의 시각 |
| Onboarding | 시작하기 |

**REQ-NAMING-002** (Ubiquitous):
Internal code, DB table names, API paths, function names SHALL retain the original
naming (`routes/verdicts.py`, `user_profiles`, `pi_report`, etc.) to avoid
developer confusion.

**REQ-NAMING-003** (Ubiquitous):
THE Sia system prompt SHALL explicitly forbid "Verdict" and "판정" vocabulary
(see REQ-SIA-002a Hard Rule #1-2).

**REQ-NAMING-004** (Ubiquitous):
THE Verdict 2.0 LLM prompt SHALL reference the product as "피드 분석" when
addressing the user directly within `hook_line`, `reason_summary`, `verdict`
(full_content), and recommendation text.

---

### 11. Schema Validation (Application Layer)

**REQ-SCHEMA-001** (Ubiquitous) — D2 contract #4:
THE system SHALL validate all JSONB payloads via Pydantic v2 schemas at the
application layer (read AND write paths). DB-level JSONB constraint 은 없으므로
모든 shape 보장은 application 에서 수행.

**REQ-SCHEMA-002** (Ubiquitous):
THE Pydantic schemas SHALL be colocated in `sigak/schemas/user_profile.py` (new module).
Minimum schema set:
  - `StructuredFields` — user_profiles.structured_fields 의 8 필드 + confidence
  - `IgFeedCache` — user_profiles.ig_feed_cache 의 raw + 파싱된 4 필드
  - `ExtractionResult` — conversations.extraction_result (Sonnet 출력)
  - `ConversationMessage` — conversations.messages[] 의 개별 메시지

**REQ-SCHEMA-003** (Event-driven):
WHEN DB row is read for business logic,
THE system SHALL parse JSONB column via Pydantic `.model_validate()` to guarantee shape.

**REQ-SCHEMA-004** (Event-driven):
WHEN writing JSONB,
THE system SHALL construct via Pydantic model then serialize via `.model_dump(mode="json")`
to prevent schema drift.

---

## Out of Scope (Priority 2+)

- PI CTA 카피 최종 결정 (Q8 유보 — Priority 2 A/B 테스트)
- Male grooming 파이프라인 (Priority 3: personal_color male variant, GROOMING_TRENDS_MALE, TREND_MOODS_MALE, report_formatter gender 전파)
- Monthly 재분석 (시계열 비교 리포트, Priority 2+)
- 대화 Resume ("나중에 이어하기") 기능 (Priority 2+)
- Male UI 잠금 해제 (Priority 3 남성 작업 완료 후)
- BullMQ/Celery 전환 (현재 FastAPI BackgroundTasks 로 충분, scale up 시 이전)

---

## References

- Design doc: `.moai/specs/sigak_v2_onboarding_verdict.md`
- Male pipeline audit: `male-pipeline-audit.md`
- 3-axis coordinate SPEC: `.moai/specs/SPEC-COORD-003/`
- Phase A clean rebuild commits: 5832a7a, 90fdc59, 9d7ee13, 9a8453e, e9e420a, 6cb7f59, fd77c40
