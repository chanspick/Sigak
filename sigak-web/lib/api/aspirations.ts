// 추구미 분석 API 클라이언트.
// Source of truth: sigak/routes/aspiration.py
//   - GET    /api/v2/aspiration              (list)
//   - GET    /api/v2/aspiration/{id}         (single)
//   - POST   /api/v2/aspiration/ig
//   - POST   /api/v2/aspiration/pinterest

import { authFetch } from "@/lib/api/fetch";
import type { AspirationListResponse } from "@/lib/types/aspiration";

/** 유저의 추구미 분석 리스트. 피드 그리드용. created_at DESC. */
export function listAspirations(
  limit = 30,
  offset = 0,
): Promise<AspirationListResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return authFetch<AspirationListResponse>(
    `/api/v2/aspiration?${params.toString()}`,
  );
}

/** R2 등 외부 절대 URL은 그대로 반환. 빈 값/null 은 빈 문자열. */
export function resolveAspirationCoverUrl(url: string | null): string {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base}${url}`;
}
