/**
 * Sia conversation API types — LEGACY (v2 Priority 1 D6).
 *
 * ⚠ LEGACY / DEPRECATED: Phase A-F 시점 스키마.
 *   STEP 2-G v4 cutover 로 백엔드의 response_mode / choices / name_fallback 는 제거됨.
 *   본 파일은 SiaStream 등 기존 컴포넌트의 SiaTurn shape 만 import 되는 상태로 남겨둠.
 *   Phase H5 완료 시 컴포넌트 import 경로를 @/lib/types/sia 로 전환하면서 본 파일 폐기.
 *
 *  신규 Phase H 버전은 @/lib/types/sia 참조 (MsgType + progress_percent 기반).
 *
 * Backend: sigak/routes/sia.py (FastAPI).
 * Session TTL: Redis 3600s. 410 on expiry → flush backup + redirect.
 */

/** @deprecated STEP 2-G 이후 백엔드 미제공. 참조 금지. */
export type SiaResponseMode = "choices" | "freetext" | "name_fallback";

// ─── /api/sia/start ────────────────────────────

export interface SiaStartRequest {
  /** nullable for Apple-login users with no Korean name */
  user_name?: string | null;
  ig_handle?: string | null;
}

export interface SiaStartResponse {
  conversation_id: string;
  assistant_message: string;
  response_mode: SiaResponseMode;
  choices: string[];
  turn_count: number;
  status: "active";
}

// ─── /api/sia/message ──────────────────────────

export interface SiaMessageRequest {
  conversation_id: string;
  user_message: string;
}

export interface SiaMessageResponse {
  conversation_id: string;
  assistant_message: string;
  response_mode: SiaResponseMode;
  choices: string[];
  turn_count: number;
  status: "active" | "ending_soon" | "closed";
}

// ─── /api/sia/end ──────────────────────────────

export interface SiaEndRequest {
  conversation_id: string;
}

export interface SiaEndResponse {
  status: "extracting";
  redirect: "/onboarding/extracting";
}

// ─── 410 Session Expired ───────────────────────

export interface SiaSessionExpiredResponse {
  message: string;
  next: "extracting";
  redirect: "/onboarding/extracting";
}

// ─── Client-side conversation turn (UI shape) ──

export type SiaTurnRole = "sia" | "user";

export interface SiaTurn {
  role: SiaTurnRole;
  content: string;
}
