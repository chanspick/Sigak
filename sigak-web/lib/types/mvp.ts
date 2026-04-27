// SIGAK MVP v1.2 — 백엔드 response 타입 정의
//
// Source of truth: sigak/routes/{onboarding,verdicts,tokens,auth,payments}.py
// Pydantic 모델과 1:1 대응. 브리프 문서와 불일치하는 곳은 실제 백엔드 기준.
//
// ⚠️ 브리프 vs 실제 차이:
//   - 브리프 6.8/7.3의 `/reports/{id}/release-blur`는 v1.2에 없음.
//     실제는 `/verdicts/{id}/release-blur` (verdicts 테이블 blur_released 컬럼).
//   - 브리프 Q7의 chugumi 저장은 users.onboarding_data(JSONB) 한 곳.
//
// 레거시 tier(standard/full/basic 등)는 lib/types/tier.ts 유지 — MVP v1.2와 무관.

// ─────────────────────────────────────────────
//  Onboarding (/api/v1/onboarding/*)
// ─────────────────────────────────────────────

/** 4스텝 질문지 필드. 모두 optional — step별 필수 필드만 검증됨. */
export interface OnboardingData {
  // Step 1: 체형
  height?: HeightOption;
  weight?: WeightOption;
  shoulder_width?: ShoulderOption;
  neck_length?: NeckOption;
  // Step 2: 얼굴
  face_concerns?: string; // comma-joined, e.g. "wide_face,short_forehead"
  // Step 3: 추구미
  style_image_keywords?: string; // comma-joined, max 3
  desired_image?: string; // free text, 10–300
  reference_celebs?: string; // optional, max 200
  makeup_level?: MakeupOption;
  // Step 4: 자기인식
  self_perception?: string; // free text, 5–300
  current_concerns?: string; // optional, max 500
  // 기타
  [key: string]: unknown;
}

export type HeightOption =
  | "under_155"
  | "155_160"
  | "160_165"
  | "165_170"
  | "170_175"
  | "over_175";

export type WeightOption =
  | "under_45"
  | "45_50"
  | "50_55"
  | "55_60"
  | "60_65"
  | "65_70"
  | "70_80"
  | "over_80";

export type ShoulderOption = "narrow" | "medium" | "wide";
export type NeckOption = "short" | "medium" | "long";
export type MakeupOption = "minimal" | "basic" | "intermediate" | "advanced";

export type StepNumber = 1 | 2 | 3 | 4;

export interface SaveStepRequest {
  step: StepNumber;
  fields: OnboardingData;
}

export interface SaveStepResponse {
  onboarding_data: OnboardingData;
  completed: boolean;
}

export interface OnboardingStateResponse {
  onboarding_completed: boolean;
  onboarding_data: OnboardingData | null;
  next_step: StepNumber | null;
}

export interface ResetOnboardingResponse {
  onboarding_completed: false;
}

// ─────────────────────────────────────────────
//  Consent v2.0 (POST /api/v1/auth/consent)
// ─────────────────────────────────────────────

export interface ConsentRequest {
  /** 이용약관 [필수] */
  terms: boolean;
  /** 개인정보 수집·이용 [필수] */
  privacy: boolean;
  /** 민감정보(얼굴·생체 특징) 수집·이용 [필수] */
  sensitive: boolean;
  /** 국외 이전 (Railway/Vercel/Anthropic) [필수] */
  overseas_transfer: boolean;
  /** 만 14세 이상 [필수] */
  age_confirmed: boolean;
  /** 마케팅 수신 [선택] */
  marketing: boolean;
}

export interface ConsentData extends ConsentRequest {
  timestamp: string;   // UTC ISO
  ip_address: string;
  terms_version: string; // e.g. "2.0"
}

export interface ConsentResponse {
  consent_completed: boolean;
  consent_data: ConsentData;
}

// /auth/me response (v2.0: gate flags 포함)
//
// 3단계 게이트:
//   consent_completed    : v2.0 약관 5+1 동의 (/onboarding/welcome)
//   essentials_completed : Step 0 구조화 입력 완료 (/onboarding/essentials)
//                          판정 = users.birth_date IS NOT NULL
//   onboarding_completed : Sia 대화 종료 (v2) / 4스텝 완료 (v1 legacy)
export interface AuthMeV2Response {
  id: string;
  kakao_id: string;
  email: string;
  name: string;
  tier: string;
  consent_completed: boolean;
  essentials_completed: boolean;
  onboarding_completed: boolean;
  /** 2026-04-27: male v1.1 차단 UI 분기용. 권위 = user_profiles.gender. NULL/비표준 시 null. */
  gender?: "female" | "male" | null;
  /** /profile/edit 가 현재 핸들 표시용으로 사용. null = 등록된 IG 핸들 없음. */
  ig_handle?: string | null;
}

// ─────────────────────────────────────────────
//  Essentials (Step 0 — SPEC-ONBOARDING-V2 REQ-ONBD-001/002)
// ─────────────────────────────────────────────

export type Gender = "female" | "male";

export interface EssentialsRequest {
  gender: Gender;
  /** ISO 8601 (YYYY-MM-DD). 만 14세 이상 필수. */
  birth_date: string;
  /** @prefix 자동 제거. 빈 문자열은 서버가 null 처리. */
  ig_handle?: string | null;
}

export interface EssentialsResponse {
  essentials_completed: boolean;
  gender: Gender;
  birth_date: string;
  ig_handle: string | null;
  /**
   * IG 비동기 fetch 트리거 시그널.
   *   pending  — ig_handle 있음, BackgroundTask 예약. 프론트는 /onboarding/ig-loading 으로 이동해 폴링.
   *   skipped  — ig_handle 없음. 프론트는 /sia 직행.
   */
  ig_fetch_status: "pending" | "skipped";
}

/**
 * GET /api/v1/onboarding/ig-status — 대기 화면 폴링용.
 *
 * 상태 흐름:
 *   pending        → BackgroundTask 시작 전/중. preview_urls 아직 없음.
 *   pending_vision → Apify 성공 + preview DB flush 완료. preview_urls 렌더 가능. Vision 진행.
 *   success        → 최종 완료. analyzed=true. Sia 진입 OK.
 *   private        → 비공개 계정. Sia 진입 OK (제한된 컨텍스트).
 *   failed         → Apify 오류. Sia 진입 OK (Vision 폴백).
 *   skipped        → 핸들 비어있거나 flag off. Sia 진입 OK.
 */
export type IgFetchStatus =
  | "pending"
  | "pending_vision"
  | "success"
  | "private"
  | "failed"
  | "skipped";

export interface IgStatusResponse {
  status: IgFetchStatus;
  /** 프로필 CDN URL. pending_vision 부터 채워짐. 최대 6장. */
  preview_urls: string[];
  username: string | null;
  /** Vision 분석 완료 여부. success + analyzed=true = 풀 컨텍스트. */
  analyzed: boolean;
}

/** Sia 진입 허용 상태 (최종 상태). pending / pending_vision 이 아님. */
export const IG_TERMINAL_STATUSES: readonly IgFetchStatus[] = [
  "success",
  "private",
  "failed",
  "skipped",
];

export function isIgTerminal(status: IgFetchStatus): boolean {
  return (IG_TERMINAL_STATUSES as readonly string[]).includes(status);
}

// ─────────────────────────────────────────────
//  Verdicts (/api/v1/verdicts/*)
// ─────────────────────────────────────────────

/** 단일 후보 사진. url은 blur_released=false이고 tier≠gold일 때 null. */
export interface TierPhoto {
  photo_id: string;
  score: number;
  url: string | null;
}

export interface VerdictTiers {
  gold: TierPhoto[];   // always length 1
  silver: TierPhoto[]; // up to 3
  bronze: TierPhoto[]; // up to 5
}

/** LLM #1/#2 + axis delta 기반 PRO 블록 데이터. blur_released=true일 때만 존재. */
export interface VerdictProData {
  silver_readings: PhotoReading[];
  bronze_readings: PhotoReading[];
  full_analysis: FullAnalysis;
}

export interface PhotoReading {
  photo_id: string;
  axis_delta: AxisDelta;
  reason: string;
}

export interface AxisDelta {
  shape: number;
  volume: number;
  age: number;
}

export interface FullAnalysis {
  interpretation: string;
  reference_base: string;
  chugumi_target: AxisDelta;
  action_spec: unknown | null;       // TODO: 백엔드 LLM #3 full 붙으면 구체화
  trajectory_signal: unknown | null; // TODO: 이전 verdict 누적 시 구체화
}

export interface VerdictResponse {
  verdict_id: string;
  candidate_count: number;
  tiers: VerdictTiers;
  gold_reading: string; // 20260425 이후 영속. 그 이전 row는 ""
  blur_released: boolean;        // deprecated (legacy 50토큰 해제)
  diagnosis_unlocked?: boolean;  // v2 BM — 10토큰 진단 해제
  pro_data: VerdictProData | null;
  /** 공유 링크로 타유저가 열었을 땐 false. 프론트는 kebab/진단 CTA 노출에 사용. */
  is_owner: boolean;
}

// v2 BM — POST /verdicts/{id}/unlock-diagnosis
export interface UnlockDiagnosisResponse {
  verdict_id: string;
  diagnosis_unlocked: true;
  token_balance: number;
}

export interface ReleaseBlurRequest {
  idempotency_key?: string;
}

export interface ReleaseBlurResponse {
  verdict_id: string;
  blur_released: true;
  pro_data: VerdictProData;
  balance_after: number;
}

// ─────────────────────────────────────────────
//  Sigak Report (시각 리포트 — 온보딩 기반 유저 분석 요약)
// ─────────────────────────────────────────────

/** 추구미 3축 좌표. 각 -1.0 .. 1.0 */
export interface ChugumiCoords {
  shape: number;
  volume: number;
  age: number;
}

// ─────────────────────────────────────────────
//  PI 리포트 (v2 BM — 유저 1회 50토큰 영속 해제)
// ─────────────────────────────────────────────

/** 최초 해제 시 placeholder. 실제 생성 로직 붙으면 필드 채워짐. */
export interface PIReportData {
  status?: "generating" | "ready" | "migrated_from_sigak_report" | string;
  face_analysis?: unknown | null;
  skin_tone?: unknown | null;
  gap_analysis?: unknown | null;
  hair_recommendations?: unknown | null;
  makeup_guide?: unknown | null;
  [key: string]: unknown;
}

export interface PIStatusResponse {
  unlocked: boolean;
  cost: number;
  unlocked_at?: string | null;
  report_data?: PIReportData | null;
}

export interface PIUnlockResponse {
  unlocked: true;
  unlocked_at: string;
  report_data: PIReportData;
  token_balance: number;
}

// ─────────────────────────────────────────────
//  변화 탭 (v2 BM — 무료)
// ─────────────────────────────────────────────

export interface ChangeEntry {
  verdict_id: string;
  created_at: string;
  winner_coords: ChugumiCoords | null;
  target_coords: ChugumiCoords | null;
  diagnosis_unlocked: boolean;
}

export interface ChangeResponse {
  entries: ChangeEntry[];
  count: number;
}

export interface SigakReportResponse {
  released: boolean;
  cost: number;
  onboarding_data: OnboardingData | null;
  /** LLM #2 자연어 해석 — "시각이 본 당신" */
  interpretation?: string | null;
  /** 해석 참조 앵커 (e.g., "따뜻한 첫사랑") */
  reference_base?: string | null;
  /** 추구미 좌표 — 방향성 */
  chugumi_coords?: ChugumiCoords | null;
}

export interface ReleaseSigakReportResponse {
  released: true;
  onboarding_data: OnboardingData;
  interpretation?: string | null;
  reference_base?: string | null;
  chugumi_coords?: ChugumiCoords | null;
  balance_after: number;
}

// ─────────────────────────────────────────────
//  Verdict List (피드 그리드용)
// ─────────────────────────────────────────────

export interface VerdictListItem {
  verdict_id: string;
  gold_photo_url: string | null;
  blur_released: boolean;
  created_at: string; // ISO
}

export interface VerdictListResponse {
  verdicts: VerdictListItem[];
  total: number;
  has_more: boolean;
}

// ─────────────────────────────────────────────
//  Tokens (/api/v1/tokens/*)
// ─────────────────────────────────────────────

export interface TokenBalanceResponse {
  balance: number;
  updated_at: string | null;
}

export type PackCode = "starter" | "regular" | "pro";

export interface PurchaseIntentRequest {
  pack_code: PackCode;
}

export interface PurchaseIntentResponse {
  order_id: string;
  amount_krw: number;
  tokens_granted: number;
  pg_order_id: string;
  pg_amount: number;
  pg_order_name: string;
}

/** 팩 메타 (프론트 카드 렌더용, 하드코딩) */
export interface TokenPack {
  code: PackCode;
  name_kr: string;
  amount_krw: number;
  tokens: number;
  perTokenKrw: number;
  badge?: string;
}

export const TOKEN_PACKS: readonly TokenPack[] = [
  { code: "starter", name_kr: "Starter", amount_krw: 10000, tokens: 100, perTokenKrw: 100, badge: "첫 충전" },
  { code: "regular", name_kr: "Regular", amount_krw: 25000, tokens: 280, perTokenKrw: 89, badge: "12% 할인" },
  { code: "pro",     name_kr: "Pro",     amount_krw: 50000, tokens: 600, perTokenKrw: 83, badge: "17% 할인" },
] as const;

// 소비 비용 (브리프 섹션 1)
export const COST_UNLOCK_REASONING = 5;
export const COST_BLUR_RELEASE = 50;
export const COST_MONTHLY_REPORT = 30;

// ─────────────────────────────────────────────
//  Payments (/api/v1/payments/*)
// ─────────────────────────────────────────────

export interface ConfirmPaymentRequest {
  payment_key: string;
  amount: number;
}

export interface ConfirmPaymentResponse {
  order_id: string;
  status: "paid" | "failed";
  balance_after: number;
}

// ─────────────────────────────────────────────
//  Auth (/api/v1/auth/*)
// ─────────────────────────────────────────────

export interface AuthMeResponse {
  id: string;
  kakao_id: string;
  email: string;
  name: string;
  tier: string; // 레거시 필드, MVP v1.2에서는 "standard" 고정
}

// ─────────────────────────────────────────────
//  Purchase intent 쿼리 파라미터
//  /tokens/purchase?intent=blur_release&verdict_id=X
// ─────────────────────────────────────────────

export type PurchaseIntent = "blur_release" | "unlock_reasoning";

export interface PurchaseIntentParams {
  intent?: PurchaseIntent;
  verdict_id?: string;
  report_id?: string;
}
