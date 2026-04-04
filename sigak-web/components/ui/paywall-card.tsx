"use client";

import { Button } from "./button";

interface PaywallCardProps {
  label: string;
  price: number;
  totalNote?: string;
  onUnlock: () => void;
}

// 결제 유도 카드 컴포넌트
export function PaywallCard({ label, price, totalNote, onUnlock }: PaywallCardProps) {
  return (
    <div className="flex flex-col items-center gap-4 py-10 px-6">
      <p className="text-lg font-medium">{label}</p>
      {totalNote && (
        <p className="text-sm text-[var(--color-muted)]">{totalNote}</p>
      )}
      <Button variant="primary" size="lg" onClick={onUnlock}>
        {`₩${price.toLocaleString()} 잠금 해제`}
      </Button>
    </div>
  );
}
