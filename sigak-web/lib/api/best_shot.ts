// Best Shot API 클라이언트 (Phase K 백엔드 연동).
// 엔드포인트: sigak/routes/best_shot.py

import { ApiError, authFetch } from "@/lib/api/fetch";
import type {
  BestShotInitRequest,
  BestShotInitResponse,
  BestShotRunResponse,
  BestShotSession,
  BestShotUploadAck,
  StrengthLowWarning,
  TooFewPhotosError,
} from "@/lib/types/best_shot";

const BASE = "/api/v2/best-shot";

/** 업로드 세션 시작.
 *
 * 주의:
 *  - expected_count < 50 → 400 body.code="too_few_photos" (피드 추천 유도 CTA 렌더)
 *  - strength < 0.3 + acknowledge=false → 409 body.code="strength_low"
 *    (경고 모달 후 acknowledge_strength_warning=true 로 재요청)
 */
export async function initBestShotSession(
  body: BestShotInitRequest,
): Promise<BestShotInitResponse> {
  return authFetch<BestShotInitResponse>(`${BASE}/init`, {
    method: "POST",
    json: body,
  });
}

/** 사진 batch 업로드. multipart/form-data.
 *
 * resume: 같은 session_id 로 반복 호출 가능. 서버가 uploaded_count 누적.
 */
export async function uploadBestShotBatch(
  sessionId: string,
  files: File[],
): Promise<BestShotUploadAck> {
  const form = new FormData();
  for (const f of files) {
    form.append("photos", f, f.name);
  }
  return authFetch<BestShotUploadAck>(
    `${BASE}/upload/${encodeURIComponent(sessionId)}`,
    { method: "POST", rawBody: form },
  );
}

/** 선별 실행 — 30 토큰 차감 + heuristic + Sonnet 선별.
 *
 * 실패 시 status="failed" + failure_reason 채워져 옴. 토큰은 자동 환불.
 */
export async function runBestShotSelection(
  sessionId: string,
): Promise<BestShotRunResponse> {
  return authFetch<BestShotRunResponse>(
    `${BASE}/run/${encodeURIComponent(sessionId)}`,
    { method: "POST" },
  );
}

/** 세션 + 결과 조회. */
export async function getBestShotSession(
  sessionId: string,
): Promise<{ session: BestShotSession }> {
  return authFetch<{ session: BestShotSession }>(
    `${BASE}/${encodeURIComponent(sessionId)}`,
  );
}

/** 업로드 중단 + 원본 R2 삭제. 차감 전 단계만 허용. */
export async function abortBestShotSession(
  sessionId: string,
): Promise<{ session_id: string; status: "aborted"; deleted_photos: number }> {
  return authFetch(
    `${BASE}/${encodeURIComponent(sessionId)}/abort`,
    { method: "POST" },
  );
}

// ── Error helpers — 프론트 UX 분기에 유용

export function isTooFewPhotosError(err: unknown): err is ApiError & {
  body: TooFewPhotosError;
} {
  return (
    err instanceof ApiError
    && err.status === 400
    && typeof err.body === "object"
    && err.body !== null
    && (err.body as { code?: string }).code === "too_few_photos"
  );
}

export function isStrengthLowWarning(err: unknown): err is ApiError & {
  body: StrengthLowWarning;
} {
  return (
    err instanceof ApiError
    && err.status === 409
    && typeof err.body === "object"
    && err.body !== null
    && (err.body as { code?: string }).code === "strength_low"
  );
}
