// authFetch — JWT Bearer 헤더 자동 부착 래퍼 (MVP v1.1 phase B)
//
// 새 MVP 엔드포인트(/api/v1/tokens/*, /api/v1/payments/*, /api/v1/auth/me)는
// 모두 Bearer JWT 필수. 기존 client.ts의 헬퍼들은 당분간 그대로 두고 —
// 새 호출부는 이 모듈을 쓴다. 레거시 전환은 refactor backlog에서 일괄 처리.

import { clearToken, getToken } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ngrok 경고 우회 헤더 (기존 client.ts와 동일)
const COMMON_HEADERS: Record<string, string> = {
  "ngrok-skip-browser-warning": "true",
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body: unknown = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** 401 응답 시 토큰 정리 + redirect 여부 옵션. 기본은 false (호출부가 처리). */
export interface AuthFetchOptions extends Omit<RequestInit, "body"> {
  /** JSON 직렬화할 body. FormData면 raw로 넘겨야 하므로 ``rawBody`` 사용. */
  json?: unknown;
  /** multipart 등 raw body. */
  rawBody?: BodyInit;
  /** 401 수신 시 자동으로 홈으로 리다이렉트할지 (기본: false) */
  redirectOn401?: boolean;
}

/** Bearer JWT 헤더가 자동 부착된 fetch 래퍼.
 *
 * 사용 예:
 *   const balance = await authFetch<BalanceResponse>("/api/v1/tokens/balance");
 *   const order = await authFetch<PurchaseIntentResponse>(
 *     "/api/v1/tokens/purchase-intent",
 *     { method: "POST", json: { pack_code: "starter" } }
 *   );
 */
export async function authFetch<T = unknown>(
  path: string,
  options: AuthFetchOptions = {},
): Promise<T> {
  const { json, rawBody, redirectOn401 = false, ...init } = options;

  const headers = new Headers(init.headers);
  // Bearer 부착 — 없으면 서버가 401 리턴하도록 둠
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  // 공통 헤더 덧붙이기 (덮어쓰지는 않음)
  for (const [key, value] of Object.entries(COMMON_HEADERS)) {
    if (!headers.has(key)) headers.set(key, value);
  }

  let body: BodyInit | undefined;
  if (json !== undefined) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    body = JSON.stringify(json);
  } else if (rawBody !== undefined) {
    body = rawBody;
  }

  const url = path.startsWith("http") ? path : `${API_URL}${path}`;
  const response = await fetch(url, { ...init, headers, body });

  if (response.status === 401) {
    clearToken();
    if (redirectOn401 && typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new ApiError(401, "인증이 만료되었습니다");
  }

  if (!response.ok) {
    let errBody: unknown = null;
    let message = `서버 오류 (${response.status})`;
    try {
      errBody = await response.json();
      if (errBody && typeof errBody === "object") {
        const b = errBody as Record<string, unknown>;
        if (typeof b.detail === "string") message = b.detail;
        else if (typeof b.message === "string") message = b.message;
      }
    } catch {
      // JSON 파싱 실패 — 기본 메시지
    }
    throw new ApiError(response.status, message, errBody);
  }

  // 204 No Content 또는 빈 body 대응
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}

// ─────────────────────────────────────────────
//  MVP v1.1 엔드포인트 타입 정의
// ─────────────────────────────────────────────

export interface BalanceResponse {
  balance: number;
  updated_at: string | null;
}

export interface PurchaseIntentRequest {
  pack_code: "starter" | "regular" | "pro";
}

export interface PurchaseIntentResponse {
  order_id: string;
  amount_krw: number;
  tokens_granted: number;
  pg_order_id: string;
  pg_amount: number;
  pg_order_name: string;
}

export interface ConfirmPaymentRequest {
  payment_key: string;
  amount: number;
}

export interface ConfirmPaymentResponse {
  order_id: string;
  status: "paid" | "failed";
  balance_after: number;
}

export interface AuthMeResponse {
  id: string;
  kakao_id: string;
  email: string;
  name: string;
  tier: string;
}

// ─────────────────────────────────────────────
//  편의 함수 (얇은 래퍼)
// ─────────────────────────────────────────────

export const api = {
  me: () => authFetch<AuthMeResponse>("/api/v1/auth/me"),

  getBalance: () => authFetch<BalanceResponse>("/api/v1/tokens/balance"),

  createPurchaseIntent: (packCode: PurchaseIntentRequest["pack_code"]) =>
    authFetch<PurchaseIntentResponse>("/api/v1/tokens/purchase-intent", {
      method: "POST",
      json: { pack_code: packCode },
    }),

  confirmPayment: (orderId: string, data: ConfirmPaymentRequest) =>
    authFetch<ConfirmPaymentResponse>(
      `/api/v1/payments/confirm/${encodeURIComponent(orderId)}`,
      { method: "POST", json: data },
    ),
};
