"use client";

// 결제 확인 대시보드 (알바용)
// - pending 목록: 유저명, 티어, 레벨, 금액, 경과시간
// - 각 항목: 확인완료/미확인 버튼 2개
// - 오늘 완료 목록 하단 표시 (confirmed today)

import { useState } from "react";
import type { PaymentRequest } from "@/lib/types/payment";
import { PaymentConfirmCard } from "./payment-confirm-card";

interface PaymentsViewProps {
  payments: PaymentRequest[];
}

// 결제 확인 뷰 - 대기 중 결제와 오늘 확인 완료 결제 표시
export function PaymentsView({ payments: initialPayments }: PaymentsViewProps) {
  // 결제 목록 상태 (확인/미확인 처리 시 업데이트)
  const [payments, setPayments] = useState<PaymentRequest[]>(initialPayments);

  // 대기 중 결제 필터링
  const pendingPayments = payments.filter((p) => p.status === "pending");

  // 오늘 확인 완료된 결제 필터링
  const today = new Date().toISOString().split("T")[0];
  const confirmedToday = payments.filter(
    (p) =>
      p.status === "confirmed" &&
      p.confirmed_at &&
      p.confirmed_at.startsWith(today),
  );

  // 확인완료 처리
  const handleConfirm = (id: string) => {
    // 실제로는 PUT /api/v1/payments/{id}/confirm 호출
    setPayments((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              status: "confirmed" as const,
              confirmed_at: new Date().toISOString(),
              confirmed_by: "관리자",
            }
          : p,
      ),
    );
  };

  // 미확인 처리
  const handleReject = (id: string) => {
    // 실제로는 PUT /api/v1/payments/{id}/reject 호출
    setPayments((prev) =>
      prev.map((p) =>
        p.id === id
          ? { ...p, status: "unconfirmed" as const }
          : p,
      ),
    );
  };

  return (
    <div>
      {/* 대기 중 섹션 */}
      <div className="mb-10">
        <div className="flex items-baseline gap-2 mb-4">
          <h2 className="text-sm font-bold tracking-[1px]">대기 중</h2>
          <span className="text-xs text-[var(--color-muted)]">
            {pendingPayments.length}건
          </span>
        </div>

        {pendingPayments.length === 0 ? (
          <p className="text-sm text-[var(--color-muted)] py-8 text-center">
            대기 중인 결제가 없습니다.
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {pendingPayments.map((payment) => (
              <PaymentConfirmCard
                key={payment.id}
                payment={payment}
                onConfirm={handleConfirm}
                onReject={handleReject}
              />
            ))}
          </div>
        )}
      </div>

      {/* 오늘 확인 완료 섹션 */}
      {confirmedToday.length > 0 && (
        <div>
          <div className="flex items-baseline gap-2 mb-4">
            <h2 className="text-sm font-bold tracking-[1px]">오늘 확인 완료</h2>
            <span className="text-xs text-[var(--color-muted)]">
              {confirmedToday.length}건
            </span>
          </div>

          <div className="flex flex-col gap-2">
            {confirmedToday.map((payment) => (
              <div
                key={payment.id}
                className="flex items-center justify-between py-3 px-4 border border-[var(--color-border)] rounded-lg opacity-60"
              >
                {/* 유저 정보 */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">
                    {payment.user_name}
                  </span>
                  <span className="text-xs text-[var(--color-muted)]">
                    {`\u20A9${payment.amount.toLocaleString()}`}
                  </span>
                </div>
                {/* 확인 완료 배지 */}
                <span className="text-[10px] font-semibold text-[var(--color-muted)]">
                  확인 완료
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
