// SIGAK — Capacitor config
//
// 초기 전략: Server mode — 네이티브 앱이 https://sigak.asia 를 WebView로 로드.
// Vercel 배포 변경이 네이티브 앱에 즉시 반영되므로 초기 개발 속도 최대.
//
// 추후 App Store 심사 시 "pure webview 래퍼" 문제로 거절되면 정적 번들 모드로
// 전환: next.config.ts output:'export' + webDir:'out' + server.url 제거.
// 마이그레이션 가이드는 CAPACITOR.md 참조.

import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "asia.sigak.app",
  appName: "SIGAK",

  // 정적 번들 모드 전환 시 사용. Server mode에선 무시됨.
  webDir: "out",

  server: {
    url: "https://sigak.asia",
    cleartext: false,
    // androidScheme: 'https' (기본값) — 로컬 테스트 시에만 'http' 고려.
  },

  android: {
    allowMixedContent: false,
  },

  ios: {
    // 세이프 에리어(노치/다이내믹 아일랜드) 자동 대응
    contentInset: "automatic",
    // Custom URL scheme (Kakao deep link 등 미래 확장용)
    scheme: "SIGAK",
  },
};

export default config;
