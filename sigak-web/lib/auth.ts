// 인증 유틸리티 (MVP v1.1 phase B — JWT migration)
//
// 저장 계층 추상화: 현재는 localStorage. Capacitor 네이티브 빌드 추가 시
// ``storage.ts``에 SecureStorage 어댑터를 꽂아 이 파일은 그대로 유지.
//
// 레거시 필드(`sigak_user_id`, `sigak_kakao_id` 등)는 당분간 유지해서 기존
// 컴포넌트(18곳)가 깨지지 않게 한다. `logout()`이 둘 다 지우므로 세션이
// 끝나면 자연스럽게 JWT-only로 전환된다.

const TOKEN_KEY = "sigak_jwt";

const LEGACY_KEYS = [
  "sigak_user_id",
  "sigak_user_name",
  "sigak_user_email",
  "sigak_user_phone",
  "sigak_profile_image",
  "sigak_kakao_id",
] as const;

// ─────────────────────────────────────────────
//  Token ops (JWT)
// ─────────────────────────────────────────────

/** JWT 조회. SSR/빌드 타임에는 null. */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

/** JWT 저장. kakao 콜백 직후 호출. */
export function setToken(jwt: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, jwt);
}

/** JWT + 모든 레거시 필드 제거. `logout()`이 호출함. */
export function clearToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  for (const key of LEGACY_KEYS) {
    localStorage.removeItem(key);
  }
}

// ─────────────────────────────────────────────
//  Kakao 로그인 성공 시 한 번에 저장
// ─────────────────────────────────────────────

interface AuthData {
  jwt: string;
  userId: string;
  kakaoId?: string;
  name?: string;
  email?: string;
  profileImage?: string;
}

/** 카카오 콜백에서 받은 데이터 일괄 저장.
 *
 * JWT를 저장하면서 레거시 필드도 함께 채운다 — 기존 컴포넌트(18곳)가
 * 곧바로 JWT-only로 바뀌지 않아도 동작 보장. 프론트 전환 PR 이후
 * 레거시 필드 저장은 제거.
 */
export function setAuthData(data: AuthData): void {
  if (typeof window === "undefined") return;
  if (data.jwt) localStorage.setItem(TOKEN_KEY, data.jwt);
  localStorage.setItem("sigak_user_id", data.userId);
  if (data.kakaoId) localStorage.setItem("sigak_kakao_id", data.kakaoId);
  if (data.name) localStorage.setItem("sigak_user_name", data.name);
  if (data.email) localStorage.setItem("sigak_user_email", data.email);
  if (data.profileImage) localStorage.setItem("sigak_profile_image", data.profileImage);
}

// ─────────────────────────────────────────────
//  기존 공개 API (호환 유지)
// ─────────────────────────────────────────────

/** 로그인 상태 확인. JWT 우선, 없으면 레거시 user_id 폴백. */
export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  if (localStorage.getItem(TOKEN_KEY)) return true;
  return !!localStorage.getItem("sigak_user_id");
}

/** 로그아웃 — 모든 인증 데이터 정리 + 홈으로 이동 */
export function logout() {
  if (typeof window === "undefined") return;
  clearToken();
  window.location.href = "/";
}

/** 현재 유저 정보 (레거시 필드 기반, 기존 컴포넌트용) */
export function getCurrentUser() {
  if (typeof window === "undefined") return null;
  const userId = localStorage.getItem("sigak_user_id");
  if (!userId) return null;
  return {
    userId,
    name: localStorage.getItem("sigak_user_name") || "",
    email: localStorage.getItem("sigak_user_email") || "",
    profileImage: localStorage.getItem("sigak_profile_image") || "",
    kakaoId: localStorage.getItem("sigak_kakao_id") || "",
  };
}
