// 대시보드 타입 정의
export type DashboardView = "queue" | "entry" | "stats" | "payments";

export type BookingStatus = "booked" | "interviewed" | "analyzing" | "reported" | "feedback_done";

export interface QueueUser {
  id: string;
  name: string;
  tier: "basic" | "creator" | "wedding";
  status: BookingStatus;
  booking_date: string;
  booking_time: string;
  has_interview: boolean;
  has_photos: boolean;
  has_report: boolean;
}

export interface DashboardStats {
  total_bookings: number;
  interviewed: number;
  reports_sent: number;
  feedbacks_received: number;
  avg_satisfaction: number;
  avg_usefulness: number;
  nps_target: number;
  nps_met: boolean;
  b2b_opt_in_count: number;
  b2b_opt_in_rate: number;
  repurchase_rate: number;
}

export interface InterviewQuestion {
  key: string;
  label: string;
  placeholder: string;
  rows: number;
}
