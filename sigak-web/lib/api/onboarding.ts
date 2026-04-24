// SIGAK MVP v1.2 — 온보딩/동의 API 클라이언트.
// authFetch 래퍼로 JWT Bearer 자동 부착.

import { authFetch } from "@/lib/api/fetch";
import type {
  ConsentRequest,
  ConsentResponse,
  EssentialsRequest,
  EssentialsResponse,
  IgStatusResponse,
  OnboardingData,
  OnboardingStateResponse,
  ResetOnboardingResponse,
  SaveStepRequest,
  SaveStepResponse,
  StepNumber,
  AuthMeV2Response,
} from "@/lib/types/mvp";

// ─────────────────────────────────────────────
//  Onboarding
// ─────────────────────────────────────────────

export function getOnboardingState(): Promise<OnboardingStateResponse> {
  return authFetch<OnboardingStateResponse>("/api/v1/onboarding/state");
}

export function saveOnboardingStep(
  step: StepNumber,
  fields: OnboardingData,
): Promise<SaveStepResponse> {
  const body: SaveStepRequest = { step, fields };
  return authFetch<SaveStepResponse>("/api/v1/onboarding/save-step", {
    method: "POST",
    json: body,
  });
}

export function resetOnboarding(): Promise<ResetOnboardingResponse> {
  return authFetch<ResetOnboardingResponse>("/api/v1/onboarding/reset", {
    method: "POST",
  });
}

// ─────────────────────────────────────────────
//  Essentials (Step 0 — SPEC-ONBOARDING-V2 REQ-ONBD-001/002)
// ─────────────────────────────────────────────

/**
 * Step 0 구조화 입력 저장. gender + birth_date 필수, ig_handle 선택.
 * Sia 대화(/sia/new) 진입 전에 반드시 호출되어야 함.
 *
 * ig_handle 있으면 서버가 BackgroundTask 로 Apify + Vision 비동기 시작.
 * 응답의 `ig_fetch_status==="pending"` 이면 프론트는 /onboarding/ig-loading 폴링 필요.
 */
export function saveEssentials(
  body: EssentialsRequest,
): Promise<EssentialsResponse> {
  return authFetch<EssentialsResponse>("/api/v1/onboarding/essentials", {
    method: "POST",
    json: body,
  });
}

/**
 * IG fetch 진행 상태 폴링. 2-3초 간격 권장.
 *
 * 상태 전환: pending → pending_vision → success | private | failed | skipped
 * 최종 상태 도달 시 프론트는 /sia 로 이동.
 */
export function getIgStatus(): Promise<IgStatusResponse> {
  return authFetch<IgStatusResponse>("/api/v1/onboarding/ig-status");
}

// ─────────────────────────────────────────────
//  Consent (v2.0)
// ─────────────────────────────────────────────

export function saveConsent(body: ConsentRequest): Promise<ConsentResponse> {
  return authFetch<ConsentResponse>("/api/v1/auth/consent", {
    method: "POST",
    json: body,
  });
}

// ─────────────────────────────────────────────
//  Me (v2.0 — gate flags)
// ─────────────────────────────────────────────

export function getMe(): Promise<AuthMeV2Response> {
  return authFetch<AuthMeV2Response>("/api/v1/auth/me");
}
