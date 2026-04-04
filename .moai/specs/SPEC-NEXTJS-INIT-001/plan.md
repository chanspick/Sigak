# SPEC-NEXTJS-INIT-001: 구현 계획

## 전략 개요

기존 JSX 파일 2개(landing.jsx, sigak_dashboard.jsx)를 **Next.js 16 + TypeScript + Tailwind CSS v4** 기반의 프로덕션 레벨 애플리케이션으로 마이그레이션한다. 핵심 신규 기능으로 **리포트 뷰어(블러 페이월)** 와 **카카오톡 수동 결제 플로우**를 구현한다.

- **프레임워크**: Next.js 16 (App Router, React 19)
- **언어**: TypeScript (strict mode)
- **스타일**: Tailwind CSS v4 (@theme directive, zero CSS-in-JS)
- **패키지 매니저**: pnpm
- **폰트**: Noto Serif KR (Google Fonts) + PretendardVariable (로컬)
- **결제**: 수동 계좌이체 + 카카오톡 딜링크 (TossPayments PG는 Phase 2)

---

## 마일스톤 및 태스크 (8 마일스톤, 26 태스크)

---

### 마일스톤 1: 프로젝트 기반 (T1-T3)

#### T1: Next.js 프로젝트 생성

- `create-next-app@latest --typescript --tailwind --app --use-pnpm` 실행
- 보일러플레이트 정리: 기본 page.tsx 내용 제거, 불필요한 아이콘/이미지 삭제
- `tsconfig.json`에서 `strict: true` 확인
- `compilerOptions.paths`에 `@/*` 별칭 설정 확인

#### T2: 프로젝트 설정 파일 구성

- **next.config.ts**: reactStrictMode, images 도메인, experimental 설정
- **postcss.config.mjs**: Tailwind CSS v4 플러그인 (`@tailwindcss/postcss`)
- **.eslintrc.json**: `next/core-web-vitals`, `next/typescript` extends
- **.prettierrc**: singleQuote, semi, tabWidth: 2, trailingComma: all
- **.gitignore**: .next/, node_modules/, .env*.local, out/

#### T3: PretendardVariable 폰트 다운로드

- `PretendardVariable.woff2` 파일 다운로드
- `public/fonts/PretendardVariable.woff2` 경로에 배치
- CDN 의존성 제거 (로컬 폰트만 사용)

---

### 마일스톤 2: 디자인 시스템 (T4-T6)

#### T4: globals.css 및 테마 설정

- Tailwind v4 `@theme` directive를 활용한 디자인 토큰 정의:
  - `--color-bg: #F3F0EB` (메인 배경)
  - `--color-fg: #000` (텍스트)
  - `--color-blur-bg: rgba(243, 240, 235, 0.7)` (블러 오버레이)
  - `--color-accent`, `--color-muted`, `--color-border` 등
- 폰트 패밀리 변수: `--font-serif`, `--font-sans`
- `::selection` 스타일 (배경색 + 텍스트색)
- 블러 유틸리티 클래스:
  - `.blur-overlay`: `backdrop-filter: blur(12px)` + 반투명 배경
  - `.blur-fade-out`: 0.6초 트랜지션 애니메이션
  - `.blur-teaser`: 티저 영역 가시성 제어

#### T5: 루트 레이아웃 (app/layout.tsx)

- `next/font/google`로 Noto Serif KR 로드 (weights: 400, 600, 700)
- `next/font/local`로 PretendardVariable 로드
- Next.js Metadata API 설정:
  - title, description, openGraph, twitter
  - viewport, themeColor
- `<html lang="ko">` 설정
- 폰트 CSS 변수를 `<body>`에 적용

#### T6: 공통 UI 컴포넌트

- **Button**: variant(primary/secondary/ghost), size(sm/md/lg), disabled 상태
- **Divider**: horizontal/vertical, 색상 커스텀
- **Input**: label, error 메시지, 폼 통합
- **RevealOnScroll**: Intersection Observer 기반, threshold 설정 가능
- **BlurOverlay**: 블러 강도/배경색 props, 애니메이션 지원
- **PaywallCard**: 결제 유도 카드, 가격/설명/CTA 버튼 포함

---

### 마일스톤 3: 타입/데이터 계층 (T7-T9)

#### T7: TypeScript 타입 정의

- **tier.ts**: `TierType`, `TierInfo`, 가격/좌석/설명 포함
- **booking.ts**: `BookingStep`, `BookingForm`, `TimeSlot`, `BookingState`
- **dashboard.ts**: `QueueEntry`, `DashboardView`, `StatCard`, `EntryStatus`
- **report.ts**:
  - `AccessLevel`: `'free' | 'standard' | 'full'`
  - `PendingLevel`: `'none' | 'standard' | 'full'`
  - `ReportSection`: 8개 섹션 유니온 타입
  - `SectionVisibility`: 섹션별 공개/블러/잠금 상태
  - `ReportData`: 전체 리포트 데이터 구조
- **payment.ts**: `PaymentRequest`, `PaymentStatus`, `PaymentConfirmAction`

#### T8: 상수 및 목 데이터

- **tiers.ts**: Free/Standard/Full 티어 정보, 가격, 설명, 포함 섹션
- **bookings.ts**: 예약 가능 시간대, 기본 질문 목록
- **questions.ts**: 티어별 사전 질문 (피부 고민, 원하는 스타일 등)
- **mock-data.ts**: 대시보드용 샘플 큐/예약 데이터
- **mock-report.ts**: PAYMENT.md API 구조 기반 리포트 목 데이터
  - 8개 섹션 전체 데이터 포함
  - Free/Standard/Full 접근 레벨별 가시성 매핑
- **mock-payments.ts**: 결제 요청/확인 샘플 데이터

#### T9: 유틸리티 함수

- **date.ts**: 날짜 포맷팅, 상대 시간 계산, 타임존 처리
- **booking.ts**: 예약 가능 여부 확인, 시간대 필터링
- **report.ts**:
  - `isUnlocked(section, accessLevel)`: 섹션 잠금 해제 여부 판단
  - `getPaywallInsertPoints(accessLevel)`: 페이월 삽입 위치 계산
  - `getSectionVisibility(accessLevel, pendingLevel)`: 섹션별 가시성 맵 반환
- **usePolling.ts**: 커스텀 훅
  - 30초 간격 폴링
  - `document.visibilitychange` 이벤트 감지하여 탭 비활성 시 일시중지
  - cleanup 함수 포함

---

### 마일스톤 4: 랜딩 + 대시보드 페이지 (T10-T14)

#### T10: 랜딩 페이지 컴포넌트 7개

기존 `landing.jsx`의 CSS-in-JS를 Tailwind 클래스로 변환:

1. **NavBar**: 로고, 메뉴 링크, 모바일 햄버거
2. **HeroSection**: 메인 카피, 서브텍스트, CTA 버튼
3. **TierSection**: 3개 티어 카드 (Free/Standard/Full), 가격, 포함 항목
4. **ExpertSection**: 전문가 소개, 자격 사항
5. **SeatsSection**: 잔여 좌석 표시, 긴급감 연출
6. **CTASection**: 하단 최종 CTA, 예약 유도
7. **Footer**: 연락처, 소셜 링크, 법적 고지

- 각 컴포넌트는 Server Component 기본
- RevealOnScroll 래핑으로 스크롤 애니메이션 적용

#### T11: 예약 오버레이 (Client Component)

- 5단계 플로우: 티어 선택 -> 날짜 선택 -> 시간 선택 -> 정보 입력 -> 결제 시뮬레이션
- 오버레이/모달 UI (배경 딨 처리)
- 폼 유효성 검사 (이름, 전화번호, 이메일)
- 단계별 뒤로가기/앞으로가기 네비게이션
- 예약 완료 시 확인 화면

#### T12: app/page.tsx 조립

- Server Component로 7개 랜딩 컴포넌트 조립
- BookingOverlay를 Client Component로 조건부 렌더링
- Metadata 설정 (title, description)

#### T13: 대시보드 컴포넌트

- **QueueView**: 대기열 리스트, 상태 뱃지, 예상 대기 시간
- **EntryView**: 개별 엔트리 상세, 사전 질문 답변, 상태 변경
- **StatsView**: 통계 카드 그리드, 일/주/월 필터
- **StatCard**: 아이콘, 수치, 변화율, 그래프 (선택)

#### T14: app/dashboard/ 조립

- **layout.tsx**: 사이드바 네비게이션, 헤더, 반응형 레이아웃
- **page.tsx**: 4개 뷰 탭 전환 (대기열/엔트리/통계/결제)
- 뷰 전환 시 URL 파라미터 동기화

---

### 마일스톤 5: 리포트 뷰어 + 결제 프론트엔드 (T15-T19)

#### T15: 리포트 섹션 컴포넌트 8개

1. **CoverSection**: 리포트 표지, 사용자 이름, 생성일, 리포트 ID
2. **ExecutiveSummarySection**: 종합 요약, 핵심 포인트 3-5개
3. **FaceStructureSection**: 얼굴 구조 분석, 비율, 황금비 비교
4. **SkinAnalysisSection**: 피부 분석, 수분/유분/탄력 등 지표
5. **CoordinateMapSection**: 퍼스널 컴러, 스타일 좌표
6. **ActionPlanSection**: 맞춤 실행 계획, 단계별 추천
7. **CelebReferenceSection**: 유사 셀럽 매칭, 스타일 참고
8. **TrendContextSection**: 트렌드 맥락, 시즌별 추천

- 각 섹션은 독립적 컴포넌트, `data` prop으로 내용 수신

#### T16: blur-teaser.tsx

- `accessLevel`에 따른 조건부 블러 처리
- 티저 영역: 섹션 상단 일부 콘텐츠 가시 상태 유지
- 블러 처리: `backdrop-filter: blur(12px)` + `rgba(243,240,235,0.7)` 오버레이
- 잠금 해제 시: 0.6초 `fade-out` 애니메이션으로 블러 제거
- `will-change: backdrop-filter` 힌트로 모바일 성능 최적화

#### T17: paywall-gate.tsx

3가지 상태 관리:

1. **locked**: `PaywallCard` 표시 (가격, 설명, 결제 CTA)
2. **pending**: `PendingCard` 표시 (확인 대기 중, 경과 시간)
3. **unlocked**: `null` 반환 (컴포넌트 미렌더링)

- `accessLevel`과 `pendingLevel`을 조합하여 상태 결정
- 상태 전환 시 부드러운 애니메이션

#### T18: manual-payment-flow.tsx + pending-card.tsx

**manual-payment-flow.tsx**:
- 은행명, 계좌번호, 예금주, 금액 표시 (복사 버튼 포함)
- 카카오톡 딜링크 버튼 (`kakaotalk://`)
- "송금 완료" 버튼 클릭 시 `POST /api/payment-request` 호출
- 결제 요청 후 PendingCard로 전환

**pending-card.tsx**:
- "확인 대기 중..." 메시지 표시
- 결제 요청 후 경과 시간 실시간 표시 (mm:ss)
- 스피너/펄스 애니메이션
- 30초 폴링으로 관리자 확인 상태 체크

#### T19: report-viewer.tsx 조립

- `access_level`과 `pending_level`을 `useState`로 관리
- 8개 섹션 순차 렌더링, 각 섹션에 블러/페이월 조건 적용
- **30초 폴링**: `usePolling` 훅 사용
  - `document.visibilitychange`로 탭 비활성 시 일시중지
  - 활성 복귀 시 즉시 1회 fetch 후 폴링 재개
- **상태 변경 시**:
  - 블러 `fade-out` 0.6초 애니메이션
  - `window.scrollY` 보존 (레이아웃 시프트 방지)
- PaywallGate 삽입 위치: `getPaywallInsertPoints()` 유틸 사용

---

### 마일스톤 6: 결제 확인 대시보드 (T20-T21)

#### T20: payments-view.tsx + payment-confirm-card.tsx

**payments-view.tsx**:
- 미확인 결제 요청 리스트 (pending 상태)
- 오늘 처리 완료 리스트 (confirmed/rejected)
- 실시간 갱신 (30초 폴링)

**payment-confirm-card.tsx**:
- 사용자 정보, 요청 시각, 결제 금액, 요청 티어
- "확인" 버튼: `POST /api/confirm-payment` (action: confirm)
- "거절" 버튼: `POST /api/confirm-payment` (action: reject)
- 확인/거절 후 리스트에서 즉시 제거 (optimistic update)

#### T21: 대시보드 4-뷰 전환 업데이트

- 기존 3개 뷰(대기열/엔트리/통계)에 **결제(payments)** 뷰 추가
- 탭 네비게이션 UI 업데이트
- URL 파라미터: `?view=queue|entry|stats|payments`
- 결제 뷰에 미확인 건수 뱃지 표시

---

### 마일스톤 7: 결제 백엔드 (T22-T24)

#### T22: API 엔드포인트 3개

1. **POST /api/payment-request**
   - 요청 본문: `{ reportId, tier, userName, amount }`
   - 응답: `{ requestId, status: 'pending', createdAt }`
   - 결제 요청 레코드 생성, 리포트에 `pending_level` 설정

2. **POST /api/confirm-payment**
   - 요청 본문: `{ requestId, action: 'confirm' | 'reject' }`
   - confirm: `access_level` 업그레이드, `pending_level` 초기화, 결제 일시 기록
   - reject: `pending_level` 초기화, 사용자에게 거절 메시지

3. **GET /api/dashboard/payments**
   - 응답: `{ pending: PaymentRequest[], todayCompleted: PaymentRequest[] }`
   - 관리자 전용 엔드포인트

#### T23: DB 스키마 확장

- **payment_requests 테이블**:
  - `id`, `report_id`, `user_name`, `tier`, `amount`
  - `status`: `'pending' | 'confirmed' | 'rejected' | 'cancelled'`
  - `created_at`, `confirmed_at`, `cancelled_at`

- **reports 테이블 확장**:
  - `pending_level`: `'none' | 'standard' | 'full'` 추가
  - `payment_1_at`: Standard 결제 확인 일시
  - `payment_2_at`: Full 결제 확인 일시

- **GET /api/report 응답 업데이트**:
  - `access_level`, `pending_level` 필드 포함

#### T24: 24시간 자동 취소 크론

- 미확인 pending 결제 요청 중 24시간 경과 건 자동 취소
- `status`를 `'cancelled'`로 변경
- `pending_level`을 `'none'`으로 초기화
- Next.js Route Handler 또는 외부 크론 서비스 활용

---

### 마일스톤 8: 검증 (T25-T26)

#### T25: 빌드 검증

- `pnpm build`: 0 에러, 0 경고
- `tsc --noEmit`: 타입 에러 0건
- `pnpm lint`: ESLint 에러 0건
- 번들 사이즈 확인 및 기록

#### T26: 시각적 검증

- **랜딩 페이지**: 데스크톱(1440px) + 모바일(375px) 레이아웃 확인
- **대시보드**: 4개 뷰 전환 정상 동작 확인
- **리포트 뷰어**:
  - Free: 3개 섹션 공개, 5개 블러, 2개 PaywallGate
  - Standard: 추가 섹션 공개, 블러 해제 애니메이션
  - Full: 전체 공개
- **결제 플로우**:
  - 계좌 정보 표시 -> 카카오톡 딥링크 -> 송금 완료 -> 대기 -> 확인 -> 해제
  - 거절 시 메시지 표시 -> 잠금 복원

---

## 아키텍처

```
app/
  layout.tsx              [Server] 루트 레이아웃 (폰트, 메타데이터)
  page.tsx                [Server] 랜딩 페이지 조립
  dashboard/
    layout.tsx            [Server] 대시보드 레이아웃 (사이드바)
    page.tsx              [Client] 4-뷰 전환 (queue/entry/stats/payments)
  report/[id]/page.tsx    [Client] 리포트 뷰어 (폴링, 상태 관리)
  api/
    payment-request/route.ts    [Server] POST 결제 요청
    confirm-payment/route.ts    [Server] POST 결제 확인/거절
    dashboard/payments/route.ts [Server] GET 결제 목록
components/
  ui/                     공통 UI (Button, Divider, Input, etc.)
  landing/                랜딩 7개 섹션 컴포넌트
  booking/                예약 오버레이 [Client]
  dashboard/              대시보드 뷰 컴포넌트 [Client]
  report/
    sections/             리포트 8개 섹션 컴포넌트
    blur-teaser.tsx       [Client] 블러 + 티저
    paywall-gate.tsx      [Client] 페이월 게이트 (3 상태)
    manual-payment-flow   [Client] 수동 결제 UI
    pending-card.tsx      [Client] 결제 대기 카드
    report-viewer.tsx     [Client] 리포트 뷰어 조립
lib/
  types/                  TypeScript 타입 정의
  constants/              상수 및 목 데이터
  utils/                  유틸리티 함수
  hooks/                  커스텀 훅 (usePolling 등)
public/fonts/PretendardVariable.woff2
```

---

## 리스크 테이블

| 리스크 | 영향도 | 완화 전략 |
|--------|--------|-----------|
| PretendardVariable.woff2 파일 크기 (2MB+) | 초기 로딩 지연 | 서브셋 생성 또는 CDN 폴백 준비 |
| `backdrop-filter` 모바일 성능 저하 | 저사양 기기 프레임 드롭 | `will-change: backdrop-filter` 힌트 적용 |
| 블러 fade-out 시 레이아웃 시프트 | 스크롤 위치 변경, UX 저하 | 섹션 고정 높이 설정 + `scrollY` 보존 로직 |
| 관리자 결제 확인 지연 | 사용자 불안감, 이탈 | 30분 경과 시 관리자 리마인더 발송 |
| 폴링 서버 부하 | API 호출 과다 | 30초 간격 + `visibilitychange` 기반 일시중지 |
| 카카오톡 딥링크 미지원 기기 | 결제 플로우 중단 | 딥링크 실패 시 웹 폴백 URL 제공 |

---

## 범위 제외 (Scope Exclusions)

다음 항목은 현재 SPEC의 범위에 포함되지 않으며, 후속 Phase에서 다룹니다:

1. **TossPayments PG 연동** (Phase 2): 자동 결제 처리, 카드/간편결제
2. **카카오톡 알림**: 결제 확인/거절 시 사용자 알림 발송
3. **인증/인가 (Auth)**: 로그인, 세션 관리, 역할 기반 접근 제어
4. **CI/CD 파이프라인**: 자동 빌드, 테스트, 배포 워크플로우
5. **프로덕션 배포**: Vercel/AWS 배포 설정, 도메인, SSL
6. **모니터링/로깅**: 에러 추적, 성능 모니터링, 분석 도구
7. **다국어 지원 (i18n)**: 한국어 이외 언어 지원

---

## 의존성 그래프

```
T1 -> T2 -> T3 (순차)
T3 -> T4 -> T5 -> T6 (순차)
T6 -> T7, T8, T9 (병렬)
T9 -> T10, T11 (병렬)
T10 + T11 -> T12
T9 -> T13 -> T14
T9 -> T15, T16, T17, T18 (병렬)
T15 + T16 + T17 + T18 -> T19
T9 -> T20 -> T21
T22, T23 (병렬) -> T24
T19 + T21 + T24 -> T25 -> T26
```

---

*최종 업데이트: 2026-04-04*
*버전: 1.0*
