// SIGAK MVP v1.2 — /tokens/fail
//
// Toss 결제 실패/취소 시 failUrl. 쿼리 code, message, orderId 표시.
"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

function FailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const code = searchParams.get("code") || "";
  const message = searchParams.get("message") || "결제가 완료되지 않았습니다.";
  const orderId = searchParams.get("orderId") || "";

  const isUserCancel = code === "PAY_PROCESS_CANCELED" || code === "USER_CANCEL";

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <TopBar backTarget="/tokens/purchase" />

      <main style={{ flex: 1, padding: "48px 24px 24px", maxWidth: 480, margin: "0 auto", width: "100%" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 28,
            fontWeight: 700,
            lineHeight: 1.35,
            letterSpacing: "-0.025em",
            margin: 0,
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          {isUserCancel ? "결제를 취소했어요" : "결제가 중단됐어요"}
          <span style={{ color: "var(--color-danger)" }}>.</span>
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 12,
            fontSize: 14,
            color: "var(--color-mute)",
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
          }}
        >
          {isUserCancel
            ? "다시 시도하거나 홈으로 돌아갈 수 있어요."
            : message}
        </p>

        {!isUserCancel && (code || orderId) && (
          <div
            style={{
              marginTop: 24,
              background: "rgba(0, 0, 0, 0.04)",
              border: "1px solid var(--color-line)",
              borderRadius: 14,
              padding: "12px 18px",
            }}
          >
            {code && <InfoRow label="CODE" value={code} />}
            {orderId && <InfoRow label="ORDER" value={orderId} />}
          </div>
        )}

        {!isUserCancel && (
          <p
            className="font-sans"
            style={{
              marginTop: 18,
              fontSize: 12,
              color: "var(--color-mute)",
              lineHeight: 1.7,
              letterSpacing: "-0.005em",
            }}
          >
            문의:{" "}
            <a
              href="mailto:partner@sigak.asia"
              style={{
                textDecoration: "underline",
                textUnderlineOffset: 2,
                color: "var(--color-ink)",
              }}
            >
              partner@sigak.asia
            </a>
          </p>
        )}
      </main>

      <div
        style={{
          padding: "20px 24px 32px",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          maxWidth: 480,
          margin: "0 auto",
          width: "100%",
        }}
      >
        <button
          type="button"
          onClick={() => router.replace("/tokens/purchase")}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            padding: "17px 24px",
            background: "var(--color-ink)",
            color: "var(--color-paper)",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          다시 시도
        </button>
        <Link
          href="/"
          className="font-sans"
          style={{
            textAlign: "center",
            fontSize: 13,
            color: "var(--color-mute)",
            letterSpacing: "-0.005em",
            textDecoration: "none",
            padding: "8px 0",
          }}
        >
          홈으로
        </Link>
      </div>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "8px 0",
      }}
    >
      <span
        className="uppercase"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          letterSpacing: "0.12em",
          color: "var(--color-mute)",
        }}
      >
        {label}
      </span>
      <span
        className="tabular-nums"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--color-ink)",
        }}
      >
        {value}
      </span>
    </div>
  );
}

export default function FailPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", background: "var(--color-paper)" }} />}>
      <FailContent />
    </Suspense>
  );
}
