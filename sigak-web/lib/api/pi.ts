// SIGAK MVP v2 BM — PI (Personal Image) API 클라이언트.

import { authFetch } from "@/lib/api/fetch";
import type { PIStatusResponse, PIUnlockResponse } from "@/lib/types/mvp";

export function getPI(): Promise<PIStatusResponse> {
  return authFetch<PIStatusResponse>("/api/v1/pi");
}

export function unlockPI(): Promise<PIUnlockResponse> {
  return authFetch<PIUnlockResponse>("/api/v1/pi/unlock", {
    method: "POST",
  });
}
