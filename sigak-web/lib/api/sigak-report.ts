// SIGAK MVP v1.2 — 시각 리포트 API 클라이언트.

import { authFetch } from "@/lib/api/fetch";
import type {
  ReleaseSigakReportResponse,
  SigakReportResponse,
} from "@/lib/types/mvp";

export function getSigakReport(): Promise<SigakReportResponse> {
  return authFetch<SigakReportResponse>("/api/v1/sigak-report");
}

export function releaseSigakReport(): Promise<ReleaseSigakReportResponse> {
  return authFetch<ReleaseSigakReportResponse>(
    "/api/v1/sigak-report/release",
    { method: "POST" },
  );
}
