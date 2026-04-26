"use client";

// 결제 확인 대기 카드
// - "확인 대기 중..." 텍스트
// - 경과 시간 표시 (getElapsedTime 사용)
// - 1초마다 경과 시간 업데이트
// - 부드러운 펄스 애니메이션

import { useState, useEffect } from "react";
import { getElapsedTime } from "@/lib/utils/date";

interface PendingCardProps {
  requestedAt: string;
}

// 결제 확인 대기 UI - 경과 시간과 함께 대기 상태 표시
export function PendingCard({ requestedAt }: PendingCardProps) {
  // 경과 시간 상태 (1초마다 갱신)
  const [elapsed, setElapsed] = useState(() => getElapsedTime(requestedAt));

  useEffect(() => {
    // 1초 간격으로 경과 시간 업데이트
    const timer = setInterval(() => {
      setElapsed(getElapsedTime(requestedAt));
    }, 1000);

    return () => clearInterval(timer);
  }, [requestedAt]);

  return (
    <div className="flex flex-col items-center gap-3 py-8 px-6 border border-[var(--color-line)] rounded-lg max-w-sm mx-auto">
      {/* 펄스 인디케이터 */}
      <div className="relative flex items-center justify-center">
        <span className="absolute w-8 h-8 rounded-full bg-[var(--color-fg)] opacity-10 animate-ping" />
        <span className="w-3 h-3 rounded-full bg-[var(--color-fg)]" />
      </div>

      {/* 대기 메시지 */}
      <p className="text-base font-semibold animate-pulse">
        확인 대기 중...
      </p>

      {/* 경과 시간 */}
      <p className="text-sm text-[var(--color-muted)]">
        {elapsed}
      </p>

      {/* 안내 텍스트 */}
      <p className="text-[10px] text-[var(--color-muted)] text-center leading-relaxed">
        관리자가 송금을 확인하면 자동으로 잠금이 해제됩니다.
      </p>
    </div>
  );
}
