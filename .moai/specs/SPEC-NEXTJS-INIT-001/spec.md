---
id: SPEC-NEXTJS-INIT-001
version: "1.0.0"
status: "planned"
created: "2026-04-04"
updated: "2026-04-04"
author: ""
priority: "high"
---

# SPEC-NEXTJS-INIT-001: Next.js 프로젝트 초기화 + 리포트 뷰어 + 페이월 결제

## HISTORY

- 2026-04-04: 초안 생성 (Next.js 16 마이그레이션)
- 2026-04-04: UX.md 반영 (리포트 뷰어 + 블러 페이월)
- 2026-04-04: PAYMENT.md 반영 (카카오톡 수동 결제 + pending + 알바 확인)
- 2026-04-04: 전면 재작성 (전체 alignment)

---

## Environment

### 현재 상태
- landing.jsx (674행): 고객 예약 페이지 - React 18 + CSS-in-JS
- sigak_dashboard.jsx (427행): 인터뷰어 대시보드 - React 18 + 인라인 스타일
- sigak-backend.tar.gz: FastAPI - 인메모리 저장, 10개 API, 5개 ORM 테이블
- 빌드 시스템/package.json/TypeScript 없음

### 목표 상태
- Next.js 16 App Router 기반 sigak-web/ 프로젝트
- 3개 라우트: / (랜딩), /dashboard (대시보드), /report/[id] (리포트 뷰어)
- Tailwind CSS v4 + CSS Variables 디자인 시스템
- TypeScript strict, pnpm, ESLint/Prettier
- 프리미엄 페이월 + 카카오톡 수동 결제 (WoZ Phase 1)

### 기술 환경
- Node.js 20 LTS, Next.js 16, React 19, TypeScript 5.9+
- Tailwind CSS v4, pnpm, ESLint, Prettier
- next/font (Noto Serif KR + Pretendard Variable)
- FastAPI 백엔드 (기존 확장)

---

## Assumptions

1. Next.js 16 App Router가 React 19 Server Components를 안정 지원
2. Tailwind v4 @theme가 CSS Variables와 호환
3. next/font로 한글 폰트 최적화 가능
4. backdrop-filter: blur()가 주요 브라우저 지원
5. 리포트 API는 mock, PAYMENT.md 구조 준수
6. Phase 1(카카오톡 수동)만 구현, Phase 2(토스페이먼츠)는 별도 SPEC
7. 기존 JSX는 루트에 참조용 보존

---

## Requirements

### R1: 프로젝트 초기화 [Ubiquitous]
시스템은 항상 Next.js 16 App Router 규약에 따른 디렉토리 구조를 유지해야 한다.
- R1.1: app/ 루트 라우팅
- R1.2: app/layout.tsx 글로벌 레이아웃
- R1.3: tsconfig strict: true
- R1.4: pnpm-lock.yaml 잠금

### R2: 디자인 시스템 추출 [Ubiquitous]
공유 디자인 토큰을 globals.css 단일 소스에서 관리.
- R2.1: 컬러 (--color-bg: #F3F0EB, --color-fg: #000)
- R2.2: 블러 (--color-blur-bg: rgba(243,240,235,0.7), blur(12px))
- R2.3: 타이포 (Noto Serif KR via next/font/google + Pretendard via next/font/local)
- R2.4: 레이아웃 (60px/24px 패딩, 1:1:2 그리드, 768px 브레이크포인트)
- R2.5: ::selection 반전

### R3: 랜딩 페이지 [Event-Driven]
WHEN / 접근 THEN 랜딩 렌더링
- R3.1: 7개 섹션 (NAV/HERO/TIERS x3/EXPERTS x2/SEATS/CTA/FOOTER)
- R3.2: 스크롤 reveal (opacity 0->1, translateY 20px->0, 0.8s)
- R3.3: 예약 오버레이 (우측 슬라이드, 티어->날짜->시간->폼->결제)
- R3.4: 하드코딩 BOOKINGS 데이터 유지
- R3.5: 768px 이하 모바일 (단일컬럼, 24px 패딩)

### R4: 대시보드 [Event-Driven]
WHEN /dashboard 접근 THEN 대시보드 렌더링
- R4.1: 4뷰 전환 (대기열/인터뷰입력/지표/결제확인)
- R4.2: mock 5명 유저, 날짜별 그룹핑, 상태 뱃지
- R4.3: 코어 6 + 티어별 추가 질문, 진행률 바
- R4.4: H1/H2/H4 지표, 목표 미달시 #A32D2D
- R4.5: 결제 확인 뷰 (pending 목록, 확인/미확인)

### R5: 리포트 뷰어 [Event-Driven]
WHEN /report/[id] 접근 THEN 리포트 렌더링
- R5.1: 8개 섹션 순서대로 렌더링
- R5.2: locked: false -> 전체 렌더링
- R5.3: locked: true -> 블러 티저
- R5.4: unlock_level 그룹 마지막 뒤 PaywallGate 1개
- R5.5: mock 데이터 (PAYMENT.md API 구조)

### R6: 블러 티저 시스템 [State-Driven]
5단계 access_level:
- free: cover/summary/face만 공개
- standard_pending: + standard 섹션 블러 + PendingCard
- standard: + standard 섹션 공개
- full_pending: + full 섹션 블러 + PendingCard
- full: 전체 공개

### R7: 블러 티저 규칙 [Ubiquitous]
원칙: "답이 있다는 것은 보여주고, 답 자체는 가린다."
- skin_analysis: "웜톤 밝은 편" 선명 / 분석 텍스트 블러
- coordinate_map: 축 라인/격자 선명 / 점/수치 블러
- action_plan: 카테고리+우선순위 선명 / 추천 내용 블러
- celeb_reference: "수지와 85% 유사" 선명 / 이유 블러
- trend_context: 제목만 선명 / 전부 블러
- CSS: backdrop-filter: blur(12px) + rgba(243,240,235,0.7)
- 해제: opacity 0 전환 0.6s ease

### R8: 결제 Phase 1 - 카카오톡 수동 [Event-Driven]
WHEN method=manual, 결제 버튼 클릭:
- R8.1: 송금 안내 (카카오뱅크/계좌/예금주/금액)
- R8.2: 카카오톡 송금 딥링크 버튼
- R8.3: "송금 완료" -> POST payment-request -> pending
- R8.4: PendingCard ("확인 대기 중..." + 경과시간)
- R8.5: 30초 폴링 (GET report)
- R8.6: 탭 비활성시 폴링 중지 (visibilitychange)
- R8.7: 확인 감지시 블러 fade-out 0.6s + 스크롤 유지

### R9: 결제 확인 대시보드 [Event-Driven]
WHEN 알바가 결제 탭 접근:
- R9.1: GET /dashboard/payments pending 목록
- R9.2: 유저명/티어/레벨/금액/경과시간
- R9.3: 확인완료 -> POST confirm-payment (confirmed: true)
- R9.4: 미확인 -> POST confirm-payment (confirmed: false)
- R9.5: 오늘 완료 목록 하단

### R10: 결제 백엔드 API [Ubiquitous]
- R10.1: POST /payment-request/{user_id}
- R10.2: POST /confirm-payment/{user_id}
- R10.3: GET /dashboard/payments
- R10.4: GET /report 응답에 pending_level, payment_account
- R10.5: payment_requests 테이블
- R10.6: reports에 pending_level, payment_1_at, payment_2_at
- R10.7: 24h 미입금 pending 자동 해제

### R11: 빌드/개발 환경 [Ubiquitous]
pnpm dev/build 정상, TS 에러 0, ESLint 에러 0

### R12: 컴포넌트 분리 [Ubiquitous]
components/ui, landing, dashboard, report + lib/constants, types, utils

### R13: 비허용 행위 [Unwanted]
CSS-in-JS 문자열, 인라인 스타일, any 타입, CDN 폰트 금지

### R14: SEO [Optional]
Metadata API, lang="ko"


---

## Specifications

### S1: 디렉토리 구조

```
sigak-web/
+-- app/
|   +-- layout.tsx                   # 루트 레이아웃
|   +-- page.tsx                     # 랜딩 (/)
|   +-- globals.css                  # Tailwind + CSS Variables + 블러
|   +-- dashboard/
|   |   +-- layout.tsx               # 대시보드 레이아웃
|   |   +-- page.tsx                 # 대시보드 (/dashboard)
|   +-- report/
|       +-- [id]/
|           +-- page.tsx             # 리포트 뷰어 (/report/[id])
+-- components/
|   +-- ui/
|   |   +-- button.tsx, divider.tsx, input.tsx
|   |   +-- reveal-on-scroll.tsx     # IntersectionObserver
|   |   +-- blur-overlay.tsx         # 블러 오버레이
|   |   +-- paywall-card.tsx         # 페이월 카드 (method 분기)
|   +-- landing/
|   |   +-- nav.tsx, hero.tsx, tier-section.tsx
|   |   +-- expert-section.tsx, seats-section.tsx
|   |   +-- cta-section.tsx, footer.tsx, booking-overlay.tsx
|   +-- dashboard/
|   |   +-- queue-view.tsx, entry-view.tsx
|   |   +-- stats-view.tsx, stat-card.tsx
|   |   +-- payments-view.tsx        # 결제 확인 뷰
|   |   +-- payment-confirm-card.tsx # 확인/미확인 카드
|   +-- report/
|       +-- report-viewer.tsx        # 오케스트레이션 (Client)
|       +-- section-renderer.tsx     # 섹션 분기
|       +-- blur-teaser.tsx          # 조건부 블러 (Client)
|       +-- paywall-gate.tsx         # locked/pending/unlocked (Client)
|       +-- manual-payment-flow.tsx  # 카카오톡 송금 (Client)
|       +-- pending-card.tsx         # 대기 UI (Client)
|       +-- sections/
|           +-- cover.tsx, executive-summary.tsx, face-structure.tsx
|           +-- skin-analysis.tsx, coordinate-map.tsx
|           +-- action-plan.tsx, celeb-reference.tsx, trend-context.tsx
+-- lib/
|   +-- constants/
|   |   +-- tiers.ts, bookings.ts, questions.ts, mock-data.ts
|   |   +-- mock-report.ts, mock-payments.ts
|   +-- types/
|   |   +-- tier.ts, booking.ts, dashboard.ts, report.ts, payment.ts
|   +-- utils/
|       +-- date.ts, booking.ts, report.ts, polling.ts
+-- public/fonts/PretendardVariable.woff2
+-- next.config.ts, postcss.config.mjs, tsconfig.json
+-- package.json, .eslintrc.json, .prettierrc, .gitignore
```

### S2: 기술 스택

| 패키지 | 버전 | 용도 |
|--------|------|------|
| next | >=16.0.0 | App Router |
| react/react-dom | >=19.0.0 | UI |
| typescript | >=5.9.0 | 타입 |
| tailwindcss | >=4.0.0 | CSS |
| @tailwindcss/postcss | >=4.0.0 | PostCSS |
| eslint-config-next | >=16.0.0 | 린팅 |
| prettier | >=3.0.0 | 포매팅 |

### S3: 핵심 타입 정의

```typescript
// lib/types/report.ts
type AccessLevel = "free" | "standard_pending" | "standard" | "full_pending" | "full";
type UnlockLevel = "standard" | "full";
type SectionId = "cover" | "executive_summary" | "face_structure"
  | "skin_analysis" | "coordinate_map"
  | "action_plan" | "celeb_reference" | "trend_context";

interface ReportSection {
  id: SectionId; locked: boolean;
  content?: Record<string, unknown>;
  unlock_level?: UnlockLevel;
  teaser?: { headline?: string; categories?: string[]; } | null;
}

interface ReportData {
  id: string; user_name: string;
  access_level: AccessLevel; pending_level: UnlockLevel | null;
  sections: ReportSection[];
  paywall: Record<UnlockLevel, PaywallTier>;
  payment_account: PaymentAccount;
}

interface PaywallTier {
  price: number; label: string;
  total_note?: string; method: "manual" | "auto";
}

interface PaymentAccount {
  bank: string; number: string; holder: string; kakao_link: string;
}
```

### S4: PaywallGate 렌더링

```
cover (free)        -> 전체
executive_summary   -> 전체
face_structure      -> 전체
skin_analysis (std) -> 블러 or 공개
coordinate_map (std)-> 블러 or 공개
-- PaywallGate(standard): locked->PaywallCard / pending->PendingCard / unlocked->null
action_plan (full)  -> 블러 or 공개
celeb_ref (full)    -> 블러 or 공개
trend (full)        -> 블러 or 공개
-- PaywallGate(full): locked->PaywallCard / pending->PendingCard / unlocked->null
```

---

## Traceability

| 요구사항 | 구현 파일 | 인수 조건 |
|--|--|--|
| R1 | package.json, tsconfig, next.config | AC-1 |
| R2 | globals.css, layout.tsx | AC-2 |
| R3 | app/page, components/landing/* | AC-3 |
| R4 | app/dashboard/*, components/dashboard/* | AC-4 |
| R5-R7 | app/report/[id]/*, components/report/* | AC-5, AC-6 |
| R8 | manual-payment-flow, pending-card, polling | AC-7 |
| R9 | payments-view, payment-confirm-card | AC-8 |
| R10 | backend main.py, db.py | AC-9 |
| R11-R13 | 전체 | AC-10, AC-11 |
| R14 | layout.tsx | AC-2 |
