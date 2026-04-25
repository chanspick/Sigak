/**
 * /pi/upload — PI v3 임시 잠금 (2026-04-26).
 *
 * 본인 결정: product 본질 검증 미완 → maintenance UI 만 노출. 5월 중 재개.
 * 재개 시 본 page.tsx 를 git history (commit cf1a899 이전) 에서 복원.
 */

import { PiMaintenance } from "@/components/pi-v3/PiMaintenance";

export default function PIUploadPage() {
  return <PiMaintenance />;
}
