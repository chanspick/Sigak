// /casting/invitation — 캐스팅 제안 상세 페이지 (PI Revival Phase B-6 결정으로 제거).
//
// 2026-04-26 본인 결정: 캐스팅 풀 영역 전반 제거.
// 페이지 자체 삭제하면 매칭 알림 메일 링크가 404.
// 따라서 redirect "/" 로 단순화 (라우트 보존, 콘텐츠 X).

import { redirect } from "next/navigation";

export default function CastingInvitationPage() {
  redirect("/");
}
