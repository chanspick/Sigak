// SIGAK — Refund page sticky top nav (client boundary).
//
// 2026-04-27 마케터 1815 정합: 검정 52px 인라인 nav → TopBar 컴포넌트
// (paper bg + 20px padding + sigak Noto Serif). /terms 와 동일 패턴.
// /refund 는 Server Component 라 use client 경계 확보용 wrapper.
"use client";

import { TopBar } from "@/components/ui/sigak";

export function RefundTopNav() {
  function handleBack() {
    if (typeof window === "undefined") return;
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  }

  return <TopBar onBack={handleBack} hideTokens />;
}
