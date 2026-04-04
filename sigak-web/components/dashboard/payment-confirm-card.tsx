"use client";

// 결제 확인 카드 컴포넌트
// - 유저명, requested_level, amount 표시
// - 경과 시간 (getElapsedTime)
// - 확인완료 버튼 (primary) / 미확인 버튼 (danger outline)

import { useState, useEffect } from "react";
import type { PaymentRequest } from "@/lib/types/payment";
import { getElapsedTime } from "@/lib/utils/date";
import { Button } from "@/components/ui/button";

interface PaymentConfirmCardProps {
  payment: PaymentRequest;
  onConfirm: (id: string) => void;
  onReject: (id: string) => void;
}

// 레벨 라벨 매핑
const levelLabels: Record<string, string> = {
  standard: "Standard",
  full: "Full",
};

// 결제 확인 카드 - 개별 결제 요청의 확인/미확인 처리 UI
export function PaymentConfirmCard({
  payment,
  onConfirm,
  onReject,
}: PaymentConfirmCardProps) {
  // 경과 시간 상태 (1초마다 갱신)
  const [elapsed, setElapsed] = useState(() =>
    getElapsedTime(payment.requested_at),
  );

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(getElapsedTime(payment.requested_at));
    }, 1000);

    return () => clearInterval(timer);
  }, [payment.requested_at]);

  return (
    <div className="flex items-center justify-between gap-4 py-4 px-5 border border-[var(--color-border)] rounded-lg">
      {/* 결제 정보 */}
      <div className="flex flex-col gap-1 min-w-0">
        {/* 유저명 + 레벨 */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold truncate">
            {payment.user_name}
          </span>
          <span className="px-2 py-0.5 text-[10px] font-semibold tracking-[1px] border border-[var(--color-fg)] rounded-full shrink-0">
            {levelLabels[payment.requested_level] ?? payment.requested_level}
          </span>
        </div>

        {/* 금액 + 경과 시간 */}
        <div className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
          <span className="font-medium text-[var(--color-fg)]">
            {`\u20A9${payment.amount.toLocaleString()}`}
          </span>
          <span className="w-px h-3 bg-[var(--color-border)]" />
          <span>{elapsed}</span>
        </div>
      </div>

      {/* 액션 버튼 */}
      <div className="flex items-center gap-2 shrink-0">
        {/* 확인완료 버튼 */}
        <Button
          variant="primary"
          size="sm"
          className="rounded-lg text-xs"
          onClick={() => onConfirm(payment.id)}
        >
          확인완료
        </Button>

        {/* 미확인 버튼 */}
        <button
          type="button"
          className="px-3 py-1.5 text-xs font-medium border border-[var(--color-danger)] text-[var(--color-danger)] rounded-lg hover:bg-[var(--color-danger)] hover:text-[var(--color-bg)] transition-colors"
          onClick={() => onReject(payment.id)}
        >
          미확인
        </button>
      </div>
    </div>
  );
}
