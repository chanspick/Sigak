// Monthly (이달의 시각) API 클라이언트 (Phase M).
// 엔드포인트: sigak/routes/monthly.py

import { authFetch } from "@/lib/api/fetch";
import type { MonthlyReport, MonthlyStatusResponse } from "@/lib/types/monthly";

const BASE = "/api/v2/monthly";

/** 이달의 시각 상태 + 다음 배달 예정. 홈 카드 렌더링용.
 *
 * MVP 스켈레톤: placeholder_message 가 non-null 일 때 "준비 중" 카피 표시.
 * 실 엔진 붙으면 placeholder_message=null, current_month_status 에 실 상태.
 */
export async function getMonthlyStatus(): Promise<MonthlyStatusResponse> {
  return authFetch<MonthlyStatusResponse>(`${BASE}/status`);
}

/** 특정 리포트 조회 — 본인 소유만. */
export async function getMonthlyReport(
  reportId: string,
): Promise<MonthlyReport> {
  return authFetch<MonthlyReport>(
    `${BASE}/${encodeURIComponent(reportId)}`,
  );
}
