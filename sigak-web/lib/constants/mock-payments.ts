import type { PaymentRequest } from "@/lib/types/payment";

// 결제 목 데이터
export const MOCK_PAYMENTS: PaymentRequest[] = [
  {
    id: "pay_001",
    user_id: "u1",
    report_id: "report_abc123",
    user_name: "김서연",
    requested_level: "standard",
    amount: 20000,
    status: "pending",
    requested_at: "2026-04-15T14:30:00Z",
    confirmed_at: null,
    confirmed_by: null,
  },
  {
    id: "pay_002",
    user_id: "u2",
    report_id: "report_def456",
    user_name: "이준혁",
    requested_level: "full",
    amount: 30000,
    status: "pending",
    requested_at: "2026-04-15T15:00:00Z",
    confirmed_at: null,
    confirmed_by: null,
  },
  {
    id: "pay_003",
    user_id: "u3",
    report_id: "report_ghi789",
    user_name: "박지민",
    requested_level: "standard",
    amount: 20000,
    status: "confirmed",
    requested_at: "2026-04-15T10:00:00Z",
    confirmed_at: "2026-04-15T10:15:00Z",
    confirmed_by: "관리자",
  },
];
