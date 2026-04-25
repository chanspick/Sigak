/**
 * PiMaintenance — 시각이 본 당신 임시 잠금 안내 (2026-04-26).
 *
 * 본인 결정: PI v3 product 본질 검증 미완 → 5월 중 재개.
 * 모든 /pi/* 라우트에서 본 컴포넌트 노출.
 */

"use client";

import Link from "next/link";

export function PiMaintenance() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        display: "flex",
        flexDirection: "column",
        padding: "60px 28px 40px",
      }}
    >
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          maxWidth: 420,
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "1.6px",
            opacity: 0.4,
          }}
        >
          PREPARING
        </span>
        <h1
          className="font-serif"
          style={{
            marginTop: 18,
            fontSize: 28,
            fontWeight: 400,
            lineHeight: 1.4,
            letterSpacing: "-0.01em",
          }}
        >
          시각이 본 당신은
          <br />
          곧 돌아옵니다
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 24,
            fontSize: 14,
            lineHeight: 1.75,
            opacity: 0.72,
            letterSpacing: "-0.005em",
          }}
        >
          시각 레포트는 여러분이 Sia와 대화하고 피드를 분석하는 만큼 여러분에
          대해 잘 알아갑니다.
        </p>
        <p
          className="font-sans"
          style={{
            marginTop: 12,
            fontSize: 13,
            lineHeight: 1.75,
            opacity: 0.5,
            letterSpacing: "-0.005em",
          }}
        >
          5월 중 개발 예정이에요.
        </p>
      </section>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <Link
          href="/"
          className="font-sans"
          style={{
            display: "block",
            width: "100%",
            height: 54,
            lineHeight: "54px",
            textAlign: "center",
            background: "var(--color-ink)",
            color: "var(--color-paper)",
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.5px",
            textDecoration: "none",
          }}
        >
          홈으로
        </Link>
      </div>
    </main>
  );
}
