// /auth/login — 로그인 진입점.
//
// 실 로그인 UI 는 홈 `/` 의 LoggedOutLanding 이 담당 (카카오 OAuth + 약관).
// guard 가 토큰 없을 때 이 경로로 redirect 하므로 404 를 막기 위해 존재.
// JWT 있는 유저는 홈 LoggedInFeed 로 그대로, 없는 유저는 LoggedOutLanding 으로.

import { redirect } from "next/navigation";

export default function AuthLoginPage() {
  redirect("/");
}
