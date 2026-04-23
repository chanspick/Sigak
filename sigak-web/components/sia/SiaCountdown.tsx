"use client";

/**
 * SiaCountdown — Phase H 대화 5분 soft limit 의 30초 이하 경고 카운트다운.
 *
 * 규격 (사용자 ⑤ 확정):
 *   - 노출 임계치: 30초 이하만 노출. 그 이상은 `null` 반환 (hidden).
 *   - 포맷: "M:SS" (예: "0:27"). 0초 도달 시 "0:00" 렌더 후 onExpire 호출.
 *   - 색상: var(--color-danger) + opacity pulse (`.animate-sia-countdown-pulse`).
 *   - 폰트: tabular-nums, 11px 600, letter-spacing 0.5px.
 *   - 접근성: aria-live="polite" — 매초 값 변경 시 낭독 (OS/AT 가 빈도 조절).
 *
 * onExpire:
 *   - 컴포넌트가 remainingSeconds <= 0 을 감지하면 한 번만 호출.
 *   - 값이 다시 양수로 바뀌면 fire 플래그 리셋 (세션 재시작 같은 엣지 대응).
 */
import { useEffect, useRef } from "react";

export interface SiaCountdownProps {
  /** 남은 초. 0 이하 = 만료. */
  remainingSeconds: number;
  /** 0 도달 시 1회만 호출. */
  onExpire?: () => void;
}

const THRESHOLD_SECONDS = 30;

function formatTime(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const m = Math.floor(safe / 60);
  const s = safe % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function SiaCountdown({
  remainingSeconds,
  onExpire,
}: SiaCountdownProps) {
  const firedRef = useRef(false);

  useEffect(() => {
    if (remainingSeconds <= 0) {
      if (!firedRef.current) {
        firedRef.current = true;
        onExpire?.();
      }
    } else {
      firedRef.current = false;
    }
  }, [remainingSeconds, onExpire]);

  if (remainingSeconds > THRESHOLD_SECONDS) {
    return null;
  }

  return (
    <span
      className="animate-sia-countdown-pulse text-[11px] font-semibold tabular-nums text-[var(--color-danger)]"
      style={{ letterSpacing: "0.5px" }}
      aria-live="polite"
      data-testid="sia-countdown"
    >
      {formatTime(remainingSeconds)}
    </span>
  );
}
