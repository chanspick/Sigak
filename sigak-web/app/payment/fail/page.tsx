"use client";

// 토스페이먼츠 결제 실패 페이지
// failUrl: /payment/fail?code=xxx&message=xxx
//
// 마케터 톤 정합 (2026-04-26).

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

function FailContent() {
  const searchParams = useSearchParams();
  const code = searchParams.get("code") || "";
  const message = searchParams.get("message") || "결제가 취소되었습니다";

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
          결제 실패
          <span style={{ color: "var(--color-danger)" }}>.</span>
        </h1>
        <p
          style={{
            margin: 0,
            fontSize: 13.5,
            color: "var(--color-mute)",
            letterSpacing: "-0.005em",
            lineHeight: 1.6,
          }}
        >
          {message}
        </p>
        {code && (
          <p
            className="tabular-nums"
            style={{
              marginTop: 8,
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-mute-2)",
              letterSpacing: "0.04em",
              marginBottom: 28,
            }}
          >
            오류 코드: {code}
          </p>
        )}
        {!code && <div style={{ height: 28 }} />}

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
          돌아가기
        </a>
      </div>
    </div>
  );
}

export default function PaymentFailPage() {
  return (
    <Suspense
      fallback={<div style={{ minHeight: "100vh", background: "var(--color-paper)" }} />}
    >
      <FailContent />
    </Suspense>
  );
}
