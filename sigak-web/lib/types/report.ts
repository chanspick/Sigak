// 리포트 타입 정의
export type AccessLevel = "free" | "standard_pending" | "standard" | "full_pending" | "full";
export type UnlockLevel = "standard" | "full";
export type SectionId =
  | "cover"
  | "executive_summary"
  | "face_structure"
  | "skin_analysis"
  | "coordinate_map"
  | "action_plan"
  | "celeb_reference"
  | "trend_context";

export interface ReportSection {
  id: SectionId;
  locked: boolean;
  content?: Record<string, unknown>;
  unlock_level?: UnlockLevel;
  teaser?: { headline?: string; categories?: string[] } | null;
}

export interface ReportData {
  id: string;
  user_name: string;
  access_level: AccessLevel;
  pending_level: UnlockLevel | null;
  sections: ReportSection[];
  paywall: Record<UnlockLevel, PaywallTier>;
  payment_account: PaymentAccount;
}

export interface PaywallTier {
  price: number;
  label: string;
  total_note?: string;
  method: "manual" | "auto";
}

export interface PaymentAccount {
  bank: string;
  number: string;
  holder: string;
  kakao_link: string;
}
