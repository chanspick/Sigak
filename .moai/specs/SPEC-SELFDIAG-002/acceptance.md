# SPEC-SELFDIAG-002: 인수 조건

---

## AC-1: 셀프 질의 폼
Given /questionnaire?user_id=X&tier=basic 접근시 -> 3페이지 멀티스텝 폼 렌더링, 코어 6개 질문 표시, 진행률 바 동작, 필수 미입력시 다음 페이지 이동 불가

## AC-2: 즉시 시작 플로우
Given 랜딩 "지금 시작하기" 클릭시 -> /start 이동, 티어 선택 + 이름/연락처 입력, 제출 -> /questionnaire 리다이렉트

## AC-3: 사진 업로드
Given 질의 폼 2페이지 도달시 -> 카메라/파일 선택 가능, 미리보기 표시, 정면 1장 미업로드시 제출 불가

## AC-4: 자동 분석
Given 질의+사진 제출시 -> 분석 로딩 UI 표시, 완료시 /report/[id] URL 표시

## AC-5: 상태 관리
registered -> submitted -> analyzing -> reported 순서 전환 정상

## AC-6: 랜딩 업데이트
Given / 접근시 -> "지금 시작하기" 텍스트, 날짜/시간 선택 없음, 새 가격 표시

## AC-7: 알바 의존 제거
/dashboard 접근시 404, queue-view/payments-view 컴포넌트 코드 없음

## AC-8: 리포트 뷰어 정상
기존 블러 티저 + 페이월 + 결제 플로우 동일 동작, 5단계 access_level 정상

## AC-9: 백엔드 API
POST /questionnaire/{user_id}/submit 정상, GET /questionnaire/{user_id} 정상, dashboard/queue + confirm-payment 제거됨

## AC-10: 빌드
pnpm build 0, tsc 0, lint 0, CSS-in-JS 0, 인라인 스타일 0, any 0, CDN 0

---

## 엣지 케이스

- E1: 질의 작성 중 브라우저 닫기 -> localStorage에서 복구
- E2: 사진 없이 제출 시도 -> 차단 + 안내
- E3: 분석 파이프라인 실패 -> 에러 메시지 + 재시도
- E4: 동일 유저 재접속 -> 기존 작성분 로드
- E5: basic 티어 -> 3페이지에서 티어별 질문 없이 바로 검토

---

## Quality Gate

- [ ] pnpm build + tsc + lint 에러 0
- [ ] 시작 -> 질의 -> 사진 -> 분석 -> 리포트 전체 플로우
- [ ] 기존 리포트 뷰어 + 블러 + 결제 정상
- [ ] 모바일 768px 반응형
- [ ] localStorage 저장/복구
- [ ] 비허용 패턴 0건

## Definition of Done

1. Quality Gate 전체 통과
2. /start -> /questionnaire -> /report 전체 플로우
3. 기존 리포트 뷰어 + 페이월 정상 동작
4. /dashboard 제거 완료
5. 알바 전용 API 제거 완료
