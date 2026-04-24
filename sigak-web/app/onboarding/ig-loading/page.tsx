"use client";

/**
 * /onboarding/ig-loading — Sia 진입 전 IG 분석 대기 페이지.
 *
 * 흐름:
 *   essentials 제출 → (ig_handle 있으면) 이 페이지로 라우팅
 *   useIgStatus 훅이 2.5초 간격 폴링
 *   status ∈ {success, private, failed, skipped} 도달 시 /sia 로 자동 이동
 *   401 수신 시 /auth/login
 *   timeout 시 에러 배너 + 재시도 CTA → 훅 재마운트
 */

import { useCallback, useState } from "react";

import { IgLoadingPoller } from "./_IgLoadingPoller";


export default function IgLoadingPage() {
  const [retryKey, setRetryKey] = useState(0);
  const handleRetry = useCallback(() => {
    setRetryKey((k) => k + 1);
  }, []);

  // retryKey 를 key prop 으로 → 자식 재마운트 → useIgStatus hook 재시작
  return <IgLoadingPoller key={retryKey} onRetry={handleRetry} />;
}
