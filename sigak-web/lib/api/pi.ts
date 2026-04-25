// SIGAK MVP v2 BM — PI (Personal Image) API 클라이언트.
//
// v1 (legacy):
//   GET  /api/v1/pi          → getPI()
//   POST /api/v1/pi/unlock   → unlockPI()
//
// v3 (Phase I PI-D, 본인 결정 2026-04-25):
//   GET  /api/v3/pi/status              → getPIv3Status()
//   POST /api/v3/pi/upload (multipart)  → uploadPIv3Baseline(file)
//   POST /api/v3/pi/preview             → previewPIv3()
//   POST /api/v3/pi/unlock              → unlockPIv3()
//   GET  /api/v3/pi/list                → listPIv3Versions()
//   GET  /api/v3/pi/{report_id}         → getPIv3Report(reportId)

import { authFetch } from "@/lib/api/fetch";
import type { PIStatusResponse, PIUnlockResponse } from "@/lib/types/mvp";

// ─────────────────────────────────────────────
//  v1 (legacy) — vision-view 가 아직 사용
// ─────────────────────────────────────────────

export function getPI(): Promise<PIStatusResponse> {
  return authFetch<PIStatusResponse>("/api/v1/pi");
}

export function unlockPI(): Promise<PIUnlockResponse> {
  return authFetch<PIUnlockResponse>("/api/v1/pi/unlock", {
    method: "POST",
  });
}

// ─────────────────────────────────────────────
//  v3 — 9 컴포넌트 3-3-3 + 50 토큰 unlock
// ─────────────────────────────────────────────

export type PIv3SectionId =
  | "cover"
  | "celeb_reference"
  | "face_structure"
  | "type_reference"
  | "gap_analysis"
  | "skin_analysis"
  | "coordinate_map"
  | "hair_recommendation"
  | "action_plan";

export type PIv3SectionVisibility = "full" | "teaser" | "locked";

export interface PIv3Section {
  section_id: PIv3SectionId;
  visibility: PIv3SectionVisibility;
  content: Record<string, unknown>;
}

export interface PIv3Report {
  report_id: string;
  version: number;
  is_current: boolean;
  generated_at: string;
  is_preview: boolean;
  sections: PIv3Section[];
  unlock_cost_tokens: number;
  token_balance: number | null;
  needs_payment_tokens: number | null;
}

export interface PIv3Status {
  has_baseline: boolean;
  baseline_uploaded_at: string | null;
  has_current_report: boolean;
  current_report_id: string | null;
  current_version: number | null;
  unlocked_at: string | null;
  unlock_cost_tokens: number;
  token_balance: number;
  needs_payment_tokens: number;
  pi_pending: boolean;
}

export interface PIv3UploadResponse {
  uploaded: boolean;
  baseline_r2_key: string | null;
  uploaded_at: string;
  makeup_warning: string | null;
}

export interface PIv3VersionEntry {
  report_id: string;
  version: number;
  is_current: boolean;
  generated_at: string;
  is_preview: boolean;
}

export interface PIv3VersionsList {
  versions: PIv3VersionEntry[];
  current_report_id: string | null;
}

export function getPIv3Status(): Promise<PIv3Status> {
  return authFetch<PIv3Status>("/api/v3/pi/status");
}

export async function uploadPIv3Baseline(file: File): Promise<PIv3UploadResponse> {
  const form = new FormData();
  form.append("image", file, file.name);
  return authFetch<PIv3UploadResponse>("/api/v3/pi/upload", {
    method: "POST",
    rawBody: form,
    // Content-Type 은 fetch 가 boundary 포함해서 자동 설정 — 직접 지정 X
    // AuthFetchOptions 가 body 를 Omit 하므로 multipart 는 rawBody (best_shot.ts 정합)
  });
}

export function previewPIv3(): Promise<PIv3Report> {
  return authFetch<PIv3Report>("/api/v3/pi/preview", {
    method: "POST",
  });
}

export function unlockPIv3(): Promise<PIv3Report> {
  return authFetch<PIv3Report>("/api/v3/pi/unlock", {
    method: "POST",
  });
}

export function listPIv3Versions(): Promise<PIv3VersionsList> {
  return authFetch<PIv3VersionsList>("/api/v3/pi/list");
}

export function getPIv3Report(reportId: string): Promise<PIv3Report> {
  return authFetch<PIv3Report>(`/api/v3/pi/${encodeURIComponent(reportId)}`);
}
