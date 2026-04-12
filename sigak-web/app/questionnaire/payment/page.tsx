"use client";

// 송금 안내 페이지 — /questionnaire/payment
// submit 완료 후 이동. 결제 정보 표시 + 딥링크 + 완료 안내.

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Button } from "@/components/ui/button";

function PaymentContent() {
  const params = useSearchParams();
  const orderId = params.get("order_id") ?? "";
  const amount = Number(params.get("amount") ?? "49000");
  const bank = params.get("bank") ?? "토스뱅크";
  const account = params.get("account") ?? "";
  const holder = params.get("holder") ?? "";
  const tossLink = params.get("toss") ?? "";
  const kakaoLink = params.get("kakao") ?? "";

  const formattedAmount = `₩${amount.toLocaleString()}`;

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)] flex items-center justify-center px-5">
      <div className="max-w-sm w-full">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <p className="text-xs tracking-[3px] uppercase text-[var(--color-muted)] mb-2">
            SIGAK
          </p>
          <h1 className="font-[family-name:var(--font-serif)] text-xl font-normal mb-2">
            주문이 접수되었습니다
          </h1>
          <p className="text-sm text-[var(--color-muted)]">
            송금 확인 후 분석을 시작합니다
          </p>
        </div>

        {/* 결제 정보 카드 */}
        <div className="border border-[var(--color-border)] p-5 mb-6">
          <div className="flex flex-col gap-3 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--color-muted)]">은행</span>
              <span className="font-medium">{bank}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-muted)]">계좌번호</span>
              <span className="font-medium">{account}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-muted)]">예금주</span>
              <span className="font-medium">{holder}</span>
            </div>
            <div className="flex justify-between border-t border-[var(--color-border)] pt-3 mt-1">
              <span className="text-[var(--color-muted)]">금액</span>
              <span className="font-bold text-lg">{formattedAmount}</span>
            </div>
          </div>
        </div>

        {/* 송금 딥링크 버튼 */}
        <div className="flex flex-col gap-3 mb-6">
          {tossLink && (
            <a
              href={tossLink}
              className="flex items-center justify-center w-full py-3 text-sm font-semibold border border-[#0064FF] text-[#0064FF] hover:bg-[#0064FF]/5 transition-all"
            >
              토스로 송금하기
            </a>
          )}
          {kakaoLink && (
            <a
              href={kakaoLink}
              className="flex items-center justify-center w-full py-3 text-sm font-semibold bg-[#FEE500] text-[#191919] hover:brightness-95 transition-all"
            >
              카카오페이로 송금하기
            </a>
          )}
        </div>

        {/* 안내 */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-border)] p-4 text-center">
          <p className="text-sm font-medium mb-1">
            송금 후 기다려 주세요
          </p>
          <p className="text-xs text-[var(--color-muted)] leading-relaxed">
            결제 확인 후 AI 분석을 시작합니다.<br />
            완료되면 카카오톡으로 리포트 링크를 보내드립니다.<br />
            평균 소요 시간: 24시간 이내
          </p>
        </div>

        {/* 주문 번호 */}
        <p className="text-[10px] text-[var(--color-muted)] text-center mt-6">
          주문번호: {orderId}
        </p>
      </div>
    </div>
  );
}

export default function PaymentPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <PaymentContent />
    </Suspense>
  );
}
