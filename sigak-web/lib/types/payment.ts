// 결제 타입 정의
export type PaymentStatus = "pending" | "confirmed" | "unconfirmed" | "cancelled";

export interface PaymentRequest {
  id: string;
  user_id: string;
  report_id: string;
  user_name: string;
  requested_level: "standard" | "full";
  amount: number;
  status: PaymentStatus;
  requested_at: string;
  confirmed_at: string | null;
  confirmed_by: string | null;
}
