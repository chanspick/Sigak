// SIGAK — Kakao OAuth 공유 유틸.
//
// login 페이지와 callback 페이지가 redirect_uri를 **동일하게** 계산해야
// Kakao OAuth 규약상 code 교환이 성공함. 불일치 시 Kakao가 400 "Redirect URI
// mismatch"로 거절.
//
// 우선순위:
//   1. NEXT_PUBLIC_KAKAO_REDIRECT_URI env (canonical 도메인 고정 시)
//   2. window.location.origin + /auth/kakao/callback (동적, 기본)
//   3. SSR 폴백 (www.sigak.asia)

export function getKakaoRedirectUri(): string {
  const fromEnv = process.env.NEXT_PUBLIC_KAKAO_REDIRECT_URI;
  if (fromEnv) return fromEnv;
  if (typeof window !== "undefined") {
    return `${window.location.origin}/auth/kakao/callback`;
  }
  return "https://www.sigak.asia/auth/kakao/callback";
}
