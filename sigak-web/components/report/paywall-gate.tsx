"use client";

// 페이월 게이트 컴포넌트
// - locked (해당 레벨 미해제): PaywallCard 표시 → 클릭 시 결제 플로우 시작
//   - method === "manual": 기존 수동 결제 (카카오톡 송금)
//   - method === "auto": 토스페이먼츠 위젯 결제
// - pending (결제 대기 중): PendingCard 표시
// - unlocked (해제 완료): null 반환 (렌더링 없음)

import { useState } from "react";
import type { AccessLevel, UnlockLevel, PaywallTier, PaymentAccount } from "@/lib/types/report";
import { isPendingLevel } from "@/lib/utils/report";
import { PaywallCard } from "@/components/ui/paywall-card";
import { PendingCard } from "./pending-card";
import { TossPaymentFlow } from "./toss-payment-flow";

interface PaywallGateProps {
  level: UnlockLevel;
  accessLevel: AccessLevel;
  paywall: PaywallTier;
  paymentAccount: PaymentAccount;
  pendingAt: string | null;
  orderId?: string;
  onPaymentComplete: () => void;
}

// 페이월 게이트 - 3가지 상태(잠김/대기중/해제)에 따른 조건부 렌더링
export function PaywallGate({
  level,
  accessLevel,
  paywall,
  pendingAt,
  orderId,
  onPaymentComplete,
}: PaywallGateProps) {
  const [loading, setLoading] = useState(false);
  const [showTossWidget, setShowTossWidget] = useState(false);

  // 해제 완료 상태 판별
  const isUnlocked =
    (level === "standard" && ["standard", "full_pending", "full"].includes(accessLevel)) ||
    (level === "full" && accessLevel === "full");

  // 해제 완료 → 렌더링 없음
  if (isUnlocked) return null;

  // 결제 대기 중 상태
  const isPending = isPendingLevel(accessLevel, level);

  if (isPending && pendingAt) {
    return (
      <div className="py-6">
        <PendingCard requestedAt={pendingAt} />
      </div>
    );
  }

  // 토스 위젯 결제 모드 — 버튼 클릭 후 위젯 표시
  if (showTossWidget && orderId) {
    const userName = typeof window !== "undefined" ? localStorage.getItem("sigak_user_name") || "" : "";
    const userEmail = typeof window !== "undefined" ? localStorage.getItem("sigak_user_email") || "" : "";

    return (
      <div className="py-6">
        <TossPaymentFlow
          orderId={orderId}
          orderName={`시각 ${level === "full" ? "풀" : "스탠다드"} 리포트`}
          amount={paywall.price}
          customerName={userName || undefined}
          customerEmail={userEmail || undefined}
        />
      </div>
    );
  }

  // 잠금 상태 → PaywallCard 클릭 시 결제 플로우 시작
  return (
    <div className="py-6">
      <PaywallCard
        label={paywall.label}
        price={paywall.price}
        originalPrice={paywall.original_price}
        totalNote={paywall.total_note}
        loading={loading}
        onUnlock={() => {
          if (paywall.method === "auto") {
            // 토스 위젯: 먼저 주문 생성 후 위젯 표시
            setLoading(true);
            onPaymentComplete();
            setShowTossWidget(true);
          } else {
            // 수동 결제: 기존 플로우
            setLoading(true);
            onPaymentComplete();
          }
        }}
      />
    </div>
  );
}
