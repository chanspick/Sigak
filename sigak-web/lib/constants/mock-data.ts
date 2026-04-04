import type { QueueUser, DashboardStats, BookingStatus } from "@/lib/types/dashboard";

// 대시보드 목 데이터 (sigak_dashboard.jsx에서 추출)
export const MOCK_QUEUE: QueueUser[] = [
  {
    id: "u1",
    name: "김서연",
    tier: "basic",
    status: "booked",
    booking_date: "2026-04-15",
    booking_time: "14:00",
    has_interview: false,
    has_photos: false,
    has_report: false,
  },
  {
    id: "u2",
    name: "이준혁",
    tier: "creator",
    status: "interviewed",
    booking_date: "2026-04-15",
    booking_time: "15:00",
    has_interview: true,
    has_photos: true,
    has_report: false,
  },
  {
    id: "u3",
    name: "박지민 · 최우진",
    tier: "wedding",
    status: "reported",
    booking_date: "2026-04-16",
    booking_time: "10:00",
    has_interview: true,
    has_photos: true,
    has_report: true,
  },
  {
    id: "u4",
    name: "정하은",
    tier: "basic",
    status: "booked",
    booking_date: "2026-04-16",
    booking_time: "11:00",
    has_interview: false,
    has_photos: false,
    has_report: false,
  },
  {
    id: "u5",
    name: "오민수",
    tier: "creator",
    status: "interviewed",
    booking_date: "2026-04-17",
    booking_time: "14:00",
    has_interview: true,
    has_photos: false,
    has_report: false,
  },
];

// 대시보드 통계 목 데이터
export const MOCK_STATS: DashboardStats = {
  total_bookings: 12,
  interviewed: 8,
  reports_sent: 5,
  feedbacks_received: 3,
  avg_satisfaction: 4.3,
  avg_usefulness: 4.1,
  nps_target: 4.2,
  nps_met: false,
  b2b_opt_in_count: 2,
  b2b_opt_in_rate: 66.7,
  repurchase_rate: 100,
};

// 티어 표시명 매핑
export const TIER_MAP: Record<string, string> = {
  basic: "시선",
  creator: "Creator",
  wedding: "Wedding",
};

// 상태 표시명 매핑
export const STATUS_MAP: Record<BookingStatus, string> = {
  booked: "예약됨",
  interviewed: "인터뷰 완료",
  analyzing: "분석 중",
  reported: "리포트 발송",
  feedback_done: "피드백 완료",
};

// 상태 순서
export const STATUS_ORDER: BookingStatus[] = [
  "booked",
  "interviewed",
  "analyzing",
  "reported",
  "feedback_done",
];
