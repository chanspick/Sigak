/**
 * Sia conversation API types — Phase H (14 타입 확장).
 *
 * 백엔드 대응:
 *   sigak/schemas/sia_state.py::MsgType enum.
 *   enum .value 는 소문자 + 언더스코어 (예: "opening_declaration").
 *   이 파일의 MsgType union 은 그 .value 와 1:1 일치해야 한다.
 *
 * ⚠ 현 상태 (Phase H3 완료 시점):
 *   - 프론트 타입 14종 선행. 백엔드 enum 확장 (check_in / re_entry / range_disclosure)
 *     은 Phase H2 재개 시 수행 예정. 실 API 호출부 (lib/api/sia.ts — 아직 없음) 는
 *     Phase H5 완료 전까지 이 파일을 import 하지 않는다.
 *   - 현행 프론트 컴포넌트 (SiaStream 등) 는 @/lib/types/sia.legacy 를 경유한다.
 *   - H5 완료 시 컴포넌트 import 경로만 legacy → 본 파일로 1줄 전환.
 *
 * Phase H 변경 요약 (legacy 대비):
 *   - 제거: response_mode / choices / turn_count / conversation_id 네이밍
 *   - 추가: msg_type / progress_percent / countdown_seconds / ended_by_timeout
 *   - 타입 11 → 14 (check_in / re_entry / range_disclosure). 세션 #6 v2 확정.
 *   - M1 결합 출력 (OPENING_DECLARATION + OBSERVATION) 은 assistant_messages
 *     배열 길이 2 로 표현 — 타입 상 특별 처리 없음.
 *   - 신규 "관리" 버킷: check_in / re_entry / range_disclosure (트리거 기반,
 *     비율 강제 없음). 기존 수집/이해/여백 3 버킷과 분리.
 */

// ─── MsgType ───────────────────────────────────
// 백엔드 schemas/sia_state.py::MsgType(str, Enum) 의 .value 와 정확히 동일.

export type MsgType =
  | "opening_declaration"
  | "observation"
  | "probe"
  | "extraction"
  | "empathy_mirror"
  | "recognition"
  | "confrontation"
  | "meta_rebuttal"
  | "evidence_defense"
  | "diagnosis"
  | "soft_walkback"
  // ── 관리 버킷 (세션 #6 v2, 14 타입 확장) ──
  | "check_in"
  | "re_entry"
  | "range_disclosure";

/** Runtime iterable (폼/셀렉트/테스트용). readonly tuple 보장. */
export const MSG_TYPES = [
  "opening_declaration",
  "observation",
  "probe",
  "extraction",
  "empathy_mirror",
  "recognition",
  "confrontation",
  "meta_rebuttal",
  "evidence_defense",
  "diagnosis",
  "soft_walkback",
  "check_in",
  "re_entry",
  "range_disclosure",
] as const satisfies readonly MsgType[];

// ─── 버킷 (백엔드 frozensets 와 대응, 참고용) ───
// 세션 #4 v2 §2: 수집 30 : 이해 50 : 여백 20 + 관리 (트리거, 비율 강제 없음).

export const COLLECTION_TYPES: readonly MsgType[] = [
  "observation",
  "probe",
  "extraction",
] as const;

export const UNDERSTANDING_TYPES: readonly MsgType[] = [
  "empathy_mirror",
  "recognition",
  "diagnosis",
  "soft_walkback",
] as const;

export const WHITESPACE_TYPES: readonly MsgType[] = [
  "opening_declaration",
] as const;

export const CONFRONT_TYPES: readonly MsgType[] = [
  "confrontation",
  "meta_rebuttal",
  "evidence_defense",
] as const;

/**
 * 관리 버킷 (세션 #6 v2 §8).
 * - check_in: A-9 단답 연타 / A-10 이탈 신호 응대.
 * - re_entry: check_in 직후 축 전환 복귀.
 * - range_disclosure: A-11 과몰입 완화 공개.
 * 트리거 기반으로 호출, 비율 강제 없음.
 */
export const MANAGEMENT_TYPES: readonly MsgType[] = [
  "check_in",
  "re_entry",
  "range_disclosure",
] as const;

export const QUESTION_REQUIRED_TYPES: readonly MsgType[] = [
  "observation",
  "probe",
  "extraction",
  "recognition",
  "confrontation",
  "meta_rebuttal",
  "evidence_defense",
] as const;

export const QUESTION_FORBIDDEN_TYPES: readonly MsgType[] = [
  "opening_declaration",
  "empathy_mirror",
  "diagnosis",
  "soft_walkback",
  // 관리 버킷 3종 전부 질문 금지 (사용자 ⑥ 확정).
  "check_in",
  "re_entry",
  "range_disclosure",
] as const;

// ─── Type guards ───────────────────────────────
// 런타임 체크 + type narrowing. 백엔드로부터 받은 값의 신뢰 검증 / 분기 용.

/** 임의의 값이 유효한 MsgType 인지 확인. 백엔드 응답 방어선. */
export function isMsgType(value: unknown): value is MsgType {
  return (
    typeof value === "string" &&
    (MSG_TYPES as readonly string[]).includes(value)
  );
}

export function isCollectionType(t: MsgType): boolean {
  return (COLLECTION_TYPES as readonly string[]).includes(t);
}

export function isUnderstandingType(t: MsgType): boolean {
  return (UNDERSTANDING_TYPES as readonly string[]).includes(t);
}

export function isWhitespaceType(t: MsgType): boolean {
  return (WHITESPACE_TYPES as readonly string[]).includes(t);
}

export function isConfrontType(t: MsgType): boolean {
  return (CONFRONT_TYPES as readonly string[]).includes(t);
}

export function isManagementType(t: MsgType): boolean {
  return (MANAGEMENT_TYPES as readonly string[]).includes(t);
}

export function isQuestionRequired(t: MsgType): boolean {
  return (QUESTION_REQUIRED_TYPES as readonly string[]).includes(t);
}

export function isQuestionForbidden(t: MsgType): boolean {
  return (QUESTION_FORBIDDEN_TYPES as readonly string[]).includes(t);
}

// ─── Core UI primitives ────────────────────────

export type SiaRole = "sia" | "user";

/**
 * Sia/유저 개별 메시지. 버블 단위 렌더링의 최소 단위.
 *
 * - 1 SiaMessage = 1 bubble group (Sia 면 parseSiaMessage 로 문장 분할되어
 *   여러 버블 렌더링될 수 있음; user 면 항상 1 버블).
 * - msg_type 은 user 메시지엔 null.
 */
export interface SiaMessage {
  id: string;
  role: SiaRole;
  content: string;
  msg_type: MsgType | null;
  created_at: string; // ISO 8601
}

/**
 * 클라이언트 보관 세션 상태. React store / Zustand / Redux 등의 상태 루트.
 */
export interface SiaSessionState {
  session_id: string;
  messages: SiaMessage[];
  /** JSON 수집률 0-100. 상단 hairline progress 에 연결. */
  progress_percent: number;
  /** 남은 초. 300 → 0. 30초 이하에서만 UI 표기. */
  countdown_seconds: number;
  is_complete: boolean;
  ended_by_timeout: boolean;
  /** ISO 8601 세션 시작 시각. */
  started_at: string;
}

// ─── REST API contracts (Phase H5 백엔드 완성 시 실제 payload) ───

export interface SiaStartRequest {
  user_name?: string | null;
  ig_handle?: string | null;
}

export interface SiaStartResponse {
  session_id: string;
  /**
   * M1 결합 출력 — OPENING_DECLARATION + OBSERVATION 2개가 배열로 옴.
   * 일반 턴은 길이 1.
   */
  assistant_messages: SiaMessage[];
  progress_percent: number;
  countdown_seconds: number;
  started_at: string;
}

export interface SiaMessageRequest {
  session_id: string;
  user_message: string;
}

export interface SiaMessageResponse {
  session_id: string;
  /** 보통 길이 1. 추후 결합 케이스 확장 여지로 배열 유지. */
  assistant_messages: SiaMessage[];
  progress_percent: number;
  countdown_seconds: number;
  is_complete: boolean;
  ended_by_timeout: boolean;
}

export interface SiaEndRequest {
  session_id: string;
  /** 자발 종료 vs 5:00 만료 구분. 프론트는 기본 false. */
  ended_by_timeout?: boolean;
}

export interface SiaEndResponse {
  session_id: string;
  ended_by_timeout: boolean;
  redirect: string;
}

// ─── 410 Session Expired ───────────────────────

export interface SiaSessionExpiredResponse {
  message: string;
  next: "extracting";
  redirect: string;
}

// ─── Legacy bridge (H5 전환 편의 용) ─────────────
// 현행 SiaStream 등은 SiaTurn 을 쓰고 있음. H5 전환 시 컴포넌트 import 를
// @/lib/types/sia 로 옮기면서 즉시 깨지지 않도록 alias 유지.
// 새 코드는 SiaMessage 를 직접 쓸 것.

export type SiaTurnRole = SiaRole;

export interface SiaTurn {
  role: SiaTurnRole;
  content: string;
}
