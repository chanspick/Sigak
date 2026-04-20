// SIGAK MVP v2 BM — /vision
//
// PI(Personal Image) 해제 탭. FeedShell 공통 레이아웃 안에 VisionView 렌더.
"use client";

import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { FeedShell } from "@/components/sigak/feed-shell";
import { VisionView } from "@/components/sigak/vision-view";
import { SiteFooter } from "@/components/sigak/site-footer";

export default function VisionPage() {
  const { status } = useOnboardingGuard();

  if (status !== "ready") {
    return (
      <div style={{ minHeight: "100vh", background: "var(--color-paper)" }} aria-busy />
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <FeedShell>
        <VisionView />
      </FeedShell>
      <SiteFooter />
    </div>
  );
}
