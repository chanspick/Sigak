import type { Metadata } from "next";
import { StartOverlay } from "@/components/start/start-overlay";

// SEO 메타데이터
export const metadata: Metadata = {
  title: "시작하기 | 시각",
};

/** /start 라우트 - 티어 선택 + 기본 정보 입력 */
export default function StartPage() {
  return <StartOverlay />;
}
