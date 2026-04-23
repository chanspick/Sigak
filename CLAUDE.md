# SIGAK 프로덕트 설계 문서 (통합 최종본)

**버전:** v2.0
**작성:** 2026-04-22
**상태:** Week 2 재설계 착수 직전, 확정 사항 51개 반영 완료

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

1. **Sia 페르소나 B** — "간파하는 비서" 톤. 단순 챗봇 아님.
2. **데이터 누적 구조** — 유저가 쓸수록 개인화 정확도 ↑. 락인.
3. **큐레이션 기반 Knowledge Base** — AI 자동 생성이 아닌 사람 큐레이션 트렌드/방법론.
4. **시계열 아카이브** — 유저 미감 변천사 장기 보관. 경쟁사 따라올 수 없는 데이터 자산.

### 현 상태 (2026-04-22)

**이미 완성된 것:**
- Sia 대화 엔진 Phase A-F (416 tests green)
- Verdict v2 풀 E2E (Sonnet Vision + preview/full + 10 토큰 unlock + 프론트 연결)
- 토큰 시스템 (atomic 차감, idempotency, 3팩 catalog: STARTER/REGULAR/PRO)
- 프론트 components/sia/* (Task 0/1 포팅)
- 프론트 components/report/sections/* 12개 (구 PI 원형 UI)

**재작업 필요:**
- Sia 페르소나 A→B 전환 + 턴 단위→메시지 단위 + 100% 주관식
- PI 실제 엔진 구현 (현재 placeholder)
- 공통 인프라 레이어 (UserTasteProfile, UserDataVault, Knowledge Base 등)
- 신규 상품 엔진 4개 (PI, Best Shot, 추구미 IG/Pinterest, 이달의 시각)

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

### 4.7 SiaWriter (페르소나 B 공통)

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

### 6.1 페르소나 B (확정)

| | 페르소나 A (폐기) | 페르소나 B (현) |
|---|---|---|
| 포지션 | 감도 날카로운 AI 미감 분석가 | 간파하는 친근 비서 / 매니저 |
| 어조 | 정중체 ("~합니다/~분이십니다") | 친근체 ("~가봐요?/~이신 것 같은데") |
| 유저 반응 | "어 맞는데" | **"어 맞아 근데 어떻게 알았지"** |

### 6.2 어미 규칙

**허용:** "~가봐요?" / "~이신 것 같은데" / "~으시죠?" / "~이시잖아요" / "~더라구요" / "~습니다"
**금지:** "~네요" / "~군요" / "~같아요" / "~같습니다" / "~것 같" / "~수 있습니다"

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
| 피부톤 LAB 분석 | 폐기 (페르소나 B 와 톤 충돌) |
| 갭 분석 벡터 | 추구미 분석 엔진 |
| 셀럽 레퍼런스 | Knowledge Base (v1.1+) |
| 얼굴 오버레이 | 폐기 (25장 스토리와 중복) |
| 컬러 팔레트 hex | PI 잠금 20장 보조 (style_element) |
| 삼각형 레이더 | 추구미 분석 UI 보조 |
| 6섹션 Claude 리포트 | 폐기 (25장 스토리로 대체) |
| 블러 페이월 3-tier | 폐기 (공개 5 + 잠금 20 단순화) |

### 12.4 프론트 컴포넌트 처리 (B안)

**재활용 (5개):**
- `coordinate-map.tsx` → 추구미 비교 삼각형 레이더
- `gap-analysis.tsx` → 갭 시각화
- `paywall-gate.tsx` → PI 공개/잠금 경계
- `blur-teaser.tsx` → 잠금 20장 티저
- `action-plan.tsx` → Knowledge Base 매칭 표시

**폐기 (5개):** face-structure / skin-analysis / hair-recommendation / celeb-reference / overlay-compare

**레거시 /components/sigak/ — 완전 폐기**

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

**마케터 완료 후:** 페르소나 B 톤 / CONFRONTATION 5 템플릿 (Priority 1) / 슬라이드 5장 카피 / 이용약관 최종

**본인 UI 후:** 홈 카드 배치 / PI 레이아웃 / 추구미 병치 UX

**FGI 후:** 5분 제한 적정성 / 공개 5 / 잠금 20 비율 / 토큰 30 조정

---

## 15. 개발 로드맵 (Phase G~Q)

### Phase G — 공통 인프라 리팩토링 ⬅️ **즉시 실행 가능**

**범위:**
- CoordinateSystem (Shape/Volume/Age)
- UserTasteProfile
- UserDataVault
- Knowledge Base 레이어 (스켈레톤 + 로더)
- KnowledgeMatcher
- SiaWriter 공통 호출
- tokens.py 상수 3개 추가 (ASPIRATION_IG/PINTEREST/BEST_SHOT)
- pi_reports 마이그레이션 계획 (user_id → report_id + version) — 실 migration 은 Phase I 시점
- **routes/sia.py turn_type/gender 파라미터 전달 (Phase C 누락분)**

**폐기:** `services/pi.py::build_v2_report_data` seed echo, `_echo_structured_fields`, placeholder 5 null 필드

**테스트:** 416 green 유지 + 신규 +30

**소요:** 1-2일

### Phase H — Sia 재설계 (페르소나 B + 메시지 단위 + 100% 주관식) 🔴 블로킹

**선행:** 마케터 페르소나 B 인격 + CONFRONTATION 5개 템플릿

**범위:**
- 메시지 타입 10개 구현
- 4단 리듬 로직
- `decide_next_message` (기존 `decide_next_turn` 대체)
- Haiku 통합 호출 (응답 + 추출 JSON)
- 100% 주관식 파싱 layer
- JSON 필드 수집 누적
- CLOSING 자동 판정 (JSON 100% or 5:00)
- validator v4 재정의 (주관식 어미 규칙)
- CONFRONTATION 템플릿 통합
- Phase D fixture 재작성 (메시지 sequence)
- Phase E/F 테스트 재작성

**소요:** 2-3일 (마케터 해소 후)

### Phase I — PI 엔진 구현

**선행:** G + H + Knowledge Base 콘텐츠 일부

**범위:**
- `pi_engine.generate_pi_report`
- `select_photos_for_pi` (Sonnet Vision)
- `compose_pi_sections` (공개 5 + 잠금 20)
- 아이작 M REPORT 오프닝 7페이지 패턴
- `user_original_phrases` 축적 → 리포트 재활용
- Knowledge Base 매칭 반영
- 재생성 로직 (버전 관리)
- pi_reports 실 migration

**소요:** 1-2일

### Phase J — 추구미 분석

aspiration_engine_ig / aspiration_engine_pinterest (동일 구조) / 좌우 병치 리포트 / 삼각형 레이더 / 블록리스트 체크

**소요:** 1일

### Phase K — Best Shot

대량 업로드 / 품질 필터 1차 / Profile 점수 2차 / Knowledge Base 호환 / 상위 30 + Sia / Haiku 4.5 Vision 검토

**소요:** 1-2일

### Phase L — Verdict v2 확장 (최소 침습)

시그니처에 `matched_trends`, `taste_profile` 추가 / Knowledge Base 매칭 주입 / 기존 JSON 유지 / 프론트 변경 최소

**소요:** 0.5일

### Phase M — 이달의 시각 스켈레톤

스케줄러 스텁 (cron) / DB 스키마 / "준비 중" UI

**소요:** 0.5일

### Phase N — 프론트 구현 (본인 주도)

Sia 대화 / 홈 IA / 로딩 슬라이드 / PI 리포트 / 추구미 비교

### Phase O — 법적 + 관리자

이용약관 / 개인정보 / 삭제 대응 템플릿 / 관리자 대시보드

### Phase P — Knowledge Base 콘텐츠

Tier 1 트렌드 10-20 / 방법론 6-10 / 셀럽 20-30 / Notion/YAML sync

**소요:** 50-65h (본인/마케터 병목)

### Phase Q — QA + Soft Launch

E2E / 버그 / FGI 10-30명 / 피드백 1-2 사이클 / 런칭

### Critical Path

```
마케터 페르소나 B + CONFRONTATION → Phase H → Phase Q
         │
         └→ Knowledge Base 콘텐츠 → Phase I, J, K → Phase Q
              │
본인 UI 디자인 → Phase N ────────────────────────┘

Phase G → Phase L (병렬 가능) → Phase M (병렬 가능)
```

---

## 16. 리스크 요약

🔴 높음: 추구미 저작권 / 페르소나 B 전환 / 100% 주관식 Haiku 파싱 / CONFRONTATION 템플릿 부재
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
| Sia | SIGAK AI 대화 페르소나. 친근 비서 톤 (페르소나 B). |
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
| 페르소나 B | 현 Sia 톤 (친근 비서 / 간파형 매니저). |
| 4단 리듬 | OBSERVATION → INTERPRETATION → [유저] → EMPATHY/PROBE |
| 메시지 타입 10개 | OBSERVATION ~ POSITIVE_PIVOT |

---

**문서 끝. v2.0**

**다음 단계:**
1. 본인 Q4, Q6 판단 (미확정)
2. 마케터 CONFRONTATION 5개 템플릿 (Priority 1)
3. **Phase G 실행 (Claude Code 즉시 착수 가능)**
4. 본인 UI 디자인 진행
