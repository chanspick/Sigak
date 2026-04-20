import type { Metadata } from "next";
import "./globals.css";
import { PostHogProvider } from "./posthog-provider";

// MVP v1.2: SiteHeader 전역 렌더 제거.
// 새 스크린(home/verdict/onboarding)은 자체 TopBar variant를 가짐.
// 레거시 스크린이 SiteHeader 필요하면 개별 import로 해결.

// 폰트는 CDN 방식. next/font/local 쓰지 않음 (public/fonts/ 파일 추가 불필요).
// - Pretendard Variable: jsdelivr CDN
// - Inter + Noto Serif KR: Google Fonts

export const metadata: Metadata = {
  title: "SIGAK — 시각",
  description: "이 중에서는, 이 한 장.",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        {/* Pretendard Variable — jsdelivr */}
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css"
        />
        {/* Inter + Noto Serif KR */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Noto+Serif+KR:wght@400;500&display=swap"
        />
      </head>
      <body>
        <PostHogProvider>{children}</PostHogProvider>
      </body>
    </html>
  );
}
