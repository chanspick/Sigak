# SIGAK 프로덕트 설계 문서 (통합 최종본)

**버전:** v2.4
**작성:** 2026-04-22 / **갱신:** 2026-04-29 (베타 hotfix v4 revert + v4 Turn Flow Phase A 진입)
**상태:** **최종 퍼블리시 전 디자인/미감 통일 + 디버그 단계.** Phase G~M 코드 완료 → PI v3 (잠금) → **PI Revive Phase B 진행 (B-1~B-8)** + 마케터 redesign 1815 적용 + **Sia v4 Turn Flow Phase A (T1-T5) 환경변수 토글로 stage 진입** (§15 참조)

> 과거 MoAI Execution Directive 는 `CLAUDE.moai.md` 로 보존. 에이전트 규칙은 `.claude/rules/moai/` 유지.

**선행 문서:**
- v1.0 SIGAK_MASTER_DOC.md (프로덕트 전체 구조)
- sia_context_handoff.md (마케터 Sia 인격설계서)
- Claude Code 현 코드베이스 조사 리포트

---

## 0. Executive Summary

### SIGAK 은 무엇인가

SIGAK (시각) 은 **개인의 시각적 정체성을 분석하고, 추구하는 방향으로의 이동을 돕는 AI 기반 미감 분석 서비스** 다. 한국 20-30대 유저 타겟.

### 핵심 가치 제안

> "당신의 피드를 본 AI 가, 당신보다 먼저 당신을 읽습니다."

유저의 Instagram 피드 + 대화 + 업로드 사진을 다각도로 분석하여:

1. **진단:** 유저의 현재 시각적 좌표 (Shape / Volume / Age 3축)
2. **외부 지식:** 성별별 큐레이션된 트렌드와 방법론
3. **맞춤 제안:** 진단 + 외부 지식 결합 실행 가이드

### 6 상품 체계

| 상품 | 가격 | 역할 |
|---|---|---|
| Sia 대화 | 무료 | 온보딩, 유저 프로필 1차 수집 |
| 시각이 본 당신 | ₩5,000 (첫 1회 무료) | 메인 리포트, 사진 25장 스토리 |
| 피드 추천 | ₩1,000 | 현재 피드 판독 (Verdict v2 확장) |
| Best Shot | ₩3,000 | 300장 → A컷 30장 선별 |
| 추구미 분석 (IG) | ₩2,000 | 타인 IG 기반 비교 |
| 추구미 분석 (Pinterest) | ₩2,000 | Pinterest 보드 기반 비교 |
| 이달의 시각 | ₩3,000 | 매달 15일 시계열 변화 |

### 차별화 4개

1. **Sia 페르소나 C** — "겸손한 경력 디자이너 친구" 톤 (2026-04-27 B→C 전환). 통찰 자랑 X, 호기심 + 분석 핀트.
2. **데이터 누적 구조** — 유저가 쓸수록 개인화 정확도 ↑. 락인.
3. **큐레이션 기반 Knowledge Base** — AI 자동 생성이 아닌 사람 큐레이션 트렌드/방법론.
4. **시계열 아카이브** — 유저 미감 변천사 장기 보관. 경쟁사 따라올 수 없는 데이터 자산.

### 현 상태 (2026-04-27 갱신)

**현재 단계:** **최종 퍼블리시 전 디자인/미감 통일 + 디버그**. 신규 기능 동결, 톤·시각·정합·버그 fix 만 진행.

**기 완료 백엔드 (코드 레벨):**
- Phase G 공통 인프라 — CoordinateSystem / UserDataVault / KnowledgeMatcher / SiaWriter
- Phase H Sia v4 — `sia_session_v4.py` / `sia_prompts_v4.py` / `sia_validators_v4.py` + persona-c 전환 (B "간파하는 비서" → C "겸손한 경력 디자이너 친구", 2026-04-27, A-21 자기과시 + A-22 닫힌 어미 hard reject 신설)
- Phase I PI v3 풀 구현 (pi-a~pi-e, 약 8천 라인 + 36 tests) → **5천원 가치 미달 판단으로 잠금** (`PiMaintenance.tsx`) → **옛 SIGAK_V3 풀 부활 (PI Revive)**
- Phase J 추구미 — IG + Pinterest + `aspiration_engine_sonnet.py` cross-analysis + base64 변환 + 429 retry + vault echo
- Phase K Best Shot — 4 런칭 블로커 해소
- Phase L Verdict v2 — best_fit 풀 노출 + **MAX_PHOTOS 5 (was 10)** + **장당 3토큰** + **선결제 흐름 (full_unlocked=TRUE)**
- Phase M Monthly — 스켈레톤 ("준비 중" UI)
- alembic 15 migrations (`20260419` ~ `20260503_pi_v3_baseline_columns`) 모두 작성 완료

**현재 진행 워크스트림 2개:**

🔄 **A. PI Revive Phase B** (vault → LLM context bridge)
- B-1 ✅ vault → LLM context bridge
- B-2/2.5 ✅ face_structure vault_context + 슬라이더 제거
- B-3 ✅ TYPE MATCH WHY / STYLING LLM 동적 생성
- B-4 ✅ vault aspiration_history GAP 카드 노출
- B-5 ✅ 톤 정합 fix (Edition + GAP LLM)
- B-6/6.1 ✅ ReportNav TopBar 정합 + 캐스팅 풀 제거
- B-7/7.1 ✅ Sia 종료 → verdict 강제 + 모바일 갤러리 피커
- B-8 ✅ 로딩 화면 통일 (redesign/로딩_1815.html)

🔄 **B. 마케터 redesign 1815 HTML 12개 적용** (MEMORY.md 4/26 규칙)
- 톱5 완료: ✅ 랜딩 ✅ 프로필 ✅ 충전 ✅ 설정(profile-edit) ✅ 온보딩
- 부수 완료: photo-upload / aspiration / payment / tokens / sia/done / EndConfirmModal / vision-view / change-view / Best Shot 헤드라인 / verdict-v2 (잠금 가이드 + 지배톤)
- 토큰 정합 cleanup: `--color-border` → `--color-line` 28파일 (저번 커밋 `2089f0d`)

**최종 퍼블리시 전 잔여 (디버그/미감):**
- 🟡 디자인 미감 통일 잔여 — 마케터 redesign 톤이 아직 안 닿은 화면 식별 + 적용
- 🟡 PI Revive Phase B 추가 잔여 (B-9 이후 잡힐 수 있음)
- 🟡 디버그 — verdict 429 retry / Pinterest 500 / IG/Pinterest CDN base64 / aspiration photo pair 매핑 / multi-worker stale interview 등 fix 진행 중
- 🟡 4 기능 LIVE probe (본인 결제) — 카피 자연도 + 결제 흐름 검증
- 🟢 KB methodology + references 콘텐츠 — v1.1+ 보류 (마케터 병목)
- 🟢 죽은 코드 정리 (sia_session.py / sia_prompts.py / sia_validators.py / pi.py / verdicts.py — v4 / pi_engine 으로 대체된 v1 잔재)

**컴포넌트 정책 정정 (CLAUDE.md v2.1 오기재 수정):**
- `components/sigak/` = **현역**. `app/page.tsx` 가 VerdictGrid / AspirationGrid / SiteFooter / TopBar 임포트. 폐기 아님.
- `components/pi-v3/PiMaintenance.tsx` = PI v3 잠금 시기 산물. PI Revive 부활 후 미사용 (정리 대상).
- `components/report/sections/` 11개 = B안 (face-structure/skin-analysis/hair-recommendation/celeb-reference/overlay-compare 5개 폐기 예정) 였으나 **PI Revive 가 옛 v3 풀 부활시키면서 재사용 중** — 폐기 보류.

---

## 0.5. 오늘 작업 (2026-04-29)

베타 6/20 부정 피드백 + 친구 베타 후기 ("AI틱 / 관통 X / 외모 정병 조심") 기반 Sia 페르소나 재작업 사이클.

### 작업 1 — 베타 hotfix v4 사이클 (4 commits) → REVERT

페르소나 C → v4 "미감 비서" 전면 재작성 명령서 집행 (5 Phase, 4 commits):

| Phase | Commit | 작업 |
|---|---|---|
| 1 | `827d335` | 페르소나 C 코드 → `_legacy_persona_c/` 격리 + `SIA_V4_MAINTENANCE` 503 게이트 |
| 2 | `076da7a` | base.md v4 본문 (T1-T11 + 5축 + A-30/A-34 + MI 원칙) |
| 3 | `0fe7bfe` | sia_v4_slots.py / sia_v4_lint.py 신규 + 라우터 재배선 (100% 결정성 템플릿) |
| 4 | `f745a3d` | test_sia_v4 8 class / 90 test + 5 fixture 시뮬레이션 |
| **REVERT** | `50d7797` | **전체 롤백 → 페르소나 C 24b7d1b 복귀 (29 files / +324 / -2465)** |

**revert 진앙**:
- 100% 하드코딩 템플릿 + 정규식 슬롯 추출 → 사용자 발화 통째로 박힘
- T2-C [핵심 단어] 3회 반복 → AI 봇 톤
- 사용자 적응 0 (유도리 없음)
- LIVE 노출 시 사용자 분노 트리거 ("야 이게 뭐야 llm한테 자유도 좀 줘서 풀어야지")

### 작업 2 — A-NEW1 / A-NEW2 패치 (`78211ef`)

페르소나 C 인프라 유지하며 두 진앙 보강 (코드 변경 최소, 3 files / +178):
- `prompts/haiku_sia/base.md`:
  - **A-NEW1** 사용자 자가 제시 정보 재질문 금지 (인물/사진/색/스타일 4 카테고리)
  - **A-NEW2** 재대화 분기 (vault block 있으면 "첫 만남이라" 어휘 reject + 항목 인용 + redirection)
- `prompts/haiku_sia/observation.md`: M1 결합 출력 모드에 "M1 재대화 분기" 서브섹션
- `services/sia_prompts_v4.py`: `_format_vault_history_block` 끝에 A-NEW2 트리거 hint 1줄

### 작업 3 — v4 Turn Flow Phase A (`1c2fbd5`)

T1-T5 흐름 의도는 살리되, **본문은 Haiku 자유 생성** 으로 디자인 (15 files / +1011):
- `prompts/haiku_sia/turns/` 신규 8 파일 — T1, T2-A/C, T3-base/norm, T4, T5-A/B
  - 각 파일 = 의도 + INCLUDE + AVOID + 좋은/나쁜 예 (템플릿 X)
- `services/sia_decision.py` `decide_v4` — turn_id 라우팅 (T6+ → None → 페르소나 C fallback)
- `services/sia_flag_extractor.py` `extract_flags_v4` — 3 v4 flag (has_self_doubt / has_uncertainty / vault_present)
- `services/sia_validators_v4.py` `validate_v4_turn` — A-17/A-20/A-18/markdown/A-NEW2 hard reject
- `services/sia_prompts_v4.py` `load_v4_turn_prompt` — base.md + turns/{turn_id}.md + context
- `config.py` `sia_v4_turn_flow: bool = False` (Railway env 토글)
- `routes/sia.py` `_v4_chat_start` / `_v4_chat_message` helpers + chat handler 분기

**안전 장치**:
- 기본 false — `SIA_V4_TURN_FLOW=true` 만 추가하면 v4 진입
- 실패 시 try-except → 페르소나 C 자동 fallback
- T6+ → 페르소나 C 위임 (T1-T5 만 v4 처리)

### 작업 4 — Avatar 통합 (`f132543`)

홈 / 설정 / 피드쉘 공용 아바타 우선순위 (8 files / +243):
- IG 첫 피드 사진 (R2 영구 URL, prefix 검증) → 카카오 프사 fallback
- `routes/auth.py` `MeResponse.feed_avatar_url` 신규
- `sigak-web/hooks/use-avatar.ts` 신규 (마운트 즉시 캐시 + 백그라운드 갱신)

### 다음 단계

1. **Railway env**: `SIA_V4_TURN_FLOW=true` 설정 → LIVE probe (본인 결제)
2. T1-T5 톤 검증 → 좋으면 T6-T11 turn 가이드 추가, 회귀 시 base.md / turns/ 보강
3. 톤 회귀 시 즉시 `SIA_V4_TURN_FLOW=false` 토글 → 페르소나 C 복귀 (코드 변경 X)

---

## 1. Product Vision

### 왜 SIGAK 인가

한국 20-30대는 **시각적 정체성에 대한 수요는 강하지만 도구는 부재한** 상태:

- 기존 뷰티/패션 앱: 트렌드 나열 중심, "나" 가 빠짐
- 퍼스널 컬러 서비스: 일회성 진단, 누적/변화 없음
- 스타일 컨설팅: 비싸고 접근성 낮음

**SIGAK 의 해법:**

1. **AI 가 대신 읽어준다** — IG 피드 분석으로 유저가 말하기 전에 파악
2. **대화로 깊이 들어간다** — Sia 가 유저도 몰랐던 경향을 짚어줌
3. **매달 쌓인다** — 시간의 축적이 상품 가치가 됨

### 유저 여정 (이상적)

**Day 1:** 가입 → Sia 대화 5분 → "시각이 본 당신" 첫 리포트 → 30 토큰 지급으로 추구미/피드 추천 체험 → "얘 뭔데 나 알아?" 호감 획득

**Day 2-14:** 여러 추구미 반복 분석 / 중요 사진 업로드 시 Best Shot / 매번 유저 프로필 데이터 누적

**Day 15:** 이달의 시각 첫 알림

**Day 30+:** 매달 이달의 시각 정기 이용 / 필요 시 PI 재생성 (데이터 축적으로 더 정교) / SIGAK = 개인 미감 아카이브

### SIGAK 이 되고 싶지 않은 것

- 단순 퍼스널 컬러 진단기
- 챗봇 쇼핑 도우미
- AI 패션 추천 엔진 (자동화 중심)
- 매거진/블로그 (정보 제공만)

### SIGAK 이 되고 싶은 것

- "AI 와 사람이 함께 만드는 개인 미감 연구실"
- 유저 개인 시각적 변천사를 유일하게 기록하는 곳
- 정보 + 진단 + 실행 통합 유료 정보 상품

---

## 2. 현 코드베이스 상태 (실측, 2026-04-22)

### 스택

- **백엔드:** Python 3.11 + FastAPI / Postgres (Railway) / Cloudflare R2 (예정) / Anthropic API (Sonnet 4.6 + Haiku 4.5) / Apify
- **프론트엔드:** Next.js 16.2.2 / React 19.2.4 / TypeScript 5 / Tailwind 4 / Pretendard + Noto Serif KR / Capacitor / Toss Payments SDK / PostHog / Vitest 2.1.9 + RTL + happy-dom / pnpm 10.33.0

### 백엔드 완료 모듈 (line count)

```
services/
├── verdict_v2.py        434 lines  (Sonnet Vision 풀 완성)
├── sia_llm.py           563 lines
├── sia_session.py       449 lines
├── sia_prompts.py       417 lines
├── ig_scraper.py        408 lines
├── ig_feed_analyzer.py  336 lines  (Phase A IgFeedAnalysis)
├── sia_validators.py    321 lines  (11 violation 체크)
└── tokens.py            197 lines  (3팩 + idempotent credit)

routes/
├── sia.py               507 lines  (start/message/end)
└── verdict_v2.py        392 lines  (create/unlock/get)

Total:
- Sia v3 파이프라인: ~2,275 lines
- Verdict v2: ~826 lines
- Tokens: 197 lines
```

### Phase A-F 요약 (Sia 대화)

- **Phase A**: IG Vision 파이프라인 (IgFeedAnalysis 9 필드, Refresh delta≥3)
- **Phase B**: Validator 11종 + Redis dual-write + spectrum 파싱 + 15 turn type
- **Phase C**: 화이트리스트 16 (여8/남8, 페르소나 A — B로 재작성 필요) / turn block 15 / SELF_CHECK 6체크
- **Phase D/E/F**: 416 tests green, Live Haiku probe 11/12 clean

### 현재 연결 상태

| 영역 | 백엔드 | 프론트 | 상태 |
|---|---|---|---|
| Verdict v2 | 완비 | E2E 연결 | ✅ |
| Sia 대화 엔진 | Phase A-F | 컴포넌트만 정적 포팅 | ⚠️ API 연결 미완 (D7) |
| PI 리포트 | placeholder | UI 12 섹션 완비 | ⚠️ 백엔드 공백 |
| Onboarding | /api/v2/onboarding | /onboarding/* | ✅ |
| 토큰/결제 | tokens.py + /payments | /tokens + /payment | ✅ |
| 레거시 sigak | /api/v1/sigak | /components/sigak | ✅ (폐기 예정) |

### 핵심 불일치 3건

1. **Sia 프론트 ↔ 백엔드 API 연결 미완** (D7 스코프)
2. **PI 프론트 UI 완비, 백엔드 placeholder** (프론트 재활용 B안 확정)
3. **Phase C 신규 파라미터 라우트 미전달** — `routes/sia.py:165` 에서 `build_system_prompt` 호출 시 turn_type/gender 미전달, default "opening"/"female" 로 고정 호출됨 (Phase G 에 포함)

### 테스트 현황

- Backend pytest: 416 tests all green
- Frontend Vitest: 13 tests all green (Sia components only)

---

## 3. 6 상품 정의

### 3.1 Sia 대화 (온보딩, 무료)

**역할:** 유저 진입점. 프로필 1차 수집.

**INPUT:** gender / birth_date / 본인 IG 핸들 + 대화 주관식 답변 (100%)

**OUTPUT:** Vision 4 필드 (IgFeedAnalysis) + 대화 수집 필드 (Shape/Volume/Age 3축 좌표 + external_data 4 + desired_image)

**구조:**
- 5분 Soft 제한
- 메시지 단위 주고받음
- **100% 주관식** — Haiku 가 답변 파싱해서 필드 추출
- 상단 진행도 바 + 카운트다운
- JSON 100% 완성 시 자동 CLOSING (5분 전이라도)
- 5:00 도달 시 현재 답변 완료 후 클로징 (Soft)

**유저 반응 목표:** "얘 뭔데 어떻게 알아?"

**메시지 타입 10개** (마케터 문서 기반):
1. OBSERVATION — Vision 관찰 선언
2. INTERPRETATION — 관찰 → 해석
3. DIAGNOSIS — 재프레임 진단 (Sia 무기)
4. PROBE — 가볍게 확인 질문
5. CONFRONTATION — 반박 회복 + 재프레임
6. EXTRACTION — 외적 정보 수집 (주관식 유지)
7. CLOSING — 종료 신호
8. CONTRADICTION — Vision vs 유저 발언 모순
9. EMPATHY_MIRROR — 짧은 공감 + 요약
10. POSITIVE_PIVOT — 부정 영역 → 긍정 전환

**4단 리듬** (Sia 고유):
```
M1: OBSERVATION (Vision 근거, 관찰 선언)
M2: INTERPRETATION (관찰 해석)
[유저 반응 대기]
M3: EMPATHY_MIRROR 또는 PROBE
```

OBSERVATION 이 맨 앞 = "어떻게 알아?" 감각의 핵심.

### 3.2 시각이 본 당신 (₩5,000 / 50 토큰, 첫 1회 무료)

**역할:** 메인 리포트. SIGAK 의 얼굴.

**INPUT:** 유저 profile (Vision + 대화 + 누적 이력) + 본인 IG 피드 사진 10장

**OUTPUT:**
- 사진 25장 선별 (공개 5 + 잠금 20)
- 각 사진 Sia 한 줄 해석
- boundary_message (공개/잠금 경계 안내)
- 종합 Sia 메시지
- Knowledge Base 기반 트렌드/방법론 (잠금 영역)
- 3축 좌표 (Shape/Volume/Age) 시각화

**구조:**
- 공개 5장: 폰 한 화면 그리드 + Sia 해석
- 잠금 20장: 추가 결제 시 해금
- 버전 관리: 재생성마다 v2, v3... 데이터 누적 반영
- 영구 보관

**재생성 가격:** 50 토큰

### 3.3 피드 추천 (Verdict v2, ₩1,000 / 10 토큰)

**역할:** 현재 피드 판독.
**현 상태:** 풀 E2E 완성. Knowledge Base 통합만 추가 필요.

**INPUT 확장:** 유저 현 IG 피드 (재수집) + 유저 profile (누적) + **Knowledge Base 트렌드 (신규)** + **UserTasteProfile (신규)**

**OUTPUT:** 기존 구조 유지 + 트렌드 매칭 보강

**구현:** `build_verdict_v2` 시그니처에 `matched_trends`, `taste_profile` 파라미터 추가. 최소 침습. (옵션 a 확정)

### 3.4 Best Shot (₩3,000 / 30 토큰)

**역할:** 유저 올릴 사진 고민 해결.

**INPUT:** 유저 업로드 최대 300장 + 유저 profile (누적) + Knowledge Base 트렌드

**OUTPUT:** A컷 30장 선별 + 각 사진 Sia 해석 + 트렌드 호환도 (★)

**구조:**
- 시각이 본 당신 + 피드 추천 경험 여부 = 선택적 조건 (MVP 정책 미확정)
- 업로드 원본 24h TTL
- 선별 결과 30일 보관
- 비용 최적화: Sonnet 대신 Haiku 4.5 Vision 검토

### 3.5 추구미 분석 IG (₩2,000 / 20 토큰)

**역할:** 유저 따라가고 싶은 사람 분석 + 갭 비교.

**INPUT:** 제3자 IG 핸들 + 유저 본인 피드 (vault)

**OUTPUT:** 본인 vs 추구미 비교 리포트 + 좌우 이미지 병치 (3-5쌍) + 각 쌍 Sia 한 줄 + 갭 벡터 + 이동 방향 + 삼각형 레이더 보조

**구조:** Apify 로 대상 IG 수집 / Phase A Vision 재사용 / 반복 구매 가능 / vault 누적

**저작권:** 이용약관 "공개 계정 1차 동의 간주". 대상자 삭제 요청 즉시 처리.

### 3.6 추구미 분석 Pinterest (₩2,000 / 20 토큰)

**역할:** 유저 큐레이션 보드 분석.
**INPUT:** Pinterest 보드 URL
**OUTPUT:** IG 와 동일 구조
**구조:** Apify URL 기반 (OAuth 미사용) / 분석 방식 IG 동일

### 3.7 이달의 시각 (₩3,000 / 30 토큰)

**역할:** 시계열 변화 리포트.
**INPUT:** 유저 전체 누적 데이터
**OUTPUT:** 지난달 대비 변화 중심 리포트
**구조:** 매달 15일 자동 알림 / 유저 선택 시 해당 월 리포트 생성 / 월 1회 반복 구매

**MVP:** 스켈레톤만 (스케줄러 스텁 + "준비 중"). 실 엔진은 v1.1+

---

## 4. 공통 인프라 설계

### 4.1 레이어 구조

```
┌─────────────────────────────────────────┐
│ Products (유저 노출)                     │
│  Sia 대화 / 시각이 본 당신 / 피드 추천    │
│  Best Shot / 추구미 IG / 추구미 Pinterest│
│  이달의 시각                             │
├─────────────────────────────────────────┤
│ Engine Layer (상품별 로직)               │
│  ConversationEngine / PIReportEngine    │
│  VerdictEngine / BestShotEngine         │
│  AspirationEngine (IG/Pinterest)        │
│  MonthlyEngine                          │
├─────────────────────────────────────────┤
│ Shared Services (공통 추상화)             │
│  UserDataVault / UserTasteProfile       │
│  CoordinateSystem (Shape/Volume/Age)    │
│  KnowledgeBase / KnowledgeMatcher       │
│  VisionService / SiaWriter              │
├─────────────────────────────────────────┤
│ Infrastructure                          │
│  Postgres / R2 / Anthropic / Apify      │
└─────────────────────────────────────────┘
```

### 4.2 UserDataVault

```python
class UserDataVault(BaseModel):
    user_id: str
    basic_info: UserBasicInfo  # gender, birth_date, ig_handle, name

    conversation_state: ConversationState  # Sia 대화 수집
    feed_snapshots: list[IgFeedSnapshot]  # 옵션 2 — 영구 저장
    aspiration_history: list[AspirationAnalysis]
    best_shot_history: list[BestShotSession]
    verdict_history: list[VerdictSession]
    pi_versions: list[PIReport]
    monthly_reports: list[MonthlyReport]

    def get_user_taste_profile(self) -> UserTasteProfile: ...
```

### 4.3 UserTasteProfile

6 상품 공유 유저 취향 객체.

```python
class UserTasteProfile(BaseModel):
    user_id: str
    snapshot_at: datetime

    current_position: Optional[VisualCoordinate]
    aspiration_vector: Optional[GapVector]

    preference_evidence: list[PhotoReference]
    conversation_signals: ConversationSignals
    trajectory: list[TrajectoryPoint]

    user_original_phrases: list[str]

    def strength_score(self) -> float:
        """0.0 (Day 1) ~ 1.0 (풀 데이터)"""
        ...
```

### 4.4 CoordinateSystem (Shape/Volume/Age 3축)

**Shape / Volume / Age** (원래 PI 최종본 확정).

```python
AxisName = Literal["shape", "volume", "age"]

class VisualCoordinate(BaseModel):
    shape: float   # 0=소프트/둥근, 1=샤프/각진
    volume: float  # 0=평면, 1=입체
    age: float     # 0=베이비/프레시, 1=매추어/성숙

    def distance_to(self, other) -> float: ...
    def gap_vector(self, target) -> GapVector: ...

class GapVector(BaseModel):
    primary_axis: AxisName
    primary_delta: float
    secondary_axis: AxisName
    secondary_delta: float

    def narrative(self) -> str: ...
```

**좌표 산출:** Haiku 가 대화 중 매 메시지마다 축별 delta 추출 → 누적.

### 4.5 KnowledgeBase (외부 지식 레이어)

**SIGAK 의 유료 정보 상품 가치 핵심.** 본인/마케터 큐레이션 기반.

```
services/knowledge_base/
├── trends/
│   ├── female/2026_spring.yaml
│   └── male/2026_spring.yaml
├── methodology/
│   ├── female/{makeup_basics, styling, color_theory}.yaml
│   └── male/{grooming_basics, styling}.yaml
└── references/
    ├── female_celebs/
    └── male_celebs/
```

**트렌드 포맷:**
```yaml
trend_id: female_2026_spring_001
season: 2026_spring
gender: female
category: color_palette
title: "민트 + 크림 조합"
compatible_coordinates:
  shape: [0.3, 0.7]
  volume: [0.4, 0.6]
  age: [0.2, 0.5]
action_hints: [...]
detailed_guide: |
  ...
```

### 4.6 KnowledgeMatcher

```python
def match_trends_for_user(
    profile: UserTasteProfile,
    gender: str,
    season: Optional[str] = None,
) -> list[MatchedTrend]: ...
```

### 4.7 SiaWriter (페르소나 C 공통)

```python
class SiaWriter:
    async def generate_comment_for_photo(photo, profile, context) -> str: ...
    async def generate_overall_message(profile, context) -> str: ...
    def render_boundary_message(vault_state) -> str: ...
```

### 4.8 VisionService

Phase A 자산 확장.

```python
class VisionService:
    async def analyze_ig_feed(handle) -> IgFeedAnalysis: ...
    async def analyze_pinterest_board(url) -> IgFeedAnalysis: ...
    async def analyze_uploaded_photos(photos) -> list[PhotoAnalysis]: ...
```

---

## 5. 상품별 파이프라인

(이하 섹션 5-16 은 본 문서 원본 v2.0 내용 유지 — 길이 문제로 요약. 구체 구현 시점에 직접 참조.)

### 5.1 시각이 본 당신 (PI) — Phase I

**현 상태:** placeholder. 재작성 필요.

**파이프라인:** 토큰 차감 → UserDataVault 로드 → UserTasteProfile.compose() → 사진 25장 선별 (Sonnet Vision) → Sia 해석 생성 (SiaWriter, Haiku 배치) → Knowledge Base 매칭 → boundary_message 동적 생성 → PIReport 저장 (versioned)

**DB 변경:** `pi_reports` PRIMARY KEY: `user_id` → `report_id` + `version` 컬럼 + `is_current` BOOLEAN

### 5.2 피드 추천 (Verdict v2 확장) — Phase L

**변경:** `build_verdict_v2(..., matched_trends, taste_profile)` 최소 침습 확장. 기존 JSON 출력 스키마 유지. 프론트 변경 최소.

### 5.3 Best Shot — Phase K

300장 업로드 → R2 임시 (24h) → 1차 필터 (품질) → 2차 점수 (profile Vision) → Knowledge Base 호환 → 상위 30 + Sia 해석

**비용:** Sonnet 300장 = $0.9. Haiku 4.5 대체 or 1차 필터 후 Sonnet 정밀 선별 검토.

### 5.4 추구미 분석 IG — Phase J

핸들 입력 → 블록리스트 체크 → Apify 수집 (공개 확인) → Vision → 좌표 비교 + GapVector → Knowledge Base 매칭 → 좌우 병치 사진 쌍 (3-5) → Sia 종합 → R2 저장 + vault 누적

### 5.5 추구미 분석 Pinterest — Phase J

IG 와 동일. Apify Pinterest 스크래퍼 / 대상 = 이미지 큐레이션 (사람 아님) / "유저가 좋아하는 이미지들의 공통 결" 추출

### 5.6 이달의 시각 — Phase M (MVP 스켈레톤)

홈 카드 + "매월 15일에 자동 준비" / 스케줄러 스텁 / DB 스키마. v1.1+ 실 엔진.

---

## 6. Sia 페르소나 & 대화 UX

### 6.1 페르소나 C (현, 2026-04-27 전환)

| | A (폐기) | B (폐기, 4/27) | **C (현)** |
|---|---|---|---|
| 포지션 | 감도 날카로운 분석가 | 간파하는 친근 비서 | **겸손한 경력 디자이너 친구** |
| 정체성 핵심 | 정중체 분석가 | 자신감 있는 통찰 자랑 | **본 게 있지만 떠벌리지 않음. 유저 이야기 다 저장하겠다는 호기심.** |
| 어조 | "~합니다/~분이십니다" | "~가봐요?/~이신 것 같은데" | "~어요/~예요" + 열린 질문 ("~어떤 순간이에요?") |
| 무기 | 카테고라이징 | 추정 반문 (`~가봐요?`) | **"이건 좀 다른데요?? 어떻게 생각하세요?"** 부드러운 challenge |
| 유저 반응 (의도) | "어 맞는데" | "어 맞아 어떻게 알았지" | **"내 이야기 들어준다 / 같이 보고 있다"** |
| 유저 반응 (실측 실패) | 정중체 거리감 | "잘못 번역된 MBTI 검사 느낌" / "MZ 사원 자존심" | — |

**전환 이유:** 페르소나 B 의 "어떻게 알았지?" 효과를 노린 어미 (`~가봐요?`, `~이시잖아요?`, `~한 편이세요?`) 가 소비자 FGI 에서 **"맞추려고 한다 / MBTI 검사 / MZ 사원이 자존심 부리는 말투"** 로 체감됨. 통찰 자랑 인격 폐기 + 호기심 인격 채택.

**페르소나 C 5원칙 (HARD):**

1. **유저 발화 반사가 먼저** — 모든 메시지는 유저 직전 발화의 단어/표현 반사로 시작.
2. **자기과시·자존심 톤 금지 (A-21)** — "직설적으로 ~", "사실은 ~인 거", "제가 보기엔", "본질은 ~", "분명히/확실히" hard reject.
3. **분석 핀트 + 열린 질문 (A-22)** — `[유저 원어 반사] + [구체 관찰] + [열린 질문]` 3단 구조 강제. 닫힌 어미 hard reject.
4. **부드러운 challenge** — 모순 발견 시 단정 confront 폐기. "이건 좀 다른데요?? 어떻게 생각하세요?" 패턴.
5. **발화 최소화** — 1-2문장. 200자 초과 hard reject. 유저가 말 많이 하게.

### 6.2 어미 규칙 (페르소나 C, 2026-04-27)

**허용 (자주 쓸 것):**
- `~어요` / `~예요` — 평서 기본. 담담한 진술.
- `~어떤 순간이에요?` / `~어떻게 일어나요?` / `~어떻게 풀어요?` — 열린 질문.
- `~좀 더 풀어주실래요?` / `~이 부분 풀어주실래요?` — 정보 요청.
- `~이건 좀 다른데요?? 어떻게 생각하세요?` — 부드러운 challenge.
- `~잘 모르겠어서요` / `~궁금해서요` — 호기심 표시 (자기 무지 인정).

**금지 (HARD reject):**

A. 닫힌 어미 (네/아니오 답 가능 — A-22 validator 차단):
- `~세요?` / `~이세요?` / `~인가요?`
- `~한 편이세요?` / `~한 편이신가요?` (카테고라이징 — MBTI 톤 핵심)
- `~이시잖아요?` / `~이신 거잖아요?` / `~잖아요?` (닫힌 동의 유도)
- `~가봐요?` / `~이신가봐요?` (추정 반문 — B 무기)
- `~이신 것 같은데` / `~이신 것 같` (단정 추측)
- `~으시죠?` / `~시죠?` (동의 강요)

B. 흐릿한 단정 (A-1):
- `~네요` / `~군요` / `~같아요` / `~같습니다` / `~것 같` / `~수 있습니다`

C. 사족·어색 종결:
- `~더라구요` (4/27 폐기 — 소비자 피드백)
- `~면요` 단독 / `~이긴 한데요` 불완전 / `~인 셈이죠`

D. 자기과시 (A-21 신설):
- "직설적으로 말씀드릴게요" / "솔직히 말해서"
- "사실은 ~인 거" / "본질은 ~" / "본질이 ~"
- "제가 보기엔 ~" / "제가 본 바"
- "분명히 ~" / "확실히 ~" / "명백히 ~"
- "그게 핵심이에요"

**변경 이력:**
- v2.1 (4/25) `~더라구요` 허용 → v2.2 (4/27) 폐기 (소비자 피드백)
- v2.3 (4/27) **페르소나 B → C 전환**. 닫힌 어미 7종 hard reject (A-22) + 자기과시 어휘 hard reject (A-21) 신설. 4단 리듬 M1 OBSERVATION 톤 약화 (관찰 선언 → 담담한 진술 + 풀어달라). 인격 단정 2회 → 0회. 발화 길이 3문장 → 2문장. 자세한 규칙은 `sigak/prompts/haiku_sia/base.md` 참조.

### 6.3 환상 유지

Sia 는 오직 "이미지로부터 읽었다" 포지션. 댓글/타인 증언 0건. Vision 이 댓글도 받지만 유저 앞에선 "이미지만 본 AI".

### 6.4-6.13 (메시지 타입 / 4단 리듬 / 오프닝 / CONFRONTATION / 종료 / 5분 제한 / 100% 주관식 / 대화 샘플 / 온보딩 / 온보딩 직후)

(원본 문서 섹션 6.4-6.13 유지 — Phase H 착수 시 상세 참조)

**핵심:**
- 100% 주관식 (선택지 UI 완전 폐기)
- Haiku 1회 호출 = Sia 응답 + 구조화 추출 JSON (방법 B)
- 진행도 바 = JSON 수집률 (시간 아님)
- JSON 100% OR 5:00 자동 CLOSING

---

## 7. 리포트 구조

### 7.1 시각이 본 당신 — 25장 스토리

- 공개 5장: 폰 한 화면 그리드 + Sia 해석 + 경계 카드 + 전체 열람 CTA
- 잠금 20장 카테고리: `signature` (공개 5) / `detail_analysis` / `aspiration_gap` / `weaker_angle` / `style_element` / `trend_match` / `methodology`

### 7.2 아이작 M REPORT 패턴 (7페이지 오프닝)

P1 요약 → P2 니즈 → P3 좌표계 → P4-5 공개 5장 → P6 경계 → P7 분량 + 잠금 CTA

**7 원칙:**
- R1: 1-2p desired_image+concerns 요약+니즈 선언
- R2: user_original_phrases[] state 필수
- R3: 3축 좌표계 공통 언어
- R4: 역순 공개 (TOP 3 → 1) trade-off
- R5: 심화 분석 1등 근거 강화
- R6: "25장 / 10+ 관찰 / 3-5 트렌드" 분량
- R7: 대화 `~더라구요` 제거, 리포트 `~있어요/세요` 유지

### 7.3 PIReport 스키마

```python
class PIReport(BaseModel):
    report_id: str
    user_id: str
    version: int
    is_current: bool

    public_photos: list[PhotoInsight]  # 5장
    locked_photos: list[PhotoInsight]  # 20장

    user_taste_profile: dict  # snapshot
    boundary_message: str
    sia_overall_message: str

    matched_trends: list[str]
    matched_methodologies: list[str]
    matched_references: list[str]

    user_summary: str         # P1
    needs_statement: str      # P2
    user_original_phrases: list[str]

    data_sources_used: PIReportSources
```

### 7.4 추구미 비교 리포트

좌우 병치 사진 쌍 + 삼각형 레이더 + 갭 분석 + Knowledge Base 매칭 + 방법론

**프론트 재활용:** coordinate-map.tsx / gap-analysis.tsx

---

## 8. UI/UX 원칙

### 8.1 홈 IA

- 상단: 토큰 잔량 (원 단위) + 누적 배지 ("피드 10장 · 대화 12개 · 추구미 0회")
- 메인: 시각이 본 당신 (큰 카드) + 4상품 그리드 + 이달의 시각 (매달 15일)
- 하단: 토큰 구매 CTA + 약관/고객센터

### 8.2-8.6

카톡식 말풍선 / SiaChoices 폐기 / SiaInputDock 만 / 로딩 슬라이드 5장 / 상품 카드 / PI 리포트 화면 / 추구미 비교 화면

---

## 9. 데이터 저장 정책

### 9.1 Postgres

```
users / token_balances / token_transactions
conversations / user_profiles / feed_snapshots
aspiration_analyses / best_shot_sessions
verdict_sessions / pi_reports (migration)
monthly_reports (v1.1+)
aspiration_target_blocklist
```

### 9.2 R2 레이아웃

```
/users/{user_id}/
├── feed_snapshots/{snapshot_id}/ (영구)
├── aspiration_targets/instagram/{handle}_{ts}/ (영구)
├── aspiration_targets/pinterest/{board_hash}_{ts}/ (영구)
├── pi_reports/{report_id}/public_photo_{rank}.jpg / locked_photo_{rank}.jpg
└── best_shot/uploads/{session_id}/ (24h) · selected/{session_id}/ (30일)
```

### 9.3 보관 정책

유저 본인 피드 영구 / 추구미 원본 영구 / PI 사진 영구 / Best Shot 업로드 24h / 선별 30일

### 9.4 삭제 정책

유저 탈퇴 전수 삭제 / 대상자 요청 7일 내 + 블록리스트 / 유저 특정 분석 삭제 요청 즉시

---

## 10. 토큰 시스템

### 10.1 가격 체계 (6 상품)

| 상품 | 토큰 | 가격 |
|---|---|---|
| 시각이 본 당신 (재생성) | 50 | ₩5,000 |
| 시각이 본 당신 (첫 1회) | 0 | 무료 |
| 피드 추천 | 10 | ₩1,000 |
| Best Shot | 30 | ₩3,000 |
| 추구미 분석 IG | 20 | ₩2,000 |
| 추구미 분석 Pinterest | 20 | ₩2,000 |
| 이달의 시각 | 30 | ₩3,000 |

**1 토큰 = ₩100**

### 10.2-10.4

구매 팩 (STARTER 10K/100 · REGULAR 25K/280 · PRO 50K/600) / 가입 지급 30 토큰 30일 만료 / Idempotency 패턴 재사용

**COST_* 상수 신규 (Phase G):**
```python
COST_ASPIRATION_IG = 20
COST_ASPIRATION_PINTEREST = 20
COST_BEST_SHOT = 30
```

**Idempotency key 패턴:**
```
f"pi_regenerate:{user_id}:{version}"
f"verdict:{user_id}:{session_id}"      # 기존
f"best_shot:{user_id}:{upload_session_id}"
f"aspiration_ig:{user_id}:{target}:{timestamp}"
f"aspiration_pinterest:{user_id}:{board_hash}:{timestamp}"
f"monthly:{user_id}:{year_month}"
```

---

## 11. 법적 / 개인정보

이용약관 "공개 계정 1차 동의 간주" / 대상자 삭제 요청 7일 내 + 블록리스트 영구 / 유저 책임 전가 / Apify 재배포 / MVP 규모 감수.

---

## 12. 구 PI vs 신 구조 매핑

### 12.1 3축 좌표계 — Shape/Volume/Age 확정

**impression/tone/mood (내가 잘못 가정) 폐기. Shape/Volume/Age 유지 (원래 PI 최종본).**

- **Shape** — 얼굴형/실루엣
- **Volume** — 부피감/입체감
- **Age** — 인상 성숙도

### 12.2 구 PI 요소 재분배

| 구 PI 요소 | 신 배정 |
|---|---|
| Shape/Volume/Age 3축 | 공통 인프라 (CoordinateSystem) |
| MediaPipe 얼굴 메트릭 | v1.1+ 검토 (Sonnet Vision 우선) |
| 피부톤 LAB 분석 | 폐기 (페르소나 톤 충돌) |
| 갭 분석 벡터 | 추구미 분석 엔진 |
| 셀럽 레퍼런스 | Knowledge Base (v1.1+) |
| 얼굴 오버레이 | 폐기 (25장 스토리와 중복) |
| 컬러 팔레트 hex | PI 잠금 20장 보조 (style_element) |
| 삼각형 레이더 | 추구미 분석 UI 보조 |
| 6섹션 Claude 리포트 | 폐기 (25장 스토리로 대체) |
| 블러 페이월 3-tier | 폐기 (공개 5 + 잠금 20 단순화) |

### 12.4 프론트 컴포넌트 처리 (2026-04-27 갱신 — v2.1 B안 폐기)

**v2.1 의 B안 (재활용 5 / 폐기 5) 은 PI Revive 로 무효화됨.** 옛 SIGAK_V3 풀 부활 (`df8d43b`) 로 face-structure / skin-analysis / hair-recommendation / overlay-compare 모두 재사용 중. celeb-reference 만 실 폐기 (`bebf996` celeb 폐기).

**현 정책:**
- `components/report/sections/` 11개 — **전부 현역** (PI Revive 옛 v3 풀 사용)
  - `cover.tsx` / `executive-summary.tsx` / `coordinate-map.tsx` / `gap-analysis.tsx` / `face-structure.tsx` / `skin-analysis.tsx` / `hair-recommendation.tsx` / `overlay-compare.tsx` / `action-plan.tsx` / `trend-context.tsx` / `type-reference.tsx`
  - `celeb-reference.tsx` 만 폐기 (법적 리스크 — feedback memory 참조)
- `components/sigak/` 13개 — **현역**. 홈 (`app/page.tsx`) 핵심 컴포넌트
  - `home-screen.tsx` / `verdict-grid.tsx` / `aspiration-grid.tsx` / `site-footer.tsx` / `feed-shell.tsx` / `result-screen.tsx` / `vision-view.tsx` / `change-view.tsx` / `analyzing-screen.tsx` / `verdict-v2-screen.tsx` / `sigak-report-view.tsx` / `token-insufficient-modal.tsx`
- `components/pi-v3/PiMaintenance.tsx` — PI v3 잠금 시기 산물. PI Revive 부활로 미사용. 정리 대상.
- `components/landing/` 7개 — 비로그인 랜딩 (`hero / nav / cta-section / expert-section / footer / seats-section / tier-section`).
- `components/sia/` 20개 — Sia v4 (`SiaChatView` / `SiaInputDock` / `LoadingSlides` / `EndConfirmModal` / `CompletionScreen` 등).

---

## 13. 확정 사항 전수 리스트 (51개)

(Sia 페르소나 5 · 대화 구조 9 · 메시지 타입 체계 3 · 온보딩 후 3 · 데이터 4 · 상품 6 · 토큰 3 · 리포트 구조 5 · 법적 3 · 인프라 7 · 코드베이스 반영 3 + 3축 좌표 통합 1 = 51개)

핵심 하이라이트:
1. 페르소나 A → B 전환
2. 턴 단위 → 메시지 단위
3. **100% 주관식** (선택지 UI 완전 폐기)
4. 5분 Soft 제한
5. JSON 100% 자동 CLOSING
6. Haiku 1회 호출 = Sia 응답 + 추출 (방법 B)
7. 메시지 타입 10개
8. 4단 리듬 (M1 OBSERVATION 맨 앞)
9. 리포트 자동 생성 (대화 종료 직후)
10. 로딩 슬라이드 5장
11. 피드 10장 영구 저장 (옵션 2)
12. 추구미 원본 영구 저장
13. 시각이 본 당신 첫 1회 무료
14. Knowledge Base **사람 큐레이션 기반**
15. 프론트 report/sections 5개 재활용 (B안)
16. Verdict v2 파라미터 확장 (a안)
17. **Shape/Volume/Age** 확정

---

## 14. 미확정 결정

**본인 즉시:** Q4 카테고리형 유저 유형 네이밍? / Q6 맛보기 케이스? / Knowledge Base 저장소 (Notion vs YAML, **YAML 우선 MVP 권장**) / PI 재생성 가격 / Best Shot 이용 조건

**마케터 완료 후:** 페르소나 C 톤 검수 / CONFRONTATION 5 템플릿 (Priority 1) / 슬라이드 5장 카피 / 이용약관 최종

**본인 UI 후:** 홈 카드 배치 / PI 레이아웃 / 추구미 병치 UX

**FGI 후:** 5분 제한 적정성 / 공개 5 / 잠금 20 비율 / 토큰 30 조정

---

## 15. 개발 로드맵 (Phase G~Q)

### Phase G~M ✅ 모두 완료 (2026-04-23 ~ 2026-04-25)

| Phase | 결과 |
|---|---|
| G 공통 인프라 | CoordinateSystem / UserDataVault / KnowledgeMatcher / SiaWriter / tokens 상수 3개 |
| H Sia v4 | 페르소나 B → C 전환 (4/27) + 메시지 단위 + 100% 주관식 + 14 타입 + 5 fixture (`sia_session_v4.py` 등) |
| I PI 엔진 | `pi_engine.py` 1761라인 + 9 컴포넌트 어댑터 + alembic 작성 → **PI v3 잠금 → Revive Phase B 진행 (§0)** |
| J 추구미 | IG + Pinterest + Sonnet cross-analysis + base64 변환 + 429 retry + vault echo |
| K Best Shot | 4 블로커 해소 + Haiku 4.5 Vision |
| L Verdict v2 | best_fit 풀 노출 + MAX_PHOTOS 5 + 장당 3토큰 + 선결제 흐름 |
| M Monthly | 스켈레톤 (실 엔진 v1.1+) |

### Phase N — 프론트 구현 ✅ **마케터 redesign 1815 적용 진행 중**

랜딩 / 프로필 / 충전 / 설정 / 온보딩 / 업로드 / verdict 결과 / 추구미 / payment / sia/done — 모두 redesign HTML 정합 완료. **PI Revive Phase B-1~B-8 진행** (§0).

### Phase O — 법적 + 관리자

이용약관 v2.0 (4/20 시행) / 개인정보 / 삭제 대응 / 관리자 대시보드 (`app/admin/`).

### Phase P — Knowledge Base 콘텐츠

Tier 1 트렌드 10-20 / 방법론 6-10 / 셀럽 20-30 / Notion/YAML sync

**소요:** 50-65h (본인/마케터 병목)

### Phase Q — QA + Soft Launch

E2E / 버그 / FGI 10-30명 / 피드백 1-2 사이클 / 런칭

### Critical Path (2026-04-27 갱신 — 최종 퍼블리시 전)

Phase G~M + PI v3 + PI Revive Phase B-1~B-8 + 마케터 redesign 톱5 완료. **현 단계 = 디자인/미감 통일 + 디버그**.

```
[현 단계] 디자인 미감 통일 ────────┐
         (마케터 톤 미적용 화면)    │
                                    │
[현 단계] 디버그 fix ───────────────┤→ 4 기능 LIVE probe ─→ 퍼블리시
         (verdict / aspiration /    │   (본인 결제 검증)
          PI Revive 흐름)           │
                                    │
[현 단계] PI Revive Phase B 잔여 ──┘
         (B-9+ 발생 시)
```

**현재 진행 (즉시 영역)**:
- 마케터 redesign 1815 미적용 화면 식별 + 정합 (톱5 외 잔여)
- 디버그 — Apify rate limit / Pinterest 어댑터 / 좌표 산출 fallback / multi-worker stale state 등
- 톤 정합 — `~더라구요` 잔재 grep 제거 / 마케터 카피 vs 코드 미스매치 fix
- 토큰 cleanup — `--color-border` → `--color-line` (저번 커밋 완료) / 추가 디자인 토큰 정합
- 죽은 코드 정리 (sia_session/prompts/validators v1 / pi.py / verdicts.py / `components/pi-v3/`)

**본인 병목 (퍼블리시 직전 검증)**:
- 4 기능 LIVE probe 결제 (Sia 재진입 / Best Shot 30토큰 / Aspiration IG / Pinterest)
- Railway env 검증 (`cost_monitor.py` / `r2_client._client_mode`)
- 최종 톤/카피 검수

**보류 (v1 이후)**:
- KB methodology + references 콘텐츠 (마케터)
- Monthly 실 엔진 (스케줄러 → 실 생성)
- PI v3 (잠금 상태 유지) / 셀럽 매칭 인프라

---

## 16. 리스크 요약

🔴 높음: 추구미 저작권 / 페르소나 C LIVE 검증 / 100% 주관식 Haiku 파싱 / CONFRONTATION 템플릿 부재
🟡 중간: Knowledge Base 병목 / Best Shot 대량 Vision 비용 / 런칭 지연
🟢 낮음: R2 비용 / Apify 비용 / 기술 부채

감수하지 않을 것: 유저 데이터 유출 / 결제 오류 / 미성년자 데이터 분석

---

## 부록 A: 주요 파일 경로

```
백엔드 (sigak/):
├── services/
│   ├── sia_llm.py                    [완료 A, 재설계 H]
│   ├── sia_validators.py             [완료, v4 H]
│   ├── sia_session.py                [완료, 재설계 H]
│   ├── sia_prompts.py                [완료 A, B 재작성 H]
│   ├── ig_scraper.py                 [완료]
│   ├── ig_feed_analyzer.py           [완료 A]
│   ├── verdict_v2.py                 [완료, 확장 L]
│   ├── pi.py                         [껍데기, 폐기 I]
│   ├── tokens.py                     [완료, 상수 3개 추가 G]
│   │
│   ├── coordinate_system.py          [신규 G]
│   ├── user_taste_profile.py         [신규 G]
│   ├── user_data_vault.py            [신규 G]
│   ├── knowledge_base/               [신규 G]
│   ├── knowledge_matcher.py          [신규 G]
│   ├── sia_writer.py                 [신규 G]
│   │
│   ├── pi_engine.py                  [신규 I]
│   ├── aspiration_engine_ig.py       [신규 J]
│   ├── aspiration_engine_pinterest.py [신규 J]
│   ├── best_shot_engine.py           [신규 K]
│   ├── monthly_engine.py             [신규 M]
│   │
│   └── vision_service.py             [ig_feed_analyzer 확장]
│
├── schemas/
│   ├── user_profile.py               [완료, 확장]
│   ├── pi_report.py                  [신규]
│   ├── aspiration.py                 [신규]
│   ├── best_shot.py                  [신규]
│   └── knowledge.py                  [신규]
│
├── routes/
│   ├── sia.py                        [완료, turn_type 전달 G]
│   ├── verdict_v2.py                 [완료]
│   ├── pi.py                         [완료, 재작성 I]
│   ├── aspiration.py                 [신규 J]
│   ├── best_shot.py                  [신규 K]
│   └── monthly.py                    [신규 M]
│
└── tests/
    └── (416 green 유지 + 신규 추가)

프론트 (sigak-web/):
├── components/
│   ├── sia/                          [Task 0/1 완료, SiaChoices 폐기]
│   ├── sigak/                        [레거시 완전 폐기]
│   └── report/                       [5개 재활용 + 5개 폐기]
│
└── app/
    ├── onboarding/sia/               [신규, D7 Phase N]
    ├── report/[id]/                  [재활용 + 신규]
    ├── aspiration/                   [신규]
    ├── best_shot/                    [신규]
    └── ...
```

---

## 부록 B: 용어 정리

| 용어 | 정의 |
|---|---|
| Sia | SIGAK AI 대화 페르소나. 겸손한 경력 디자이너 친구 톤 (페르소나 C, 2026-04-27 B→C 전환). |
| PI (내부 코드) | "시각이 본 당신" 상품. 유저 노출 금지. |
| Verdict (내부 코드) | "피드 추천" 상품. 유저 노출 금지. |
| Monthly (내부 코드) | "이달의 시각" 상품. |
| UserTasteProfile | 6 상품 공유 유저 취향 통합 객체. |
| UserDataVault | 유저 모든 데이터 중앙 저장소. |
| VisualCoordinate | 3축 (Shape/Volume/Age) 좌표 0-1. |
| GapVector | 현재 좌표 → 목표 좌표 이동 벡터. |
| IgFeedAnalysis | Sonnet Vision IG 피드 분석 구조화 결과 (Phase A). |
| Knowledge Base | 외부 큐레이션 지식 (트렌드, 방법론, 레퍼런스). |
| strength_score | profile 데이터 풍부도 0.0-1.0. |
| boundary_message | PI 리포트 공개/잠금 경계 동적 안내. |
| user_original_phrases | 유저 대화 중 발화 원어. 리포트 재활용. |
| 페르소나 A | 폐기된 이전 Sia 톤 (단정 분석가). |
| 페르소나 B | 폐기된 Sia 톤 (간파하는 친근 비서, 2026-04-27 C로 전환). 추정 반문 (~가봐요?) / 카테고라이징 어미가 "맞추려 함" 으로 체감됨. |
| 페르소나 C | 현 Sia 톤 (겸손한 경력 디자이너 친구). 본 게 있지만 떠벌리지 않고 유저 이야기를 끌어냄. 분석 핀트 + 열린 질문 + 부드러운 challenge. |
| 4단 리듬 | OBSERVATION → INTERPRETATION → [유저] → EMPATHY/PROBE |
| 메시지 타입 10개 | OBSERVATION ~ POSITIVE_PIVOT |

---

**문서 끝. v2.0**

**다음 단계:**
1. 본인 Q4, Q6 판단 (미확정)
2. 마케터 CONFRONTATION 5개 템플릿 (Priority 1)
3. **Phase G 실행 (Claude Code 즉시 착수 가능)**
4. 본인 UI 디자인 진행
