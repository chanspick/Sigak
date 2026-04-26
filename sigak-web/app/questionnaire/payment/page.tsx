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
        <div className="border border-[var(--color-line)] p-5 mb-6">
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
            <div className="flex justify-between border-t border-[var(--color-line)] pt-3 mt-1">
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
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(account.replace(/-/g, ""));
              alert("계좌번호가 복사되었습니다. 은행 앱에서 붙여넣기로 입력해주세요.");
            }}
            className="flex items-center justify-center w-full py-3 text-sm font-semibold border border-[var(--color-line)] hover:bg-[var(--color-surface)] transition-all"
          >
            계좌번호 복사하기
          </button>
        </div>

        {/* 안내 */}
        <div className="bg-[var(--color-surface)] border border-[var(--color-line)] p-4 text-center">
          <p className="text-sm font-medium mb-1">
            송금 후 기다려 주세요
          </p>
          <p className="text-xs text-[var(--color-muted)] leading-relaxed">
            결제 확인 후 AI 분석을 시작합니다.<br />
            완료되면 카카오톡으로 리포트 링크를 보내드립니다.<br />
            평균 소요 시간: 24시간 이내
          </p>
        </div>

        {/* 카카오톡 채널 추가 */}
        <a
          href="http://pf.kakao.com/_GxfPxlX"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 mt-6 p-4 border border-[#FEE500]/40 bg-[#FEE500]/5 hover:bg-[#FEE500]/10 transition-all"
        >
          <div className="w-10 h-10 rounded-full bg-[#FEE500] flex items-center justify-center shrink-0">
            <svg viewBox="0 0 24 24" className="w-5 h-5" fill="#191919">
              <path d="M12 3C6.48 3 2 6.58 2 10.94c0 2.8 1.86 5.27 4.66 6.67-.15.53-.96 3.39-.99 3.61 0 0-.02.17.09.24.11.06.24.01.24.01.32-.04 3.7-2.44 4.28-2.86.55.08 1.13.13 1.72.13 5.52 0 10-3.58 10-7.94S17.52 3 12 3z"/>
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold">시각 카카오톡 채널 추가</p>
            <p className="text-[11px] text-[var(--color-muted)] mt-0.5">
              채널 추가 시 개인 번호가 아닌 비즈니스 메시지로 안내드립니다
            </p>
          </div>
          <svg className="w-4 h-4 opacity-30 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M6 3l5 5-5 5" />
          </svg>
        </a>

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
