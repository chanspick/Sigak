/**
 * LoadingSlides — 분석 / 리포트 생성 대기 화면.
 *
 * Phase B-8 (PI-REVIVE 2026-04-27): 본인 결정 — 5장 carousel 폐기,
 * 단일 SigakLoading (redesign/로딩_1815.html 패턴) 으로 통일.
 * 이전: 5 슬라이드 × 5초 cycling messages → 본인 피드백
 *       "로딩창들 너무 많고 병렬적이고 메시지가 다 달라서".
 * 이후: SIGAK 로고 + 단일 message + 3-dot pulse + hint.
 *
 * Props 호환성 보존:
 *   - onComplete (옵션): SLIDE_DURATION_MS 후 콜백 호출 (caller redirect 용).
 *     없으면 backend 응답까지 무한 hold (기존 동작).
 *   - message / hint (Phase B-8 신규, 옵션): 컨텍스트별 카피 override.
 *
 * 기존 callers 모두 호환:
 *   - /sia/done: <LoadingSlides onComplete={...} />  (15s 단일 hold + redirect)
 *   - /aspiration: <LoadingSlides />                  (응답까지 hold)
 *   - /best-shot:  <LoadingSlides ... />              (응답까지 hold)
 */

"use client";

import { useEffect, useRef } from "react";
import { SigakLoading } from "@/components/ui/sigak/sigak-loading";

const COMPLETE_DELAY_MS = 25000; // 기존 5장 × 5초 = 25초 유지 (onComplete 호출 시점)

interface LoadingSlidesProps {
  /** 옵션: 일정 시간 후 콜백. 없으면 무한 hold (caller 가 unmount). */
  onComplete?: () => void;
  /** Phase B-8 신규: 컨텍스트별 메시지 override. 기본: "잠시만요, 분석중이에요." */
  message?: string;
  /** Phase B-8 신규: 힌트 override. 기본: "최대 30초 정도 걸릴 수 있어요" */
  hint?: string;
}

export function LoadingSlides({
  onComplete,
  message,
  hint,
}: LoadingSlidesProps = {}) {
  const completedRef = useRef(false);

  useEffect(() => {
    if (!onComplete) return;
    if (completedRef.current) return;
    const t = setTimeout(() => {
      if (!completedRef.current) {
        completedRef.current = true;
        onComplete();
      }
    }, COMPLETE_DELAY_MS);
    return () => clearTimeout(t);
  }, [onComplete]);

  return <SigakLoading message={message} hint={hint} />;
}
