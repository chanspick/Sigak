"use client";

// 토스페이먼츠 결제 성공 → 서버 승인 → 리포트 이동
// successUrl: /payment/success?paymentKey=xxx&orderId=xxx&amount=xxx
//
// 마케터 톤 정합 (2026-04-26): Noto Serif 헤드라인 + period accent +
// pill CTA + 카드 시각 (radius 14 + soft bg). Tailwind → inline 통일.

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
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
        padding: "40px 24px",
      }}
    >
      <div style={{ maxWidth: 380, width: "100%", textAlign: "center" }}>
        <p
          className="uppercase"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.3em",
            color: "var(--color-mute)",
            marginBottom: 24,
          }}
        >
          SIGAK
        </p>

        {status === "confirming" && (
          <>
            <div
              style={{
                width: 32,
                height: 32,
                border: "2px solid var(--color-ink)",
                borderTopColor: "transparent",
                borderRadius: "50%",
                margin: "0 auto 18px",
                animation: "spin 1s linear infinite",
              }}
              aria-hidden
            />
            <h1
              className="font-serif"
              style={{
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                margin: 0,
                color: "var(--color-ink)",
              }}
            >
              결제 확인 중
              <span style={{ color: "var(--color-danger)" }}>.</span>
            </h1>
            <p
              className="font-sans"
              style={{
                marginTop: 10,
                fontSize: 13.5,
                color: "var(--color-mute)",
                letterSpacing: "-0.005em",
              }}
            >
              잠시만 기다려 주세요...
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: "50%",
                background: "var(--color-ink)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 22px",
              }}
              aria-hidden
            >
              <svg width="24" height="20" viewBox="0 0 24 20" fill="none">
                <path
                  d="M2 10L8.5 16.5L22 3"
                  stroke="white"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <h1
              className="font-serif"
              style={{
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                margin: 0,
                color: "var(--color-ink)",
                marginBottom: 8,
              }}
            >
              결제 완료
              <span style={{ color: "var(--color-danger)" }}>.</span>
            </h1>
            <p
              className="font-sans"
              style={{
                margin: 0,
                fontSize: 13.5,
                color: "var(--color-mute)",
                letterSpacing: "-0.005em",
                lineHeight: 1.65,
              }}
            >
              AI 분석을 시작합니다.
              <br />
              완료되면 자동으로 리포트 페이지로 이동합니다.
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: "50%",
                background: "rgba(163, 45, 45, 0.08)",
                border: "1.5px solid rgba(163, 45, 45, 0.4)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 22px",
              }}
              aria-hidden
            >
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <path
                  d="M11 7V12"
                  stroke="var(--color-danger)"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <circle cx="11" cy="15.5" r="1.2" fill="var(--color-danger)" />
              </svg>
            </div>
            <h1
              className="font-serif"
              style={{
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                margin: 0,
                color: "var(--color-ink)",
                marginBottom: 8,
              }}
            >
              결제 오류
              <span style={{ color: "var(--color-danger)" }}>.</span>
            </h1>
            <p
              style={{
                margin: "0 0 24px",
                fontSize: 13.5,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
                lineHeight: 1.6,
              }}
            >
              {errorMsg}
            </p>
            <a
              href="/sia"
              className="font-sans"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "13px 32px",
                background: "var(--color-ink)",
                color: "var(--color-paper)",
                border: "none",
                borderRadius: 100,
                fontSize: 14,
                fontWeight: 600,
                letterSpacing: "-0.01em",
                textDecoration: "none",
              }}
            >
              다시 시도하기
            </a>
          </>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

export default function PaymentSuccessPage() {
  return (
    <Suspense
      fallback={<div style={{ minHeight: "100vh", background: "var(--color-paper)" }} />}
    >
      <SuccessContent />
    </Suspense>
  );
}
