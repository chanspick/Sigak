// 인터뷰 질문 타입 정의

/** 질문 입력 유형 */
export type QuestionType = "text" | "single_select" | "multi_select" | "yes_no";

/** 선택지 옵션 */
export interface SelectOption {
  value: string;
  label: string;
  /** 선택지 아래 보조 설명 */
  description?: string;
}

/** 인터뷰 질문 (통합 타입) */
export interface InterviewQuestion {
  key: string;
  label: string;
  /** 질문 유형 (기본: text) */
  type?: QuestionType;
  /** textarea placeholder (text 타입) */
  placeholder?: string;
  /** textarea 줄 수 (text 타입) */
  rows?: number;
  /** 질문 아래 보조 설명 */
  description?: string;
  /** 선택 옵션 (single_select / multi_select) */
  options?: SelectOption[];
  /** multi_select 최대 선택 수 */
  maxSelect?: number;
  /** 필수 여부 (기본: true) */
  required?: boolean;
}
