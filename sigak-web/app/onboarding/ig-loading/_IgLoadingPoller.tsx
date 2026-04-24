"use client";

/**
 * Inner — key prop 으로 remount 되는 폴링 컴포넌트.
 * useIgStatus 를 담은 분리 컴포넌트 이유: retry 시 hook 재시작.
 */

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";

import { IgLoadingView } from "@/components/onboarding/IgLoadingView";
import { useIgStatus } from "@/hooks/useIgStatus";


export interface IgLoadingPollerProps {
  onRetry: () => void;
}


export function IgLoadingPoller({ onRetry }: IgLoadingPollerProps) {
  const router = useRouter();
  const result = useIgStatus({ enabled: true });

  const goToSia = useCallback(() => {
    router.replace("/sia");
  }, [router]);

  // 401 수신 시 로그인 리다이렉트
  useEffect(() => {
    if (result.error === "auth") {
      router.replace("/auth/login");
    }
  }, [result.error, router]);

  // 최종 상태 도달 시 짧은 딜레이 후 /sia 자동 이동
  useEffect(() => {
    if (!result.isTerminal) return;
    // success 는 "다 봤어요" 1.2초 표시 후 이동. 그 외는 0.6초.
    const delay = result.status === "success" ? 1200 : 600;
    const timer = setTimeout(goToSia, delay);
    return () => clearTimeout(timer);
  }, [result.isTerminal, result.status, goToSia]);

  return (
    <IgLoadingView
      result={result}
      onRetry={onRetry}
      onContinue={goToSia}
    />
  );
}
