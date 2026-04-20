// SIGAK MVP v1.2 (D-6) — / (피드)
//
// 로그인 + 가드 통과 유저 → FeedTopBar + VerdictGrid
// 비로그인 → LoggedOutLanding (카카오 CTA)
//
// 업로드는 더 이상 여기 없음 → /verdict/new 로 이동 (FeedTopBar의 + 아이콘).
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { getToken } from "@/lib/auth";
import { FeedTopBar, TopBar } from "@/components/ui/sigak";
import { VerdictGrid } from "@/components/sigak/verdict-grid";

type RootPhase = "loading" | "logged_out" | "logged_in";

export default function RootPage() {
  const [phase, setPhase] = useState<RootPhase>("loading");

  useEffect(() => {
    setPhase(getToken() ? "logged_in" : "logged_out");
  }, []);

  if (phase === "loading") {
    return <div style={{ minHeight: "100vh", background: "var(--color-paper)" }} aria-busy />;
  }

  if (phase === "logged_out") {
    return <LoggedOutLanding />;
  }

  return <LoggedInFeed />;
}

// ─────────────────────────────────────────────
//  로그인 + 가드 통과 시 피드
// ─────────────────────────────────────────────

function LoggedInFeed() {
  const { status } = useOnboardingGuard();
  if (status !== "ready") {
    return <div style={{ minHeight: "100vh", background: "var(--color-paper)" }} aria-busy />;
  }
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <FeedTopBar />
      <VerdictGrid />
    </div>
  );
}

// ─────────────────────────────────────────────
//  비로그인 랜딩
// ─────────────────────────────────────────────

function LoggedOutLanding() {
  const router = useRouter();

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
      <TopBar />

      <section style={{ padding: "72px 28px 0" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 40,
            fontWeight: 400,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          당신을<br />읽겠습니다.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 20,
            fontSize: 13,
            opacity: 0.5,
            lineHeight: 1.6,
            color: "var(--color-ink)",
          }}
        >
          사진 세 장. AI가 오늘의 한 장을.
        </p>
      </section>

      <div style={{ flex: 1 }} />

      <Rule />

      <section style={{ padding: "28px 28px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <Label>읽기</Label>
          <LabelRight>03</LabelRight>
        </div>
        <ol style={{ margin: "16px 0 0", padding: 0, listStyle: "none" }}>
          {[
            "사진 세 장부터.",
            "GOLD 한 장 · reading 무료.",
            "나머지 · 50 토큰으로 해제.",
          ].map((t, i) => (
            <li
              key={t}
              style={{
                display: "flex",
                alignItems: "baseline",
                gap: 14,
                padding: "12px 0",
                borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
              }}
            >
              <span
                className="font-serif tabular-nums"
                style={{
                  fontSize: 14,
                  fontWeight: 400,
                  opacity: 0.4,
                  color: "var(--color-ink)",
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                className="font-sans"
                style={{
                  fontSize: 14,
                  fontWeight: 400,
                  letterSpacing: "-0.005em",
                  color: "var(--color-ink)",
                }}
              >
                {t}
              </span>
            </li>
          ))}
        </ol>
      </section>

      <div style={{ padding: "28px 28px 20px" }}>
        <button
          type="button"
          onClick={() => router.push("/auth/login")}
          aria-label="카카오로 시작하기"
          style={{
            width: "100%",
            height: 56,
            background: "#FEE500",
            color: "rgba(0, 0, 0, 0.85)",
            border: "none",
            borderRadius: 0,
            fontFamily: "var(--font-sans)",
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.5px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
          }}
        >
          <svg width="18" height="16" viewBox="0 0 18 16" aria-hidden>
            <path
              d="M9 0C4.029 0 0 3.14 0 7.015c0 2.496 1.66 4.69 4.162 5.943-.183.667-.664 2.423-.76 2.8-.12.467.172.46.36.335.148-.098 2.358-1.6 3.311-2.247.625.09 1.27.137 1.927.137 4.971 0 9-3.14 9-7.015C18 3.14 13.971 0 9 0Z"
              fill="currentColor"
            />
          </svg>
          <span>카카오로 시작하기</span>
        </button>
      </div>

      <div style={{ padding: "0 28px 32px" }}>
        <p
          className="font-sans"
          style={{
            fontSize: 11,
            lineHeight: 1.7,
            opacity: 0.4,
            textAlign: "center",
            margin: 0,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          계속 진행하면{" "}
          <Link href="/terms" style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>
            이용약관
          </Link>
          {" · "}
          <Link href="/terms#privacy" style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>
            개인정보처리방침
          </Link>
          에 동의하는 것으로 간주됩니다.
        </p>
      </div>
    </div>
  );
}

function Rule() {
  return (
    <div
      style={{
        height: 1,
        background: "var(--color-ink)",
        margin: "0 28px",
        opacity: 0.15,
      }}
    />
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-sans uppercase"
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "1.5px",
        opacity: 0.4,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}

function LabelRight({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-serif tabular-nums"
      style={{
        fontSize: 14,
        fontWeight: 400,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}
