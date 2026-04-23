/**
 * /sia — Sia 대화 (단일 라우트, session_id 서버 상태).
 *
 * 가드: useOnboardingGuard 가 consent + essentials 미완료 시 각 단계로 redirect.
 * onboarding 완료 유저가 진입하면 useSiaSession 이 자동으로 새 /chat/start 호출.
 */

"use client";

import { SiaChatView } from "@/components/sia/SiaChatView";
import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";

export default function SiaPage() {
  const { status } = useOnboardingGuard();
  if (status !== "ready") {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-hidden
      />
    );
  }
  return <SiaChatView />;
}
