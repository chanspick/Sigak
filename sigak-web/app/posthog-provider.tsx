"use client";

// PostHog 클라이언트 초기화 + SPA 페이지뷰 트래킹
// https://posthog.com/docs/libraries/next-js

import posthog from "posthog-js";
import { PostHogProvider as PHProvider } from "posthog-js/react";
import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, Suspense } from "react";

// 브라우저에서만 1회 초기화
if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://us.i.posthog.com",
    // SPA 페이지뷰: history API 기반 자동 캡처
    capture_pageview: false, // PostHogPageview에서 수동 트래킹
    capture_pageleave: true,
    // 세션 리플레이
    session_recording: {
      maskAllInputs: true,
      maskTextSelector: "[data-ph-mask]",
    },
    // 성능
    loaded: (ph) => {
      if (process.env.NODE_ENV === "development") {
        ph.debug();
      }
    },
  });
}

// SPA 라우트 변경 시 페이지뷰 캡처
function PostHogPageview() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (pathname && posthog) {
      let url = window.origin + pathname;
      if (searchParams.toString()) {
        url += "?" + searchParams.toString();
      }
      posthog.capture("$pageview", { $current_url: url });
    }
  }, [pathname, searchParams]);

  return null;
}

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  if (!process.env.NEXT_PUBLIC_POSTHOG_KEY) {
    // 키 없으면 PostHog 비활성화 (로컬 개발 등)
    return <>{children}</>;
  }

  return (
    <PHProvider client={posthog}>
      <Suspense fallback={null}>
        <PostHogPageview />
      </Suspense>
      {children}
    </PHProvider>
  );
}
