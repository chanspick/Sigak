/**
 * Sia conversation API types — LEGACY (v2 Priority 1 D6).
 *
 * ⚠ LEGACY: Phase A-F 시점 스키마. 4지선다 (response_mode: "choices") + turn_count
 *  기반. Phase H 전환 완료 전까지 실 API 호출부 유지용.
 *
 *  신규 Phase H 버전은 @/lib/types/sia 참조 (MsgType + progress_percent 기반).
 *  H5 백엔드 라우트 재작성 완료 시 import 경로 전환 예정.
 *
 * Backend: sigak/routes/sia.py (FastAPI).
 * Session TTL: Redis 3600s. 410 on expiry → flush backup + redirect.
 *
 * Usage (legacy):
 *   POST /api/sia/start     → SiaStartResponse
 *   POST /api/sia/message   → SiaMessageResponse | 410 SiaSessionExpiredResponse
 *   POST /api/sia/end       → SiaEndResponse
 */

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
