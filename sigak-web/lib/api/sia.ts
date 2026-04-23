/**
 * Sia chat API 클라이언트 — `/api/v1/sia/chat/{start,message,end}`.
 *
 * 계약 adapter 레이어:
 *   백엔드 D6 실 계약 (conversation_id / opening_message / response_mode / choices)
 *   → 프론트 friendly shape (sessionId / openingMessage / isComplete)
 *
 * Phase H5 완료 시 어댑터만 제거. useSiaSession 등 호출부는 무변경.
 *
 * 에러 분류 (SiaApiError):
 *   - network  : fetch 실패 (오프라인 / DNS / CORS)
 *   - timeout  : AbortController 15s 초과
 *   - server   : 4xx / 5xx (401·410 제외)
 *   - auth     : 401 (JWT 만료)
 *   - expired  : 410 (Redis TTL 만료 = 세션 종료)
 */

import { ApiError, authFetch } from "./fetch";

// ─────────────────────────────────────────────
//  Timeout
// ─────────────────────────────────────────────

const SIA_TIMEOUT_MS = 15_000;

function withTimeout(): { signal: AbortSignal; cancel: () => void } {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), SIA_TIMEOUT_MS);
  return { signal: ctrl.signal, cancel: () => clearTimeout(timer) };
}

// ─────────────────────────────────────────────
//  Error classification
// ─────────────────────────────────────────────

export type SiaErrorCode =
  | "network"
  | "timeout"
  | "server"
  | "auth"
  | "expired";

export class SiaApiError extends Error {
  readonly code: SiaErrorCode;
  readonly status?: number;

  constructor(code: SiaErrorCode, status?: number, message?: string) {
    super(message ?? code);
    this.name = "SiaApiError";
    this.code = code;
    this.status = status;
  }
}

function classifySiaError(err: unknown): SiaApiError {
  if (err instanceof SiaApiError) return err;

  // AbortController timeout
  if (err instanceof DOMException && err.name === "AbortError") {
    return new SiaApiError("timeout");
  }

  // authFetch ApiError (status 기반)
  if (err instanceof ApiError) {
    if (err.status === 401) {
      return new SiaApiError("auth", 401, err.message);
    }
    if (err.status === 410) {
      return new SiaApiError("expired", 410, err.message);
    }
    return new SiaApiError("server", err.status, err.message);
  }

  // fetch 자체 실패 (네트워크 / CORS)
  if (err instanceof TypeError) {
    return new SiaApiError("network");
  }

  // 알 수 없는 에러는 server 로 폴백
  const msg = err instanceof Error ? err.message : "unknown error";
  return new SiaApiError("server", undefined, msg);
}

// ─────────────────────────────────────────────
//  Backend D6 raw shapes (internal)
// ─────────────────────────────────────────────

type BackendResponseMode = "choices" | "freetext" | "name_fallback";

interface BackendStartResponse {
  conversation_id: string;
  opening_message: string;
  turn_count: 0;
  response_mode: BackendResponseMode;
  choices: string[];
}

interface BackendMessageResponse {
  conversation_id: string;
  assistant_message: string;
  turn_count: number;
  status: "active" | "ending_soon" | "closed";
  response_mode: BackendResponseMode;
  choices: string[];
}

interface BackendEndResponse {
  conversation_id: string;
  status: "ended";
  messages_persisted: number;
  extraction_queued: boolean;
}

// ─────────────────────────────────────────────
//  Frontend-friendly result shapes (exported)
// ─────────────────────────────────────────────

/**
 * /chat/start 결과.
 * openingMessage 는 raw 문자열 — 여러 문장 가능. useSiaSession 이
 * parseSiaMessage 로 split 하여 버블 여러 개로 렌더 (M1 결합 효과).
 */
export interface SiaStartResult {
  sessionId: string;
  openingMessage: string;
  turnCount: number;
}

export interface SiaSendParams {
  sessionId: string;
  text: string;
}

export interface SiaSendResult {
  sessionId: string;
  assistantMessage: string;
  turnCount: number;
  /** `status === "closed"` 이면 true — useSiaSession 이 completed 로 전환. */
  isComplete: boolean;
}

export type SiaEndReason = "completed" | "timeout" | "exit";

export interface SiaEndParams {
  sessionId: string;
  reason: SiaEndReason;
}

export interface SiaEndResult {
  sessionId: string;
  messagesPersisted: number;
  extractionQueued: boolean;
}

// ─────────────────────────────────────────────
//  API surface
// ─────────────────────────────────────────────

/**
 * 새 Sia 세션 시작. 첫 Sia 턴(오프닝)을 포함해 반환.
 * 백엔드가 현재 M1 결합 출력을 단일 문자열로 내려주므로, 프론트에서
 * 마침표 기준 split 필요 (SiaStream.parseSiaMessage 이용).
 */
export async function startSiaChat(): Promise<SiaStartResult> {
  const { signal, cancel } = withTimeout();
  try {
    const raw = await authFetch<BackendStartResponse>(
      "/api/v1/sia/chat/start",
      { method: "POST", json: {}, signal },
    );
    return {
      sessionId: raw.conversation_id,
      openingMessage: raw.opening_message,
      turnCount: raw.turn_count,
    };
  } catch (err) {
    throw classifySiaError(err);
  } finally {
    cancel();
  }
}

/**
 * 유저 메시지 전송 후 Sia 응답 수신.
 * 410 수신 시 `expired` 에러 — 세션 TTL 만료. 호출부는 세션 종료로 처리.
 */
export async function sendSiaMessage(
  params: SiaSendParams,
): Promise<SiaSendResult> {
  const { signal, cancel } = withTimeout();
  try {
    const raw = await authFetch<BackendMessageResponse>(
      "/api/v1/sia/chat/message",
      {
        method: "POST",
        json: {
          conversation_id: params.sessionId,
          user_message: params.text,
        },
        signal,
      },
    );
    return {
      sessionId: raw.conversation_id,
      assistantMessage: raw.assistant_message,
      turnCount: raw.turn_count,
      isComplete: raw.status === "closed",
    };
  } catch (err) {
    throw classifySiaError(err);
  } finally {
    cancel();
  }
}

/**
 * 명시 종료 — 유저의 "대화 끝내기" 또는 로컬 카운트다운 만료 시 호출.
 * 백엔드는 이 호출 후 extraction BackgroundTask 를 큐잉 (REQ-SIA-008).
 *
 * `reason` 은 클라이언트 telemetry 목적 — 백엔드는 현재 `conversation_id` 만
 * 요구하므로 프론트에서 로컬 로그/분석 용도로만 사용 (네트워크 전송 X).
 */
export async function endSiaChat(
  params: SiaEndParams,
): Promise<SiaEndResult> {
  const { signal, cancel } = withTimeout();
  try {
    const raw = await authFetch<BackendEndResponse>("/api/v1/sia/chat/end", {
      method: "POST",
      json: { conversation_id: params.sessionId },
      signal,
    });
    return {
      sessionId: raw.conversation_id,
      messagesPersisted: raw.messages_persisted,
      extractionQueued: raw.extraction_queued,
    };
  } catch (err) {
    throw classifySiaError(err);
  } finally {
    cancel();
  }
}
