/**
 * /pi/[id] — DEPRECATED redirect (PI Revival Phase 5, 작업 D).
 *
 * 신 PI v3 풀 리포트 페이지 폐기에 따라 본 라우트는 영구 redirect.
 * dynamic id 보존하여 옛 SIGAK_V3 report 풀 화면으로 매핑.
 *
 * Target: /report/{id}/full (옛 SIGAK_V3 ReportViewer 9 sections).
 * 보존 기간: v1 launch 후 6개월 (v1.5 에서 완전 삭제 검토).
 *
 * Next.js 16 App Router: params 는 Promise — async + await params 패턴 적용.
 *
 * @see handoff/PI_REVIVE_V5_OLD_SYSTEM.md 작업 D
 */

import { redirect } from "next/navigation";

export default async function PiReportDeprecated({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/report/${encodeURIComponent(id)}/full`);
}
