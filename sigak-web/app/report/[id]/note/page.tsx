// /report/[id]/note — DEPRECATED 2026-04-27
//
// SPEC-PI-FINALE-001 흐름 정정 (본인 결정):
//   /vision 시각 탭 카드 클릭 → 바로 /report/[id]/full 로 이동
//   /full 하단 (공유하기 위) 에 Card 1 hero + Card 2 4-step 노출
//
// 본 라우트는 호환을 위해 /report/[id]/full 로 영구 redirect.
// 외부 링크 / 북마크 / 메일 푸시 등에서 옛 URL 진입해도 깨끗히 수렴.

import { redirect } from "next/navigation";

export default async function NotePageRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/report/${encodeURIComponent(id)}/full`);
}
