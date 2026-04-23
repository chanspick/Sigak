// Monthly (이달의 시각) 타입 — 백엔드 schemas/monthly_report.py 동기화 (Phase M).
//
// MVP 스켈레톤 — 실 리포트 생성 엔진은 v1.1+. 현재 status="placeholder" 로 안내.

export type MonthlyReportStatus =
  | "scheduled"
  | "generating"
  | "ready"
  | "delivered"
  | "failed"
  | "placeholder";

export interface MonthlyReport {
  report_id: string;
  user_id: string;
  year_month: string;                   // "2026-04"
  status: MonthlyReportStatus;
  scheduled_for: string;                // ISO UTC
  generated_at: string | null;
  result_data: Record<string, unknown> | null;
  created_at: string;
}

export interface MonthlyStatusResponse {
  next_delivery: string;                // ISO UTC
  next_delivery_year_month: string;
  days_remaining: number;
  current_month_report_id: string | null;
  current_month_status: MonthlyReportStatus | null;
  past_reports_count: number;
  placeholder_message: string | null;   // MVP 안내. 실 엔진 붙으면 null.
}
