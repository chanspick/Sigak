"use client";

// 토스페이먼츠 결제 성공 → 서버 승인 → 리포트 이동
// successUrl: /payment/success?paymentKey=xxx&orderId=xxx&amount=xxx

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { confirmTossPayment } from "@/lib/api/client";

function SuccessContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"confirming" | "success" | "error">("confirming");
  const [errorMsg, setErrorMsg] = useState("");
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;

    const paymentKey = searchParams.get("paymentKey");
    const orderId = searchParams.get("orderId");
    const amount = searchParams.get("amount");

    if (!paymentKey || !orderId || !amount) {
      setStatus("error");
      setErrorMsg("결제 정보가 올바르지 않습니다");
      return;
    }

    processedRef.current = true;

    (async () => {
      try {
        const result = await confirmTossPayment({
          paymentKey,
          orderId,
          amount: Number(amount),
        });

        setStatus("success");

        // 리포트 준비 완료 시 이동, 아니면 대기 안내
        if (result.report_id) {
          setTimeout(() => {
            router.replace(`/report/${result.report_id}`);
          }, 2000);
        }
      } catch (err) {
        processedRef.current = false;
        setStatus("error");
        setErrorMsg(err instanceof Error ? err.message : "결제 승인에 실패했습니다");
      }
    })();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] text-[var(--color-fg)]">
      <div className="max-w-sm w-full text-center px-6">
        <p className="text-xs tracking-[3px] uppercase text-[var(--color-muted)] mb-4">SIGAK</p>

        {status === "confirming" && (
          <>
            <div className="w-8 h-8 border-2 border-[var(--color-fg)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h1 className="font-[family-name:var(--font-serif)] text-xl mb-2">결제 확인 중</h1>
            <p className="text-sm text-[var(--color-muted)]">잠시만 기다려 주세요...</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="w-12 h-12 rounded-full border-2 border-[var(--color-fg)] flex items-center justify-center mx-auto mb-4">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12" /></svg>
            </div>
            <h1 className="font-[family-name:var(--font-serif)] text-xl mb-2">결제 완료</h1>
            <p className="text-sm text-[var(--color-muted)]">
              AI 분석을 시작합니다.<br />
              완료되면 자동으로 리포트 페이지로 이동합니다.
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <h1 className="font-[family-name:var(--font-serif)] text-xl mb-2">결제 오류</h1>
            <p className="text-sm text-red-500 mb-4">{errorMsg}</p>
            <a href="/start" className="text-sm font-medium underline text-[var(--color-fg)]">
              다시 시도하기
            </a>
          </>
        )}
      </div>
    </div>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg)]" />}>
      <SuccessContent />
    </Suspense>
  );
}
