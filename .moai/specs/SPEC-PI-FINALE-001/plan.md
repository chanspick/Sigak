---
spec_id: SPEC-PI-FINALE-001
title: Sia Finale — 구현 계획
created: 2026-04-27
status: Planned
---

# 구현 계획 — SPEC-PI-FINALE-001

## 마일스톤 (우선순위 기반)

### Primary Goal — 백엔드 finale 엔진

- `sigak/services/sia_writer.py::generate_finale` 신설 (Sonnet 1회 호출 + 6 필드 JSON + 페르소나 B validator + 재시도 2회 + 폴백 카피)
- 시스템 프롬프트 작성: 페르소나 B 톤 규칙, 어미 허용/금지 목록, 호칭 "당신", 데이터 숫자 인용 금지, 6 필드 스키마, 글자수 범위
- 폴백 카피 사전 정의 (스키마/페르소나 검증 모두 실패 시 사용)
- 단위 테스트: validator pass/fail, 재시도, 폴백 발동, JSON 스키마

### Primary Goal — 파이프라인 통합

- `sigak/main.py::_run_analysis_pipeline` Step 10 직전에 `generate_finale` 호출 추가
- 결과를 `DBReport.raw_data["sia_finale"]` 에 저장
- `pi_engine.py` 잠금 보호: import 금지, 우회 보장
- 통합 테스트: PI 신규 생성 → DB raw_data 에 finale 존재 확인

### Secondary Goal — API 응답 확장

- `sigak/routes/my.py` 의 `GET /api/v1/my/reports` 응답에 `sia_finale_preview` 추가 (lead 200자 truncate)
- 신규 라우트 `GET /api/v1/reports/{id}/finale` — 풀 페이로드 + 백필 트리거
- 백필 흐름: `sia_finale` 미존재 → `generate_finale` 호출 → 영구 저장 → 응답
- 라우트 테스트: 신규/기존(백필)/갱신 케이스

### Secondary Goal — 프론트 라우트 + 컴포넌트

- `sigak-web/components/finale/FinalePreviewCard.tsx` 신설 (serif headline + lead truncate + 시그)
- `sigak-web/app/vision/page.tsx` 의 `hasReport=true` 분기 교체
- `sigak-web/app/report/[id]/note/page.tsx` 신규 라우트 + Hero Card + 단일 CTA
- `sigak-web/components/finale/FinaleStepsCard.tsx` 신설 (4-step + mono 넘버 + 한국어 헤딩)
- `sigak-web/app/report/[id]/full/page.tsx` 마지막 섹션에 FinaleStepsCard 추가
- 토큰: `var(--color-bg-paper)`, `var(--color-ink)`, `var(--color-line)`, `var(--color-ember)` 등 globals.css 그대로 사용

### Final Goal — 백필 + 운영 안전망

- 기존 레포트 첫 진입 자동 백필 검증 (Sonnet 1회 무료, 영구 저장)
- 50토큰 갱신 시 finale 자동 재생성 (덮어쓰기) 검증
- PostHog 이벤트: `finale_generated`, `finale_retry`, `finale_fallback`
- `cost_monitor.py` finale 호출 카운트 반영 검증

### Optional Goal — UX 디테일

- Card 1 preview 의 lead truncate 2~3줄 (line-clamp Tailwind utility)
- Card 1 클릭 영역 카드 전체 (motion-safe hover 미세 lift)
- `/report/{id}/note` Hero serif 글자 크기 모바일 28~32px, 데스크톱 40~48px
- 4-step 헤딩 mono 넘버 ember 컬러 액센트

## 기술 접근

### 백엔드 (Python/FastAPI)

- Sonnet 4.6 호출은 기존 `services/sia_llm.py` 의 anthropic client 재사용
- JSON 응답 파싱: pydantic `SiaFinale` 스키마 (schemas/sia_finale.py 신설)
- 재시도: 데코레이터 또는 명시 루프 (max 2회)
- 폴백 카피: `services/sia_writer.py` 내 상수 `FALLBACK_FINALE` 정의
- 페르소나 B 어미 검증: `sia_validators.py::check_persona_b_endings` 재사용 (없으면 신설)

### 프론트 (Next.js/React)

- App Router 동적 라우트 `/report/[id]/note/page.tsx` 신규
- `/api/v1/reports/{id}/finale` fetch (server component)
- FinalePreviewCard / FinaleStepsCard 는 server component 우선 (인터랙션은 클라이언트 분리)
- 디자인 토큰 마케터 1815 globals.css 그대로 사용

### 데이터

- `DBReport.raw_data` JSONB 컬럼 활용 (alembic migration 불필요)
- 키: `raw_data["sia_finale"]` — 신규 추가만, 기존 키 미변경

## 아키텍처 설계 방향

- finale 생성기는 PI 엔진과 격리 (sia_writer 영역). pi_engine.py import 금지.
- API 응답 분리: 리스트(/my/reports) = preview만 / 상세(/reports/{id}/finale) = 풀 페이로드. 페이로드 비대화 방지.
- 프론트 2 카드 분리: vision Card 1 preview / report note Card 1 hero / report full Card 2 4-step. 각 라우트 단일 책임.
- 백필은 lazy: 진입 시 1회 호출, 영구 저장, 이후 캐시 히트.

## 위험과 대응 계획

| 위험                              | 대응                                                                |
| --------------------------------- | ------------------------------------------------------------------- |
| 페르소나 B 어미 위반 빈발         | 시스템 프롬프트 강화 + validator 재시도 2회 + 폴백 카피             |
| Sonnet 응답 JSON 깨짐             | response_format JSON 모드 + pydantic 검증 + 재시도                  |
| 데이터 숫자 본문 노출 (예 "0.42") | 프롬프트 명시 + 후처리 정규식 검사로 차단                           |
| 백필 동시 다발 호출 (race)        | DB 단일 진입점 (raw_data 조건부 update) + idempotent Sonnet 호출    |
| 비용 cap 초과                     | `cost_monitor.py` daily cap 점검, finale 호출도 카운트 반영         |
| 신규 라우트 권한 누락             | `/report/[id]/note` 도 기존 `/report/[id]/full` 와 동일 인증 가드   |
| pi_engine.py 잠금 침범            | 코드 리뷰 시 import 검사. CI lint 룰 추가 검토                      |
| 마케터 톤 일관성                  | redesign 1815 토큰 (paper / ink / ember / line) globals.css 그대로  |
