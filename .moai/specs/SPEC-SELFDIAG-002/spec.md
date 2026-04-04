---
id: SPEC-SELFDIAG-002
version: "1.0.0"
status: "completed"
created: "2026-04-04"
updated: "2026-04-04"
author: ""
priority: "high"
---

# SPEC-SELFDIAG-002: AI 셀프 진단 피벗

## HISTORY

- 2026-04-04: 초안 생성 (줌 미팅 → AI 셀프 질의 전환)

---

## Environment

### 현재 상태 (SPEC-NEXTJS-INIT-001 완료)
- sigak-web/: Next.js 16 + TypeScript + Tailwind v4
- 3개 라우트: / (랜딩+예약), /dashboard (알바 4뷰), /report/[id] (리포트 뷰어)
- 랜딩: 예약 캘린더 기반 (날짜+시간 슬롯)
- 대시보드: 알바 전용 (대기열/인터뷰입력/지표/결제확인)
- 리포트: 8섹션 + 블러 티저 + 페이월 + 수동 결제
- 백엔드: FastAPI, 인메모리 저장, 결제 API 포함

### 목표 상태
- 알바 의존 완전 제거
- 유저 셀프 질의 폼 → AI 자동 분석 → 리포트 생성
- 즉시 시작 (예약/스케줄 없음)
- 가격 대폭 인하
- 기존 리포트 뷰어 + 블러 + 페이월 100% 재사용

### 기술 환경 (기존 유지)
- Node.js 20 LTS, Next.js 16, React 19, TypeScript 5.9+
- Tailwind CSS v4, pnpm, ESLint, Prettier
- FastAPI 백엔드 (기존 확장)

---

## Assumptions

1. 기존 질문 구조(코어 6개 + 티어별)는 셀프 질의에도 유효
2. 기존 분석 파이프라인(face.py, coordinate.py, llm.py) 재사용 가능
3. 사진은 유저가 직접 촬영/업로드 (얼굴 검출 가이드 제공)
4. 리포트 뷰어 + 블러 + 페이월은 변경 없이 재사용
5. 가격은 추후 확정 (constants에서 쉽게 변경 가능하도록)
6. 결제: Phase 1 수동(카카오톡) 유지

---

## Requirements

### R1: 셀프 질의 폼 [Ubiquitous]
시스템은 항상 유저가 직접 작성할 수 있는 멀티스텝 질의 폼을 제공해야 한다.
- R1.1: 3페이지 구성 (기본질문 → 고민+사진 → 티어별+제출)
- R1.2: 코어 6개 질문 (자기인식/추구미/셀럽/키워드/고민/루틴)
- R1.3: 티어별 추가 질문 (wedding 2개, creator 3개, basic 0개)
- R1.4: 진행률 바 (현재 페이지 / 전체 페이지)
- R1.5: 필수 필드 검증 (코어질문 최소 4개 작성)
- R1.6: localStorage 자동 저장 (작성 중 이탈 시 복구)

### R2: 즉시 시작 플로우 [Event-Driven]
WHEN 유저가 "지금 시작하기" 클릭 THEN 즉시 질의 플로우 시작
- R2.1: 랜딩 CTA → /start 라우트 이동
- R2.2: /start에서 티어 선택 + 기본정보(이름/연락처) 입력
- R2.3: 기본정보 제출 → user 생성 → /questionnaire 리다이렉트
- R2.4: 날짜/시간 예약 없음

### R3: 사진 업로드 [Event-Driven]
WHEN 유저가 사진 업로드 단계 도달 THEN 촬영/업로드 UI 표시
- R3.1: 정면 1장 필수 (측면은 선택)
- R3.2: 카메라 촬영 또는 파일 업로드 선택
- R3.3: 업로드 미리보기 + 재촬영
- R3.4: 얼굴 검출 가이드 (정면 응시, 밝은 조명 안내)

### R4: 자동 분석 파이프라인 [Event-Driven]
WHEN 유저가 질의+사진 제출 THEN 자동으로 분석 실행
- R4.1: POST /api/v1/questionnaire/{user_id}/submit
- R4.2: 백엔드 face.py → coordinate.py → llm.py 자동 체인
- R4.3: 분석 중 로딩 UI (예상 소요시간 안내)
- R4.4: 분석 완료 시 리포트 URL 제공

### R5: 분석 상태 관리 [State-Driven]
5단계 상태:
- registered: 유저 등록 완료
- submitted: 질의+사진 제출
- analyzing: 분석 실행 중
- reported: 리포트 생성 완료
- feedback_done: 피드백 수집 완료

### R6: 랜딩 페이지 업데이트 [Ubiquitous]
- R6.1: "예약하기" → "지금 시작하기" 텍스트 변경
- R6.2: booking-overlay → start-overlay (날짜/시간 제거)
- R6.3: 가격 업데이트 (상수에서 변경)
- R6.4: seats-section → 참여자 카운터로 변경
- R6.5: 전문가 섹션 유지

### R7: 알바 의존 제거 [Unwanted]
- R7.1: /dashboard 라우트 제거
- R7.2: queue-view, payments-view, payment-confirm-card 제거
- R7.3: 알바 결제 확인 API 제거
- R7.4: 관련 mock 데이터/타입 정리

### R8: 리포트 뷰어 재활용 [Ubiquitous]
기존 리포트 뷰어는 변경 없이 재사용한다.
- R8.1: 8개 섹션 컴포넌트 유지
- R8.2: 블러 티저 시스템 유지
- R8.3: PaywallGate + 결제 플로우 유지
- R8.4: 30초 폴링 + visibilitychange 유지

### R9: 백엔드 API 리팩토링 [Ubiquitous]
- R9.1: POST /questionnaire/{user_id}/submit 신규
- R9.2: GET /questionnaire/{user_id} 신규
- R9.3: POST /booking 간소화 (날짜/시간 제거)
- R9.4: dashboard/queue, dashboard/payments 제거
- R9.5: confirm-payment 제거

### R10: 빌드/환경 [Ubiquitous]
pnpm dev/build 정상, TS 에러 0, ESLint 에러 0

### R11: 비허용 행위 [Unwanted]
CSS-in-JS 문자열, 인라인 스타일, any 타입, CDN 폰트 금지

---

## Specifications

### S1: 신규/변경 디렉토리 구조

```
sigak-web/
├── app/
│   ├── start/
│   │   └── page.tsx                  # 즉시 시작 (/start)
│   ├── questionnaire/
│   │   ├── page.tsx                  # 셀프 질의 폼
│   │   └── complete/
│   │       └── page.tsx              # 분석 로딩 + 완료
│   ├── page.tsx                      # 랜딩 (수정: CTA → /start)
│   ├── report/[id]/page.tsx          # 리포트 (재사용)
│   └── dashboard/ → 제거
├── components/
│   ├── start/
│   │   └── start-overlay.tsx         # 간소화 시작 오버레이
│   ├── questionnaire/
│   │   ├── questionnaire-form.tsx    # 멀티스텝 폼
│   │   ├── questionnaire-step.tsx    # 스텝 렌더러
│   │   ├── photo-uploader.tsx        # 사진 업로드
│   │   ├── progress-bar.tsx          # 진행률
│   │   └── analysis-loader.tsx       # 분석 로딩 UI
│   ├── landing/ (수정)
│   ├── report/ (재사용)
│   └── ui/ (재사용)
├── lib/
│   ├── types/questionnaire.ts        # 신규
│   ├── constants/tiers.ts            # 가격 수정
│   └── (나머지 재사용)
```

### S2: 핵심 타입 정의

```typescript
// lib/types/questionnaire.ts
type QuestionnaireStatus = "registered" | "submitted" | "analyzing" | "reported" | "feedback_done";

interface QuestionnaireState {
  user_id: string;
  tier: "basic" | "creator" | "wedding";
  step: number;
  answers: Record<string, string>;
  photos: string[];
  status: QuestionnaireStatus;
  submitted_at: string | null;
  report_id: string | null;
}
```

### S3: 셀프 질의 폼 페이지 구성

```
Page 1: 기본 질문
  - 자기 인식 (필수, 3행)
  - 추구미 (필수, 3행)
  - 레퍼런스 셀럽 (2행)
  - 스타일 키워드 (2행)

Page 2: 고민 + 사진
  - 현재 고민 (필수, 3행)
  - 일상 루틴 (2행)
  - 사진 업로드 (정면 필수)

Page 3: 티어별 + 검토
  - [wedding] 웨딩 컨셉, 드레스 선호
  - [creator] 콘텐츠 스타일, 타겟 시청자, 채널 톤
  - [basic] 바로 검토
  - 전체 답변 검토 → 제출
```

---

## Traceability

| 요구사항 | 구현 파일 | 인수 조건 |
|--|--|--|
| R1 | components/questionnaire/* | AC-1 |
| R2 | app/start/, components/start/* | AC-2 |
| R3 | photo-uploader.tsx | AC-3 |
| R4 | 백엔드 API, analysis-loader | AC-4 |
| R5 | types/questionnaire.ts | AC-5 |
| R6 | app/page.tsx, components/landing/* | AC-6 |
| R7 | app/dashboard/ 제거 | AC-7 |
| R8 | components/report/* (변경 없음) | AC-8 |
| R9 | sigak/main.py | AC-9 |
| R10-R11 | 전체 | AC-10 |
