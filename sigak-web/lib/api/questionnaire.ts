// mock API 유틸리티
// 실제 백엔드 연동 시 fetch 호출로 교체

import type { QuestionnaireStatus } from "@/lib/types/questionnaire";

/** 설문 제출 시뮬레이션 (2-5초 딜레이) */
export async function submitQuestionnaire(
  userId: string,
  data: { answers: Record<string, string>; photos: string[] },
): Promise<{ success: boolean; report_id: string }> {
  // 네트워크 지연 시뮬레이션
  await new Promise((resolve) =>
    setTimeout(resolve, 2000 + Math.random() * 3000),
  );

  // userId, data를 사용하여 실제 API 호출로 대체 예정
  void userId;
  void data;

  return {
    success: true,
    report_id: "mock-report-id", // mock-report.ts와 일치
  };
}

// 상태 조회 시뮬레이션 - 호출할 때마다 상태 진행
let callCount = 0;
const statusSequence: QuestionnaireStatus[] = [
  "submitted",
  "analyzing",
  "analyzing",
  "reported",
];

/** 설문 상태 조회 시뮬레이션 */
export async function getQuestionnaireStatus(
  userId: string,
): Promise<{ status: QuestionnaireStatus; report_id: string | null }> {
  await new Promise((resolve) => setTimeout(resolve, 500));

  // userId를 사용하여 실제 API 호출로 대체 예정
  void userId;

  const idx = Math.min(callCount++, statusSequence.length - 1);
  const status = statusSequence[idx];

  return {
    status,
    report_id: status === "reported" ? "mock-report-id" : null,
  };
}

/** 테스트용 상태 초기화 */
export function resetQuestionnaireStatus(): void {
  callCount = 0;
}
