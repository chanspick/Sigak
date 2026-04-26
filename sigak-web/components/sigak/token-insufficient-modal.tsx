// SIGAK — TokenInsufficientModal
//
// 마케터 redesign/토큰부족_모달_1815.html 차용. bottom sheet (slideUp).
//
// 호출 예:
//   <TokenInsufficientModal
//     open={lowBalance}
//     balance={2}
//     required={20}
//     onCharge={() => router.push("/tokens/purchase")}
//     onClose={() => setOpen(false)}
//   />
//
// 디자인 토큰: 우리 globals.css 그대로 (--color-paper / --color-ink /
// --color-mute / --color-line / --color-danger / --font-serif / --font-mono)
"use client";

import { useEffect } from "react";

interface TokenInsufficientModalProps {
  open: boolean;
  balance: number;
  required: number;
  onCharge: () => void;
  onClose: () => void;
  /** 옵션: title/sub override (default: "토큰이 부족해요" / "이 기능을 사용하려면 토큰이 더 필요해요.") */
  title?: string;
  sub?: string;
}

export function TokenInsufficientModal({
  open,
  balance,
  required,
  onCharge,
  onClose,
  title = "토큰이 부족해요",
  sub = "이 기능을 사용하려면 토큰이 더 필요해요.",
}: TokenInsufficientModalProps) {
  // ESC 키로 닫기
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    // body scroll lock
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handler);
      document.body.style.overflow = original;
    };
  }, [open, onClose]);

  if (!open) return null;

  const shortage = Math.max(required - balance, 0);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="token-insufficient-title"
      onClick={onClose}
      className="animate-modal-fade-in"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(45, 45, 45, 0.45)",
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        zIndex: 200,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="animate-modal-slide-up"
        style={{
          background: "var(--color-paper)",
          borderRadius: "20px 20px 0 0",
          padding: "12px 24px 32px",
          width: "100%",
          maxWidth: 480,
          paddingBottom: "max(32px, env(safe-area-inset-bottom))",
        }}
      >
        {/* handle bar */}
        <div
          aria-hidden
          style={{
            width: 36,
            height: 4,
            borderRadius: 2,
            background: "var(--color-line-strong)",
            margin: "0 auto 28px",
          }}
        />

        {/* 경고 아이콘 (ember-softer 배경 + 1.5px ember border + svg) */}
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
        >
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
            <path
              d="M11 7V12"
              stroke="var(--color-danger)"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx="11" cy="15.5" r="1.2" fill="var(--color-danger)" />
            <path
              d="M9.27 3.5L1.5 17.5A2 2 0 003.23 20.5h15.54A2 2 0 0020.5 17.5L12.73 3.5a2 2 0 00-3.46 0Z"
              stroke="var(--color-danger)"
              strokeWidth="1.8"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        <h2
          id="token-insufficient-title"
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 700,
            color: "var(--color-ink)",
            textAlign: "center",
            letterSpacing: "-0.02em",
            marginBottom: 8,
          }}
        >
          {title}
        </h2>
        <p
          className="font-sans"
          style={{
            margin: 0,
            fontSize: 13.5,
            color: "var(--color-mute)",
            textAlign: "center",
            letterSpacing: "-0.005em",
            lineHeight: 1.6,
            marginBottom: 24,
          }}
        >
          {sub}
        </p>

        {/* 토큰 현황 테이블 */}
        <div
          style={{
            background: "rgba(0, 0, 0, 0.04)",
            border: "1px solid var(--color-line)",
            borderRadius: 14,
            padding: "16px 22px",
            marginBottom: 20,
          }}
        >
          <Row label="BALANCE" value={`${balance} 토큰`} />
          <RowDivider />
          <Row label="REQUIRED" value={`${required} 토큰`} />
          <RowDivider />
          <Row label="SHORTAGE" value={`−${shortage} 토큰`} highlight />
        </div>

        {/* shortage-bar */}
        <div
          style={{
            background: "rgba(163, 45, 45, 0.06)",
            border: "1px solid rgba(163, 45, 45, 0.15)",
            borderRadius: 10,
            padding: "13px 16px",
            marginBottom: 22,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <span
            aria-hidden
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--color-danger)",
              flexShrink: 0,
            }}
          />
          <span
            className="font-sans"
            style={{
              fontSize: 13,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
          >
            최소 {shortage} 토큰을 충전하면 바로 이용할 수 있어요.
          </span>
        </div>

        {/* CTA 버튼 2개 */}
        <button
          type="button"
          onClick={onCharge}
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
            marginBottom: 10,
          }}
        >
          토큰 충전하기 →
        </button>
        <button
          type="button"
          onClick={onClose}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: "100%",
            padding: "15px 24px",
            background: "transparent",
            color: "var(--color-mute)",
            border: "1.5px solid var(--color-line)",
            borderRadius: 100,
            fontSize: 14,
            fontWeight: 500,
            letterSpacing: "-0.01em",
            cursor: "pointer",
            transition: "all 0.2s ease",
          }}
        >
          취소
        </button>
      </div>
    </div>
  );
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "8px 0",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--color-mute)",
        }}
      >
        {label}
      </span>
      <span
        className="font-serif tabular-nums"
        style={{
          fontSize: 16,
          fontWeight: 500,
          color: highlight ? "var(--color-danger)" : "var(--color-ink)",
          letterSpacing: "-0.015em",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function RowDivider() {
  return (
    <div
      aria-hidden
      style={{
        height: 1,
        background: "var(--color-line)",
        margin: "0",
      }}
    />
  );
}
