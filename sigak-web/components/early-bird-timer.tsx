"use client";

import { useState, useEffect } from "react";

const DEADLINE = new Date("2026-04-28T23:59:59+09:00");

function getTimeLeft() {
  const diff = DEADLINE.getTime() - Date.now();
  if (diff <= 0) return null;
  return {
    days: Math.floor(diff / (1000 * 60 * 60 * 24)),
    hours: Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
    minutes: Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60)),
    seconds: Math.floor((diff % (1000 * 60)) / 1000),
  };
}

function pad(n: number) {
  return n.toString().padStart(2, "0");
}

export function EarlyBirdTimer() {
  // SSR hydration mismatch 방지: 초기값 null, 클라이언트에서만 시작
  const [time, setTime] = useState<ReturnType<typeof getTimeLeft>>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setTime(getTimeLeft());
    const interval = setInterval(() => setTime(getTimeLeft()), 1000);
    return () => clearInterval(interval);
  }, []);

  // SSR 또는 마감 지나면 숨김
  if (!mounted || !time) return null;

  return (
    <div className="py-8 text-center">
      <span className="block text-[10px] font-bold tracking-[2px] opacity-30 mb-3">
        EARLY BIRD
      </span>
      <p className="font-[family-name:var(--font-serif)] text-[clamp(28px,4vw,40px)] font-normal tracking-[1px] mb-3">
        {time.days}일 {pad(time.hours)}:{pad(time.minutes)}:{pad(time.seconds)}
      </p>
      <p className="text-[13px] opacity-40 leading-[1.6]">
        얼리버드 할인이 종료되면 오버뷰 ₩5,000 · 풀 리포트 ₩49,000으로 복귀됩니다.
      </p>
    </div>
  );
}
