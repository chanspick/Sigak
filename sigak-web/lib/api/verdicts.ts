// SIGAK MVP v1.2 — Verdict API 클라이언트.
// Phase C 백엔드 엔드포인트: sigak/routes/verdicts.py

import { authFetch } from "@/lib/api/fetch";
import type {
  ReleaseBlurRequest,
  ReleaseBlurResponse,
  VerdictListResponse,
  VerdictResponse,
} from "@/lib/types/mvp";

/** 업로드 파일 개수 제약 (백엔드와 동일) */
export const MIN_PHOTOS = 2;
export const MAX_PHOTOS = 10;

/** MVP Home은 3장부터 CTA 활성 — 백엔드 MIN(2)과 별개 UX 규칙. */
export const UX_MIN_PHOTOS = 3;

/** 사진 N장 업로드 → verdict 생성. multipart/form-data.
 *
 * 파일 필드명은 "files" (FastAPI ``files: list[UploadFile] = File(...)``).
 * Authorization Bearer는 authFetch가 자동 부착.
 */
export async function createVerdict(files: File[]): Promise<VerdictResponse> {
  if (files.length < MIN_PHOTOS || files.length > MAX_PHOTOS) {
    throw new Error(`사진은 ${MIN_PHOTOS}~${MAX_PHOTOS}장까지 올릴 수 있어요`);
  }
  const form = new FormData();
  for (const f of files) {
    form.append("files", f, f.name);
  }
  return authFetch<VerdictResponse>("/api/v1/verdicts", {
    method: "POST",
    rawBody: form,
  });
}

/** 유저의 verdict 리스트. 피드 그리드용. created_at DESC. */
export function listVerdicts(
  limit = 30,
  offset = 0,
): Promise<VerdictListResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return authFetch<VerdictListResponse>(`/api/v1/verdicts?${params.toString()}`);
}

/** 기존 verdict 재조회. gold_reading은 재조회 시 빈 문자열(ephemeral on create). */
export function getVerdict(verdictId: string): Promise<VerdictResponse> {
  return authFetch<VerdictResponse>(
    `/api/v1/verdicts/${encodeURIComponent(verdictId)}`,
  );
}

/** 본인 verdict 삭제. 204. 404/403 시 authFetch가 throw. */
export function deleteVerdict(verdictId: string): Promise<void> {
  return authFetch<void>(
    `/api/v1/verdicts/${encodeURIComponent(verdictId)}`,
    { method: "DELETE" },
  );
}

/** 50토큰 소비해서 블러 해제.
 *
 * 409 (onboarding 미완), 402 (잔액 부족), 404, 403 가능.
 * idempotency_key 생략 시 백엔드가 `blur:{verdict_id}`로 자동 설정 — 재시도 안전.
 */
export function releaseBlur(
  verdictId: string,
  body: ReleaseBlurRequest = {},
): Promise<ReleaseBlurResponse> {
  return authFetch<ReleaseBlurResponse>(
    `/api/v1/verdicts/${encodeURIComponent(verdictId)}/release-blur`,
    {
      method: "POST",
      json: body,
    },
  );
}

/** 백엔드 응답의 photo.url (``/api/v1/uploads/{user_id}/{filename}``)을
 * API_URL prefix와 합쳐 절대 URL로. null이면 빈 문자열. */
export function resolvePhotoUrl(url: string | null): string {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base}${url}`;
}
