# SPEC-NEXTJS-INIT-001: 수락 기준 (Acceptance Criteria)

---

## AC-1: 프로젝트 초기화

```gherkin
Feature: Next.js 프로젝트 구조 검증

  Scenario: 프로젝트 디렉토리 구조가 올바르게 생성됨
    Given create-next-app으로 프로젝트가 생성되었을 때
    Then app/ 디렉토리가 존재해야 한다
    And app/layout.tsx, app/page.tsx 파일이 존재해야 한다
    And tsconfig.json에 strict: true가 설정되어야 한다
    And pnpm-lock.yaml 파일이 존재해야 한다

  Scenario: 개발 서버에서 3개 라우트가 정상 동작함
    Given pnpm dev로 개발 서버가 실행되었을 때
    Then /, /dashboard, /report/[id]가 200 응답을 반환해야 한다
```

---

## AC-2: 디자인 시스템

```gherkin
Feature: 디자인 시스템 적용 검증

  Scenario: 테마 색상이 올바르게 적용됨
    Then --color-bg=#F3F0EB, --color-fg=#000, --color-blur-bg=rgba(243,240,235,0.7)

  Scenario: 폰트가 로컬에서 로드됨
    Then Noto Serif KR(next/font/google) + PretendardVariable(public/fonts/) 로드, CDN 폰트 요청 0건

  Scenario: 텍스트 선택 스타일이 적용됨
    Then ::selection 배경색/텍스트색이 커스텀 색상이어야 한다
```

---

## AC-3: 랜딩 페이지

```gherkin
Feature: 랜딩 페이지 렌더링 및 상호작용

  Scenario: 7개 섹션이 모두 렌더링됨
    Given / 경로에 접속했을 때
    Then NavBar, HeroSection, TierSection, ExpertSection, SeatsSection, CTASection, Footer가 렌더링되어야 한다

  Scenario: 스크롤 시 섹션이 순차적으로 나타남
    Then RevealOnScroll이 Intersection Observer로 fade-in 애니메이션 적용

  Scenario: 예약 오버레이 전체 플로우
    Given CTA 버튼 클릭 시 오버레이 표시
    Then 티어선택->날짜->시간->정보입력->결제시뮬레이션 5단계 완료

  Scenario: 모바일 반응형 (768px)
    Then NavBar 햄버거 메뉴, 단일 컬럼 배치
```

---

## AC-4: 대시보드

```gherkin
Feature: 대시보드 4-뷰 전환 및 기능

  Scenario: 4개 뷰 전환
    Then queue/entry/stats/payments 탭 전환 정상 동작

  Scenario: URL 파라미터 동기화
    Given /dashboard?view=payments 접속 시 결제 뷰 즉시 표시

  Scenario: 티어별 사전 질문 + 진행률 바 표시
```

---

## AC-5: 리포트 뷰어 (Free 접근)

```gherkin
Feature: Free 접근 레벨 리포트 뷰어

  Scenario: Free 사용자에게 3개 섹션 공개, 5개 블러
    Given access_level이 'free'인 리포트에 접속했을 때
    Then Cover, ExecutiveSummary, FaceStructure 완전 공개
    And SkinAnalysis, CoordinateMap, ActionPlan, CelebReference, TrendContext 블러 + 티저 가시

  Scenario: PaywallGate 2개 올바른 위치
    Then Standard PaywallGate=FaceStructure 다음, Full PaywallGate=ActionPlan 다음
```

---

## AC-6: 블러 티저 규칙

```gherkin
Feature: 섹션별 블러 및 티저 규칙 (R7 기준)

  Scenario: CSS 블러 효과
    Then backdrop-filter: blur(12px), 오버레이 배경: rgba(243,240,235,0.7)

  Scenario: 각 섹션 티저
    Then SkinAnalysis: 제목+첫 지표 카테고리 가시
    And CoordinateMap: 제목+축 레이블 가시
    And ActionPlan: 제목+첫 단계 제목 가시
    And CelebReference: 제목+매칭 카테고리 가시
    And TrendContext: 제목+시즌 키워드 가시
```

---

## AC-7: 수동 결제 (Standard 업그레이드)

```gherkin
Feature: Standard 업그레이드 수동 결제 플로우

  Scenario: 은행 정보 표시
    Then 은행명, 계좌번호(복사), 예금주, Standard 금액 표시

  Scenario: 카카오톡 딥링크
    Then kakaotalk:// 딥링크 호출

  Scenario: 송금 완료 -> 대기 -> 확인 -> 블러 해제
    Then POST payment-request -> PendingCard -> 30초 폴링 -> 관리자 확인 -> fade-out 0.6s + 스크롤 유지
```

---

## AC-8: 수동 결제 (Full 업그레이드)

```gherkin
Feature: Full 업그레이드

  Scenario: Full 결제 확인 후 전체 공개
    Then access_level='full', 모든 블러 fade-out 0.6s, PaywallGate 전부 제거, 8개 섹션 완전 공개

  Scenario: 스크롤 위치 보존
    Then window.scrollY 애니메이션 전후 동일
```

---

## AC-9: 결제 확인 대시보드

```gherkin
Feature: 관리자 결제 확인 대시보드

  Scenario: pending 목록 표시 + 확인/거절 버튼 + 오늘 완료 목록
```

---

## AC-10: 결제 백엔드 API

```gherkin
Feature: 결제 관련 API

  Scenario: POST /api/payment-request -> {requestId, status:'pending', createdAt}
  Scenario: POST /api/confirm-payment (confirm) -> access_level 업그레이드, pending_level='none'
  Scenario: POST /api/confirm-payment (reject) -> pending_level='none', access_level 유지
  Scenario: GET /api/dashboard/payments -> {pending[], todayCompleted[]}
  Scenario: GET /api/report/[id] -> access_level + pending_level 포함
```

---

## AC-11: 빌드 및 린트

```gherkin
Feature: 빌드 및 코드 품질

  Scenario: pnpm build 에러 0건
  Scenario: tsc --noEmit 에러 0건
  Scenario: pnpm lint 에러 0건
```

---

## AC-12: 비허용 패턴

```gherkin
Feature: 금지된 코드 패턴

  Scenario: CSS-in-JS 0건 (styled-components, emotion)
  Scenario: 인라인 style={{ }} 0건
  Scenario: TypeScript any 타입 0건
  Scenario: CDN 폰트 참조 0건
```

---

## 엣지 케이스 (E1-E6)

### E1: Full 접근 -> 8개 섹션 완전 공개, PaywallGate 0개

### E2: Fade-out 시 scrollY 불변, 레이아웃 시프트 없음

### E3: 미송금 + 완료 클릭 -> 관리자 거절 -> pending_level='none', 블러 복원, 거절 메시지

### E4: 24시간 미확인 -> status='cancelled', pending_level='none', 재결제 가능

### E5: Standard -> Full 순차 결제 -> 나머지 블러 해제, access_level='full'

### E6: 관리자 30분+ 미응답 -> 리마인더 발송, PendingCard 경과 시간 계속 표시

---

## 품질 게이트 체크리스트

- [ ] pnpm build 에러 0건
- [ ] tsc --noEmit 에러 0건
- [ ] pnpm lint 에러 0건
- [ ] CSS-in-JS 0건
- [ ] 인라인 style 0건
- [ ] any 타입 0건
- [ ] CDN 폰트 0건
- [ ] 모든 컴포넌트 TypeScript 타입 정의 완료
- [ ] Server/Client 경계 명확
- [ ] 블러 fade-out 레이아웃 시프트 없음
- [ ] 30초 폴링 + visibilitychange 동작
- [ ] 모바일(375px) + 데스크톱(1440px) 반응형
- [ ] 카카오톡 딥링크 동작
- [ ] 결제 확인/거절 후 상태 즉시 반영

---

## 완료 정의 (Definition of Done)

1. **빌드 무결성**: pnpm build, tsc --noEmit, pnpm lint 모두 에러 0건
2. **기능 완전성**: 8 마일스톤 26 태스크 완료, AC-1~AC-12 전체 충족
3. **시각적 품질**: 랜딩/대시보드/리포트/결제 플로우 시각 검증 완료
4. **엣지 케이스**: E1-E6 모든 시나리오 정상 동작
5. **코드 품질**: AC-12 비허용 패턴 통과, strict mode, Server/Client 경계 명확

---

*최종 업데이트: 2026-04-04*
*버전: 1.0*
