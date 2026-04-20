// SIGAK MVP v1.2 — /tokens/fail
//
// Toss 결제 실패/취소 시 failUrl. 쿼리 code, message, orderId 표시.
"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PrimaryButton, TopBar } from "@/components/ui/sigak";
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

      <main style={{ flex: 1, padding: "48px 28px 24px" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 32,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          {isUserCancel ? "결제를 취소했어요." : "결제가 중단됐어요."}
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 16,
            fontSize: 13,
            opacity: 0.55,
            lineHeight: 1.7,
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
              marginTop: 28,
              paddingTop: 14,
              paddingBottom: 14,
              borderTop: "1px solid rgba(0, 0, 0, 0.1)",
              borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
            }}
          >
            {code && (
              <InfoRow label="code" value={code} />
            )}
            {orderId && (
              <InfoRow label="order" value={orderId} />
            )}
          </div>
        )}

        {!isUserCancel && (
          <p
            className="font-sans"
            style={{
              marginTop: 20,
              fontSize: 12,
              opacity: 0.5,
              lineHeight: 1.7,
              letterSpacing: "-0.005em",
            }}
          >
            문의:{" "}
            <a
              href="mailto:partner@sigak.asia"
              style={{ textDecoration: "underline", textUnderlineOffset: 2 }}
            >
              partner@sigak.asia
            </a>
          </p>
        )}
      </main>

      <div style={{ padding: "20px 28px 32px", display: "flex", flexDirection: "column", gap: 10 }}>
        <PrimaryButton onClick={() => router.replace("/tokens/purchase")}>
          다시 시도
        </PrimaryButton>
        <Link
          href="/"
          className="font-sans"
          style={{
            textAlign: "center",
            fontSize: 13,
            opacity: 0.55,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
            textDecoration: "none",
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
        padding: "6px 0",
      }}
    >
      <span
        className="font-sans uppercase"
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "1.5px",
          opacity: 0.4,
          color: "var(--color-ink)",
        }}
      >
        {label}
      </span>
      <span
        className="font-mono tabular-nums"
        style={{ fontSize: 11, opacity: 0.8, color: "var(--color-ink)" }}
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
