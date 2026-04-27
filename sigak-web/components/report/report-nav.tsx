"use client";

// 리포트 페이지 전용 네비게이션 바.
// Phase B-6 (PI-REVIVE 2026-04-26): 옛 PI v3 시절 nav → TopBar 정합.
// Phase B-6.1 (2026-04-26): 우측 OVERVIEW / 내 리포트 / NotificationBell 모두 제거.
// 2026-04-27 마케터 1815 정합: 검정 52px → TopBar 컴포넌트 (paper bg + 20px).
//   rightLink prop 은 backward compat 위해 유지 (caller 변경 안 해도 무시됨).

import { TopBar } from "@/components/ui/sigak";

interface ReportNavProps {
  /** Phase B-6.1: 사용 안 함 (backward compat). caller 가 전달해도 무시. */
  rightLink?: { href: string; label: string };
}

export function ReportNav(_props: ReportNavProps = {}) {
  return <TopBar backTarget="/" hideTokens />;
}
