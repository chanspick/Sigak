// SIGAK MVP v1.2 — 온보딩/동의 API 클라이언트.
// authFetch 래퍼로 JWT Bearer 자동 부착.

import { authFetch } from "@/lib/api/fetch";
import type {
  ConsentRequest,
  ConsentResponse,
  EssentialsRequest,
  EssentialsResponse,
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
 */
export function saveEssentials(
  body: EssentialsRequest,
): Promise<EssentialsResponse> {
  return authFetch<EssentialsResponse>("/api/v1/onboarding/essentials", {
    method: "POST",
    json: body,
  });
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
