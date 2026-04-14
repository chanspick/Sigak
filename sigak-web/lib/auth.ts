// 인증 유틸리티

const STORAGE_KEYS = [
  "sigak_user_id",
  "sigak_user_name",
  "sigak_user_email",
  "sigak_user_phone",
  "sigak_profile_image",
  "sigak_kakao_id",
];

/** 로그인 상태 확인 */
export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("sigak_user_id");
}

/** 로그아웃 — localStorage 정리 + 홈으로 이동 */
export function logout() {
  if (typeof window === "undefined") return;
  for (const key of STORAGE_KEYS) {
    localStorage.removeItem(key);
  }
  window.location.href = "/";
}

/** 현재 유저 정보 */
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
