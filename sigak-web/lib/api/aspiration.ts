// Aspiration (추구미 분석) API 클라이언트 (Phase J).
// 엔드포인트: sigak/routes/aspiration.py

import { authFetch } from "@/lib/api/fetch";
import type {
  AspirationAnalysis,
  AspirationIgRequest,
  AspirationPinterestRequest,
  AspirationStartResponse,
} from "@/lib/types/aspiration";

const BASE = "/api/v2/aspiration";

/** 제3자 IG 핸들 추구미 분석 — 20 토큰.
 *
 * 실패 시 (failed_private / failed_scrape / failed_blocked 등) 토큰 자동 환불.
 * status="completed" 인 경우만 analysis 필드 채워짐.
 */
export async function createIgAspiration(
  body: AspirationIgRequest,
): Promise<AspirationStartResponse> {
  return authFetch<AspirationStartResponse>(`${BASE}/ig`, {
    method: "POST",
    json: body,
  });
}

/** Pinterest 보드 추구미 분석 — 20 토큰.
 *
 * MVP: pinterest_enabled=false 기본 → failed_skipped 로 반환. Phase P 이후 활성.
 */
export async function createPinterestAspiration(
  body: AspirationPinterestRequest,
): Promise<AspirationStartResponse> {
  return authFetch<AspirationStartResponse>(`${BASE}/pinterest`, {
    method: "POST",
    json: body,
  });
}

/** 분석 결과 재조회 (본인 소유만). */
export async function getAspirationAnalysis(
  analysisId: string,
): Promise<AspirationAnalysis> {
  return authFetch<AspirationAnalysis>(
    `${BASE}/${encodeURIComponent(analysisId)}`,
  );
}

// ─────────────────────────────────────────────
//  DELETE — 본인 분석 단건 삭제 (PI-REVIVE 2026-04-26)
// ─────────────────────────────────────────────

export interface AspirationDeleteResponse {
  deleted: boolean;
  history_entry_removed: boolean;
}

export async function deleteAspirationAnalysis(
  analysisId: string,
): Promise<AspirationDeleteResponse> {
  return authFetch<AspirationDeleteResponse>(
    `${BASE}/${encodeURIComponent(analysisId)}`,
    { method: "DELETE" },
  );
}
