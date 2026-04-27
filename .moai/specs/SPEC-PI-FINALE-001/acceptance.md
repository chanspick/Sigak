---
spec_id: SPEC-PI-FINALE-001
title: Sia Finale — 인수 조건
created: 2026-04-27
status: Planned
---

# 인수 조건 — SPEC-PI-FINALE-001

## Given-When-Then 시나리오

### AC1 — 신규 PI 레포트 생성 시 finale 자동 생성 (E1)

- Given: 유저가 사진 10장 + Sia 대화 + vault 누적 데이터를 보유한다
- When: 유저가 "시각이 본 당신" 첫 1회 무료 또는 50토큰 갱신을 트리거한다
- Then:
  - `_run_analysis_pipeline` Step 10 직전 `generate_finale` 가 정확히 1회 호출된다
  - `DBReport.raw_data["sia_finale"]` 에 6 필드 JSON 이 저장된다
  - 6 필드 글자수가 명세 범위 내(headline ≤50 / lead 200~350 / step1·2 150~250 / step3 200~350 / step4 100~200) 이다
  - 페르소나 B validator 통과 (금지 어미 0개)

### AC2 — 기존 레포트 백필 (E2)

- Given: `sia_finale` 키가 없는 레거시 `DBReport` 가 존재한다
- When: 유저가 `/report/{id}/note` 또는 `/report/{id}/full` 에 진입한다
- Then:
  - 시스템이 `generate_finale` 을 1회 무료 호출한다
  - 결과가 `raw_data["sia_finale"]` 에 영구 저장된다
  - 동일 레포트 재진입 시 Sonnet 미호출 (캐시 히트)
  - 응답에 finale 페이로드 포함

### AC3 — 50토큰 갱신 시 자동 재생성 (E3)

- Given: 유저가 기존 PI 레포트 + finale 보유, 토큰 50개 보유
- When: 유저가 "사진 다시 올려서 갱신하기 · 50토큰" 을 실행한다
- Then:
  - PI 레포트가 새 사진으로 재생성된다
  - `sia_finale` 도 자동 재생성되어 덮어써진다 (별도 토글 없음)
  - 신규 finale 의 `generated_at` 이 갱신된다

### AC4 — `/api/v1/my/reports` 응답 확장 (E4)

- Given: 유저가 1개 이상의 레포트를 보유한다
- When: 클라이언트가 `GET /api/v1/my/reports` 를 호출한다
- Then:
  - 응답 각 항목에 `sia_finale_preview` 객체가 존재한다
  - `headline` 은 ≤50자
  - `lead_paragraph_preview` 는 ≤200자 (lead_paragraph 의 200자 truncate)
  - 4-step 본문은 응답 페이로드에 미포함

### AC5 — `/vision` 탭 Card 1 preview (S1, S2, E5)

- Given: 유저가 `hasReport=true` 상태로 `/vision` 진입
- When: 페이지가 렌더링된다
- Then:
  - 안내 텍스트와 "내 레포트 보기" 버튼이 노출되지 않는다
  - `<FinalePreviewCard>` 가 렌더링된다 (serif headline + lead 2~3줄 truncate + "— sia")
  - 카드 전체 클릭 영역 → `/report/{id}/note` 이동
  - 그 아래 "사진 다시 올려서 갱신하기 · 50토큰" 보조 CTA 가 함께 노출된다

### AC6 — `/report/{id}/note` 단일 CTA (S5, E6, N3, N4)

- Given: 유저가 `/report/{id}/note` 에 진입
- When: 페이지가 렌더링된다
- Then:
  - Hero Card 에 headline (serif 큰 글씨) + lead_paragraph 풀 본문 + "— sia" 가 노출된다
  - 4-step 본문 (관찰/해석/진단/다음 한 걸음) 은 노출되지 않는다
  - 단일 CTA "자세한 분석 보기 →" 만 존재
  - 50토큰 갱신 CTA 가 노출되지 않는다
  - CTA 클릭 → `/report/{id}/full` 이동

### AC7 — `/report/{id}/full` 끝 4-step 카드 (O2)

- Given: 유저가 `/report/{id}/full` 진입
- When: 페이지를 끝까지 스크롤한다
- Then:
  - 기존 PI 섹션이 모두 렌더링된 직후, 공유하기 위에 `<FinaleStepsCard>` 가 노출된다
  - 4 step 블록이 각각 mono 넘버(01~04) + 한국어 헤딩(관찰/해석/진단/다음 한 걸음) + 본문으로 구성된다
  - 디자인 톤은 마케터 1815 (paper / ink / line / ember 토큰) 와 정합한다

### AC8 — 페르소나 B 어미 검증 (U1, N1, S3)

- Given: Sonnet 응답을 검증한다
- When: validator 가 어미를 분석한다
- Then:
  - 금지 어미("~네요/~군요/~같아요/~같습니다/~것 같/~수 있습니다/~더라구요") 0개
  - 호칭 "당신" 일관 (다른 호칭 0개)
  - 위반 시 동일 프롬프트 최대 2회 재시도, 그래도 실패 시 폴백 카피로 응답

### AC9 — 데이터 숫자 비노출 (U4, N2)

- Given: finale 본문이 생성된다
- When: 후처리 검사를 수행한다
- Then:
  - 본문에 좌표 숫자 패턴 (예: `\b0\.\d+`), 8-type 내부 코드, trend_id 가 0건 검출된다

### AC10 — JSON 스키마 + 글자수 검증 (U2, S4)

- Given: Sonnet 응답을 받는다
- When: pydantic `SiaFinale` 으로 파싱한다
- Then:
  - 6 필드 모두 존재
  - 글자수 범위 위반 시 최대 2회 재시도
  - 재시도 모두 실패 시 폴백 카피 사용

### AC11 — 비용/응답시간 (NFR2, NFR3)

- Given: 운영 환경
- When: finale 생성 호출이 발생한다
- Then:
  - P95 ≤ 8초
  - 입력 토큰 ≤ 4K, 출력 토큰 ≤ 1.5K
  - `cost_monitor.py` daily cap 위반 0건

### AC12 — `pi_engine.py` 잠금 보호 (N5)

- Given: 본 SPEC 변경 PR
- When: 코드 변경을 검사한다
- Then:
  - `pi_engine.py` 의 git diff 0줄
  - `sia_writer.py` 가 `pi_engine` 을 import 하지 않음

## 품질 게이트 기준

- 백엔드 신규 코드 라인 단위 테스트 커버리지 ≥ 85%
- finale validator 테스트 100% 통과 (페르소나 B + JSON + 글자수)
- 프론트 새 라우트 (`/report/[id]/note`) E2E 1건 (Playwright 또는 Vitest+RTL)
- TRUST 5: Tested / Readable / Unified / Secured / Trackable 모두 충족
- 페르소나 B 어미 위반 0건 (LIVE probe 5회 샘플 기준)

## 검증 방법과 도구

- 단위 테스트: pytest (`tests/services/test_sia_writer_finale.py`, `tests/routes/test_my_reports_finale_preview.py`, `tests/routes/test_finale_route_backfill.py`)
- 프론트: Vitest + RTL (FinalePreviewCard / FinaleStepsCard)
- 통합: 본인 LIVE probe — 신규 PI 1건 + 백필 1건 + 50토큰 갱신 1건
- 비용 검증: `cost_monitor.py` 로그 + Anthropic dashboard 토큰 카운트 대조
- 톤 검증: 페르소나 B validator 자동 + 본인 육안 5샘플

## Definition of Done

- [ ] `generate_finale` 함수 구현 + 단위 테스트 ≥85% 커버리지
- [ ] `_run_analysis_pipeline` Step 10 직전 호출 통합 + `pi_engine.py` 미수정 확인
- [ ] `DBReport.raw_data["sia_finale"]` 저장 검증 (신규 + 백필 + 갱신 3 케이스)
- [ ] `GET /api/v1/my/reports` 응답에 `sia_finale_preview` 추가
- [ ] `GET /api/v1/reports/{id}/finale` 라우트 + 백필 동작
- [ ] `/vision` 탭 Card 1 preview 교체 + 50토큰 보조 CTA 보존
- [ ] `/report/[id]/note` 신규 라우트 + Hero Card + 단일 CTA (50토큰 CTA 없음)
- [ ] `/report/[id]/full` FinaleStepsCard 추가 (마케터 1815 톤)
- [ ] 페르소나 B validator 통과 (금지 어미 0건)
- [ ] LIVE probe 3건 통과 (신규/백필/갱신)
- [ ] PostHog 이벤트 (`finale_generated`, `finale_retry`, `finale_fallback`) 기록 확인
- [ ] CHANGELOG / docs sync (Phase Sync 단계)
