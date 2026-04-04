import type { Metadata } from "next";
import { Noto_Serif_KR } from "next/font/google";
// import localFont from "next/font/local";
import "./globals.css";

// 폰트 설정
const notoSerifKr = Noto_Serif_KR({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-noto-serif-kr",
  display: "swap",
});

// Pretendard 로컬 폰트 설정
// PretendardVariable.woff2 파일이 public/fonts/에 추가되면 아래 주석을 해제합니다.
// const pretendard = localFont({
//   src: "../public/fonts/PretendardVariable.woff2",
//   variable: "--font-pretendard",
//   display: "swap",
//   fallback: ["-apple-system", "BlinkMacSystemFont", "system-ui", "sans-serif"],
// });

// SEO 메타데이터
export const metadata: Metadata = {
  title: "SIGAK - 시각",
  description: "이목구비 비율 · 얼굴형 정밀 분석, 피부톤 × 컬러 복합 매칭",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className={notoSerifKr.variable}>
      <body>{children}</body>
    </html>
  );
}
