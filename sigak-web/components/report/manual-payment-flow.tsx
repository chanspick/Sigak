"use client";

// 수동 결제 플로우 - 카카오톡 송금 UI
// 1. 은행/계좌/예금주/금액 정보 표시
// 2. 카카오톡 송금 딥링크 버튼
// 3. "송금 완료했어요" 버튼 → onComplete 콜백 호출

import type { PaywallTier, PaymentAccount } from "@/lib/types/report";
import { Button } from "@/components/ui/button";

interface ManualPaymentFlowProps {
  paywall: PaywallTier;
  paymentAccount: PaymentAccount;
  onComplete: () => void;
}

// 수동 결제 UI - 계좌 정보 표시 및 카카오톡 딥링크 제공
export function ManualPaymentFlow({
  paywall,
  paymentAccount,
  onComplete,
}: ManualPaymentFlowProps) {
  return (
    <div className="border border-[var(--color-border)] rounded-lg p-6 max-w-sm mx-auto">
      {/* 결제 안내 헤더 */}
      <h3 className="text-lg font-bold mb-1 text-center">
        {paywall.label}
      </h3>
      {paywall.total_note && (
        <p className="text-xs text-[var(--color-muted)] text-center mb-6">
          {paywall.total_note}
        </p>
      )}

      {/* 계좌 정보 영역 */}
      <div className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg p-4 mb-6">
        <div className="flex flex-col gap-2 text-sm">
          {/* 은행명 */}
          <div className="flex justify-between">
            <span className="text-[var(--color-muted)]">은행</span>
            <span className="font-medium">{paymentAccount.bank}</span>
          </div>
          {/* 계좌번호 */}
          <div className="flex justify-between">
            <span className="text-[var(--color-muted)]">계좌번호</span>
            <span className="font-medium">{paymentAccount.number}</span>
          </div>
          {/* 예금주 */}
          <div className="flex justify-between">
            <span className="text-[var(--color-muted)]">예금주</span>
            <span className="font-medium">{paymentAccount.holder}</span>
          </div>
          {/* 금액 */}
          <div className="flex justify-between border-t border-[var(--color-border)] pt-2 mt-1">
            <span className="text-[var(--color-muted)]">금액</span>
            <span className="font-bold text-base">
              {paywall.original_price && (
                <span className="line-through opacity-40 font-normal text-sm mr-1.5">
                  {`\u20A9${paywall.original_price.toLocaleString()}`}
                </span>
              )}
              {`\u20A9${paywall.price.toLocaleString()}`}
            </span>
          </div>
        </div>
      </div>

      {/* 카카오뱅크 앱 열기 + 계좌 복사 */}
      <button
        type="button"
        onClick={() => {
          navigator.clipboard.writeText(paymentAccount.number.replace(/-/g, ""));
          window.location.href = "kakaobank://";
          setTimeout(() => {
            alert("카카오뱅크 앱에서 붙여넣기로 계좌번호를 입력해주세요");
          }, 1500);
        }}
        className="flex items-center justify-center w-full py-3 mb-3 text-sm font-semibold rounded-lg bg-[#FEE500] text-[#191919] hover:brightness-95 transition-all"
      >
        카카오뱅크로 송금하기
      </button>

      {/* 송금 완료 버튼 */}
      <Button
        variant="primary"
        size="md"
        className="w-full rounded-lg"
        onClick={onComplete}
      >
        송금 완료했어요
      </Button>

      {/* 안내 텍스트 */}
      <p className="text-[10px] text-[var(--color-muted)] text-center mt-4 leading-relaxed">
        송금 완료 후 버튼을 눌러주세요.<br />
        관리자 확인 후 자동으로 잠금이 해제됩니다.
      </p>
    </div>
  );
}
