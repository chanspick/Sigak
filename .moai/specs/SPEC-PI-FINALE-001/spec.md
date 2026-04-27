---
spec_id: SPEC-PI-FINALE-001
title: Sia Finale — PI 레포트 마무리 한 마디
created: 2026-04-27
status: Planned
priority: High
lifecycle: spec-anchored
related_specs:
  - SPEC-SIA
  - SPEC-COORD-003
  - SPEC-SELFDIAG-002
related_files:
  - sigak/main.py
  - sigak/pipeline/report_formatter.py
  - sigak/services/sia_writer.py
  - sigak/models/db_report.py
  - sigak/routes/my.py
  - sigak-web/app/vision/page.tsx
  - sigak-web/app/report/[id]/note/page.tsx
  - sigak-web/app/report/[id]/full/page.tsx
---

# SPEC-PI-FINALE-001 — Sia Finale

## Environment

- 백엔드: FastAPI (Python 3.11) + Postgres (Railway) + Anthropic Sonnet 4.6
- 프론트: Next.js 16.2 + React 19 + Tailwind 4 + Pretendard/Noto Serif KR
- 활성 PI 파이프라인: `sigak/main.py::_run_analysis_pipeline` → `sigak/pipeline/report_formatter.py::format_report_for_frontend`
- 잠금 영역: `pi_engine.py` (PI v3 잠금) — 본 SPEC 범위 외
- 디자인 톤: 마케터 redesign 1815 (warm 베이지 + #2D2D2D ink + ember 액센트)
- 페르소나: Sia 페르소나 B (간파하는 비서/매니저)

## Assumptions

- PI 레포트 생성 시 8가지 데이터 소스가 이미 메모리에 로드되어 있다 (좌표, 8-type, gap, vault.aspiration_history, verdict history, user_taste_profile.user_original_phrases, action_plan)
- `DBReport.raw_data` 또는 `DBReport.report_data` (JSONB) 컬럼이 존재하므로 신규 alembic migration 없이 finale 저장 가능
- Sonnet 호출 1회 추가 비용은 BETA 기간 무료 정책 하에서 cost_monitor cap 내 흡수 가능
- Next.js App Router 동적 라우트 `/report/[id]/note`, `/report/[id]/full` 신규 추가 가능
- 페르소나 B 어미 검증 룰은 `sigak/services/sia_validators.py` 에 이미 존재

## Requirements (EARS)

### Ubiquitous (시스템 항상)

- U1: 시스템은 모든 Sia Finale 출력에 대해 페르소나 B 어미 규칙(허용/금지 목록)을 항상 검증해야 한다.
- U2: 시스템은 Sia Finale 6 필드 JSON 스키마(headline, lead_paragraph, step_1~4)를 항상 준수해야 한다.
- U3: 시스템은 호칭을 항상 "당신"으로 일관 사용해야 한다.
- U4: 시스템은 데이터 좌표 숫자(예: "0.42")를 finale 본문에 직접 인용하지 않아야 한다.

### Event-driven (WHEN ... THEN)

- E1: WHEN PI 레포트가 신규 생성되면 (`_run_analysis_pipeline` Step 10 직전), THEN 시스템은 Sonnet 1회 호출로 6 필드 JSON 을 생성하고 `DBReport.raw_data["sia_finale"]` 에 저장해야 한다.
- E2: WHEN 유저가 `sia_finale` 이 없는 기존 레포트의 `/report/{id}/note` 또는 `/report/{id}/full` 에 진입하면, THEN 시스템은 자동 백필을 수행 (Sonnet 1회 무료) 하고 결과를 영구 저장한 뒤 응답해야 한다.
- E3: WHEN 유저가 50토큰 갱신 (사진 재업로드) 을 수행하면, THEN 시스템은 PI 레포트와 함께 `sia_finale` 도 자동 재생성하여 덮어써야 한다.
- E4: WHEN `/api/v1/my/reports` 엔드포인트가 호출되면, THEN 시스템은 각 레포트에 대해 `sia_finale_preview` 객체 (`headline`, `lead_paragraph_preview` ≤200자) 를 응답에 포함해야 한다.
- E5: WHEN 유저가 `/vision` 탭에서 Card 1 preview 를 클릭하면, THEN 프론트는 `/report/{id}/note` 로 라우팅해야 한다.
- E6: WHEN `/report/{id}/note` 의 "자세한 분석 보기 →" CTA 가 클릭되면, THEN 프론트는 `/report/{id}/full` 로 라우팅해야 한다.

### State-driven (IF ... THEN)

- S1: IF 유저가 `hasReport=true` 상태로 `/vision` 에 진입하면 THEN 시스템은 안내 텍스트와 "내 레포트 보기" 버튼 대신 Card 1 preview (headline + lead 2~3줄 truncate, 카드 전체 클릭 영역) 를 노출해야 한다.
- S2: IF Card 1 preview 영역이 렌더링 중이면 THEN 시스템은 그 아래에 "사진 다시 올려서 갱신하기 · 50토큰" 보조 CTA 를 항상 함께 노출해야 한다.
- S3: IF 페르소나 B 검증이 실패하면 (금지 어미 1개 이상 또는 호칭 위반) THEN 시스템은 동일 프롬프트로 최대 2회 재시도하고, 그래도 실패하면 안전한 기본 카피로 폴백해야 한다.
- S4: IF Sonnet 응답이 6 필드 JSON 스키마를 위반하면 THEN 시스템은 최대 2회 재시도해야 한다.
- S5: IF `/report/{id}/note` 가 렌더링되면 THEN UI 는 50토큰 갱신 CTA 를 노출하지 않아야 한다 (홈 시각 탭 단일 위치 정책).

### Optional (Where possible)

- O1: 가능하면 시스템은 `user_original_phrases` 중 1개 이하를 `lead_paragraph` 에 자연스럽게 인용하여 "어떻게 알았지" 효과를 강화해야 한다.
- O2: 가능하면 4-step 헤딩에 mono 넘버(01~04)와 한국어 라벨(관찰/해석/진단/다음 한 걸음)을 함께 노출해야 한다.

### Unwanted (시스템은 ~하지 않아야 한다)

- N1: 시스템은 페르소나 A 어미("~네요/~군요/~같아요/~같습니다/~것 같/~수 있습니다/~더라구요") 를 finale 본문에 사용하지 않아야 한다.
- N2: 시스템은 finale 본문에 좌표 수치, 8-type 내부 코드, trend_id 등 내부 식별자를 노출하지 않아야 한다.
- N3: 시스템은 Card 1 preview 에서 4-step 본문(관찰/해석/진단/다음 한 걸음) 을 노출하지 않아야 한다 (full 페이지 전용).
- N4: 시스템은 `/report/{id}/note` 에 50토큰 갱신 CTA 를 노출하지 않아야 한다.
- N5: 시스템은 `pi_engine.py` 모듈을 본 SPEC 범위에서 수정하지 않아야 한다 (PI v3 잠금 보호).

## Specifications

### 백엔드 — finale 생성 흐름

1. `sigak/services/sia_writer.py` 에 `generate_finale(profile, coordinate, type_match, gap, aspiration_history, verdict_history, user_phrases, action_plan) -> SiaFinale` 추가.
2. Sonnet 4.6 호출 1회. 시스템 프롬프트에 페르소나 B 톤 규칙 + 6 필드 JSON 스키마 + "데이터 숫자 인용 금지" 명시.
3. 응답 검증: JSON 스키마 → 페르소나 B validator → 글자수 범위 체크. 실패 시 최대 2회 재시도, 그래도 실패 시 안전 폴백 카피.
4. `_run_analysis_pipeline` Step 10 (format) 직전에 호출. 결과를 `DBReport.raw_data["sia_finale"]` 에 저장.
5. 백필 라우트: `routes/reports.py` 에 `GET /api/v1/reports/{id}/finale` 추가. `sia_finale` 미존재 시 동일 함수로 즉석 생성 후 영구 저장.

### 백엔드 — API 응답 확장

- `GET /api/v1/my/reports` 응답 각 항목에 추가:
  ```json
  "sia_finale_preview": {
    "headline": "<50자>",
    "lead_paragraph_preview": "<lead_paragraph 의 200자 truncate>"
  }
  ```
- 4-step 본문은 본 응답 미포함. `/api/v1/reports/{id}/finale` 에서 풀 페이로드 제공.

### 프론트 — `/vision` 탭 변경

- 기존 `hasReport=true` 분기의 안내 텍스트와 "내 레포트 보기" 버튼 제거.
- 신규 `<FinalePreviewCard>` 컴포넌트: serif headline + lead 2~3줄 truncate + "— sia" 시그. 카드 전체 클릭 → `/report/{id}/note`.
- 그 아래 "사진 다시 올려서 갱신하기 · 50토큰" 보조 CTA 보존 (이 위치에만).

### 프론트 — `/report/[id]/note` (신규)

- TopBar (BackButton + 마케터 시그) + Hero Card.
- Hero Card: serif 큰 글씨 headline + lead_paragraph 풀 본문 + "— sia".
- 단일 하단 CTA: "자세한 분석 보기 →" → `/report/{id}/full`.
- 50토큰 CTA 없음.

### 프론트 — `/report/[id]/full` 변경

- 기존 PI 섹션들 유지.
- 마지막 섹션 (공유하기 위) 에 `<FinaleStepsCard>` 추가:
  - 4 step 블록. 각 블록: mono 넘버(01~04) + 한국어 헤딩(관찰/해석/진단/다음 한 걸음) + 본문.
  - 디자인: 마케터 1815 톤 (warm 베이지 + ink + ember 액센트).

### 데이터 모델

- 신규 alembic migration 불필요.
- `DBReport.raw_data["sia_finale"]` 스키마:
  ```json
  {
    "version": 1,
    "generated_at": "ISO8601",
    "headline": "string ≤50",
    "lead_paragraph": "string 200~350",
    "step_1_observation": "string 150~250",
    "step_2_interpretation": "string 150~250",
    "step_3_diagnosis": "string 200~350",
    "step_4_closing": "string 100~200"
  }
  ```

### 비기능 요구사항

- NFR1 (페르소나 B): finale 본문 어미 검증 통과율 100% (재시도 + 폴백 포함). validator 는 `sia_validators.py` 재사용.
- NFR2 (응답 시간): finale 생성 Sonnet 호출 P95 ≤ 8초. 백필 케이스 동일.
- NFR3 (비용): finale 1회당 Sonnet 토큰 입력 ≤ 4K, 출력 ≤ 1.5K. `cost_monitor.py` daily cap 내 흡수.
- NFR4 (안정성): JSON 스키마 위반 시 최대 2회 재시도, 그래도 실패 시 안전 폴백 카피 (사전 정의).
- NFR5 (관찰성): finale 생성 성공/재시도/폴백 카운터를 PostHog 이벤트로 기록.
- NFR6 (호환성): `pi_engine.py` 미수정. `_run_analysis_pipeline` 변경은 Step 10 전후 1지점만.

## Traceability

- @SPEC:SPEC-PI-FINALE-001 → @CODE:sigak/services/sia_writer.py::generate_finale
- @SPEC:SPEC-PI-FINALE-001 → @CODE:sigak/main.py::_run_analysis_pipeline (finale step)
- @SPEC:SPEC-PI-FINALE-001 → @CODE:sigak/routes/my.py (sia_finale_preview 응답 확장)
- @SPEC:SPEC-PI-FINALE-001 → @CODE:sigak-web/app/vision/page.tsx (FinalePreviewCard)
- @SPEC:SPEC-PI-FINALE-001 → @CODE:sigak-web/app/report/[id]/note/page.tsx (신규)
- @SPEC:SPEC-PI-FINALE-001 → @CODE:sigak-web/app/report/[id]/full/page.tsx (FinaleStepsCard)
- @SPEC:SPEC-PI-FINALE-001 → @TEST:tests/services/test_sia_writer_finale.py
- @SPEC:SPEC-PI-FINALE-001 → @TEST:tests/routes/test_my_reports_finale_preview.py
