# SPEC-SELFDIAG-002: 구현 계획

## 전략

기존 sigak-web 코드 최대 재활용. 알바 의존 제거하고 유저 셀프 질의 → AI 자동 분석 플로우로 전환.
리포트 뷰어/블러/페이월/UI 컴포넌트는 변경 없이 재사용.

---

## Milestone 1: 셀프 질의 폼 (T1-T4)

**T1: 타입 + 상수 업데이트** [R1, R5]
- lib/types/questionnaire.ts 신규 (QuestionnaireState, QuestionnaireStatus)
- lib/constants/tiers.ts 가격 업데이트
- lib/types/booking.ts 간소화 (날짜/시간 제거)

**T2: 질의 폼 오케스트레이터** [R1]
- components/questionnaire/questionnaire-form.tsx
- 멀티스텝 상태 관리 (step, answers, photos)
- localStorage 자동저장/복구

**T3: 스텝 렌더러 + 진행률** [R1]
- components/questionnaire/questionnaire-step.tsx (질문 렌더링)
- components/questionnaire/progress-bar.tsx (페이지 진행률)
- 기존 questions.ts 상수 재사용

**T4: 사진 업로드** [R3]
- components/questionnaire/photo-uploader.tsx
- 카메라/파일 선택, 미리보기, 얼굴 가이드

## Milestone 2: 즉시 시작 플로우 (T5-T7)

**T5: /start 라우트** [R2]
- app/start/page.tsx
- components/start/start-overlay.tsx (티어+이름+연락처만)

**T6: 랜딩 페이지 수정** [R6]
- "예약하기" → "지금 시작하기"
- booking-overlay 제거 → /start 링크
- 가격/seats 텍스트 업데이트

**T7: /questionnaire 라우트** [R1, R2]
- app/questionnaire/page.tsx (질의 폼 페이지)
- app/questionnaire/complete/page.tsx (분석 로딩/완료)

## Milestone 3: 자동 분석 연동 (T8-T10)

**T8: 백엔드 API** [R9]
- POST /questionnaire/{user_id}/submit (통합 제출)
- GET /questionnaire/{user_id} (작성 중 상태)
- POST /booking 간소화

**T9: 분석 로딩 UI** [R4]
- components/questionnaire/analysis-loader.tsx
- 예상 소요시간 표시, 폴링으로 완료 감지

**T10: 리포트 연결** [R4, R8]
- 분석 완료 → /report/[id] URL 표시
- 기존 리포트 뷰어 그대로 연결

## Milestone 4: 알바 의존 제거 (T11-T12)

**T11: 대시보드 제거** [R7]
- app/dashboard/ 디렉토리 삭제
- components/dashboard/ 중 알바 전용 제거
  (queue-view, payments-view, payment-confirm-card)
- stat-card, stats-view는 향후 관리자 패널용 보존 가능

**T12: API + 데이터 정리** [R7, R9]
- dashboard/queue, dashboard/payments 엔드포인트 제거
- confirm-payment 엔드포인트 제거
- mock-data.ts에서 MOCK_QUEUE 제거
- mock-payments.ts 제거
- lib/types/dashboard.ts 정리

## Milestone 5: 검증 (T13-T14)

**T13: 빌드** [R10] - build/tsc/lint 에러 0
**T14: 전체 플로우** - 시작→질의→사진→분석→리포트→결제

---

## 아키텍처

```
유저 → 랜딩 (/) "지금 시작하기"
  → /start (티어+이름+연락처)
  → /questionnaire (3페이지 셀프 질의 + 사진)
  → POST /questionnaire/submit
  → /questionnaire/complete (분석 로딩)
  → /report/[id] (기존 리포트 뷰어 재사용)
  → 결제 (기존 페이월 재사용)
```

## 위험

| 위험 | 완화 |
|------|------|
| 유저가 적절한 사진 못 올림 | 얼굴 가이드 + 예시 이미지 |
| 질의 이탈률 높음 | localStorage 저장 + 진행률 바 |
| 분석 시간 김 | 로딩 UI + 폴링 |
| 가격 미확정 | 상수 분리, 쉽게 변경 |

## 범위 외

- 토스페이먼츠 PG 자동 결제 (별도 SPEC)
- 카카오톡 자동 알림
- 관리자 대시보드 (별도 SPEC)
- CLIP 실제 구현 (mock 유지)
- CI/CD, 프로덕션 배포
