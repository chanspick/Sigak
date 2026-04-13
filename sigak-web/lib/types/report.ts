// 리포트 타입 정의
export type AccessLevel = "free" | "standard_pending" | "standard" | "full_pending" | "full";
export type UnlockLevel = "standard" | "full";
export type SectionId =
  | "cover"
  | "executive_summary"
  | "face_structure"
  | "skin_analysis"
  | "gap_analysis"
  | "coordinate_map"
  | "hair_recommendation"
  | "action_plan"
  | "type_reference"
  | "celeb_reference"
  | "trend_context";

// ─── 헤어 추천 섹션 타입 ───

export interface HairStyle {
  id: string;
  name_kr: string;
  name_en: string;
  image: string;
}

export interface BackHairStyle {
  id: string;
  name_kr: string;
  name_en: string;
  image_front: string;
  image_rear: string;
}

export interface HairCombo {
  rank: number;
  score: number | null;
  front: HairStyle | null;
  back: BackHairStyle | null;
  why: string;
  axis_shift: Record<string, number>;
  salon_instruction: string;
  trend: string | null;
}

export interface HairAvoid {
  style: HairStyle | BackHairStyle | null;
  name_kr: string;
  reason: string;
}

export interface HairRecommendationContent {
  cheat_sheet: string;
  top_combos: HairCombo[];
  avoid: HairAvoid[];
  catalog: {
    front: HairStyle[];
    back: BackHairStyle[];
  };
}

export interface ReportSection {
  id: SectionId;
  locked: boolean;
  content?: Record<string, unknown>;
  unlock_level?: UnlockLevel;
  teaser?: { headline?: string; categories?: string[] } | null;
}

export interface ReportData {
  id: string;
  user_id?: string;
  user_name: string;
  access_level: AccessLevel;
  pending_level: UnlockLevel | null;
  sections: ReportSection[];
  paywall?: Partial<Record<UnlockLevel, PaywallTier>>;
  payment_account?: PaymentAccount;
}

export interface PaywallTier {
  price: number;
  original_price?: number;
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
