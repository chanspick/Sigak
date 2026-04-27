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

/**
 * Sia Finale — SPEC-PI-FINALE-001
 *
 * PI 레포트 끝에 들어갈 Sia 페르소나 B 톤 종합 마무리 (6 필드).
 * - Card 1 = headline + lead_paragraph
 * - Card 2 = 4 step (관찰 / 해석 / 진단 / 다음 한 걸음)
 */
export interface SiaFinale {
  headline: string;
  lead_paragraph: string;
  step_1_observation: string;
  step_2_interpretation: string;
  step_3_diagnosis: string;
  step_4_closing: string;
  generated_at?: string;
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
  /** SPEC-PI-FINALE-001: 종합 마무리. 백필 전 레거시 레포트는 누락 가능. */
  sia_finale?: SiaFinale;
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
