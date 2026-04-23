"use client";

// 토스페이먼츠 결제 실패 페이지
// failUrl: /payment/fail?code=xxx&message=xxx

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

function FailContent() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") || "";
  const message = searchParams.get("message") || "결제가 취소되었습니다";

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] text-[var(--color-fg)]">
      <div className="max-w-sm w-full text-center px-6">
        <p className="text-xs tracking-[3px] uppercase text-[var(--color-muted)] mb-4">SIGAK</p>
        <h1 className="font-[family-name:var(--font-serif)] text-xl mb-2">결제 실패</h1>
        <p className="text-sm text-[var(--color-muted)] mb-1">{message}</p>
        {code && <p className="text-xs text-[var(--color-muted)] mb-6">오류 코드: {code}</p>}
        <a
          href="/sia"
          className="inline-block py-3 px-8 text-sm font-semibold border border-[var(--color-fg)] text-[var(--color-fg)] hover:bg-[var(--color-fg)] hover:text-[var(--color-bg)] transition-all"
        >
          돌아가기
        </a>
      </div>
    </div>
  );
}

export default function PaymentFailPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg)]" />}>
      <FailContent />
    </Suspense>
  );
}
