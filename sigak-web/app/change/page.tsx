// SIGAK MVP v2 BM — /change
//
// 변화 탭. 유저 verdict 시계열 궤적. FeedShell 안에 ChangeView 렌더.
"use client";

import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { SigakLoading } from "@/components/ui/sigak";
import { FeedShell } from "@/components/sigak/feed-shell";
import { ChangeView } from "@/components/sigak/change-view";
import { SiteFooter } from "@/components/sigak/site-footer";

export default function ChangePage() {
  const { status } = useOnboardingGuard();

  if (status !== "ready") {
    return <SigakLoading message="잠시만요" hint="" />;
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
        <ChangeView />
      </FeedShell>
      <SiteFooter />
    </div>
  );
}
