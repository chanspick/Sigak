// 설문 진단 타입 정의

/** 설문 상태 */
export type QuestionnaireStatus =
  | "registered"
  | "submitted"
  | "analyzing"
  | "reported"
  | "feedback_done";

/** 설문 전체 상태 */
export interface QuestionnaireState {
  user_id: string;
  tier: "basic" | "creator" | "wedding";
  step: number;
  answers: Record<string, string>;
  photos: string[]; // base64 또는 object URL
  status: QuestionnaireStatus;
  submitted_at: string | null;
  report_id: string | null;
}

/** 시작 폼 데이터 */
export interface StartFormData {
  name: string;
  phone: string;
  tier: "basic" | "creator" | "wedding";
}
