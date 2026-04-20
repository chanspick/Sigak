// SIGAK MVP v2 BM — 변화 탭 API 클라이언트.

import { authFetch } from "@/lib/api/fetch";
import type { ChangeResponse } from "@/lib/types/mvp";

export function getChange(): Promise<ChangeResponse> {
  return authFetch<ChangeResponse>("/api/v1/change");
}
