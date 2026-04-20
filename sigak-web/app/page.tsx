// SIGAK MVP v1.2 (D-6 revised) — / (피드 or 비로그인 랜딩)
//
// 로그인 + 가드 통과 → FeedTopBar + VerdictGrid
// 비로그인 → 심플 랜딩. /auth/login 경유 없이 직접 Kakao OAuth 트리거.
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { getToken } from "@/lib/auth";
import { getKakaoRedirectUri } from "@/lib/kakao";
import { TopBar } from "@/components/ui/sigak";
import { FeedShell } from "@/components/sigak/feed-shell";
import { VerdictGrid } from "@/components/sigak/verdict-grid";
import { SiteFooter } from "@/components/sigak/site-footer";

type RootPhase = "loading" | "logged_out" | "logged_in";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  const [verdictCount, setVerdictCount] = useState<number | null>(null);

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
      <FeedShell verdictCount={verdictCount}>
        <VerdictGrid onTotalChange={setVerdictCount} />
      </FeedShell>
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  비로그인 랜딩
// ─────────────────────────────────────────────

function LoggedOutLanding() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startKakaoLogin() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const redirectUri = getKakaoRedirectUri();
      const url = `${API_URL}/api/v1/auth/kakao/login?redirect_uri=${encodeURIComponent(redirectUri)}`;
      const res = await fetch(url, {
        headers: { "ngrok-skip-browser-warning": "true" },
      });
      if (!res.ok) throw new Error(`서버 응답 오류 (${res.status})`);
      const data = (await res.json()) as { auth_url?: string };
      if (!data.auth_url) throw new Error("카카오 인증 URL을 받지 못했습니다");
      window.location.href = data.auth_url;
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "카카오 로그인 시작에 실패했습니다");
    }
  }

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

      {/* 헤드라인 — 카피 미니멀 */}
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 28px",
        }}
      >
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
          오늘 한 장.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 20,
            fontSize: 14,
            opacity: 0.55,
            lineHeight: 1.7,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          3~10장 중 가장 나다운 한 장을.
        </p>
      </section>

      {/* 에러 */}
      {error && (
        <p
          className="font-sans"
          role="alert"
          style={{
            padding: "0 28px 8px",
            fontSize: 12,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
            textAlign: "center",
          }}
        >
          {error}
        </p>
      )}

      {/* Kakao CTA */}
      <div style={{ padding: "0 28px 20px" }}>
        <button
          type="button"
          onClick={startKakaoLogin}
          disabled={busy}
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
            cursor: busy ? "default" : "pointer",
            opacity: busy ? 0.6 : 1,
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
          <span>{busy ? "이동 중..." : "카카오로 시작하기"}</span>
        </button>
      </div>

      {/* 약관 fine print */}
      <div style={{ padding: "0 28px 12px" }}>
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

      {/* Toss PG 심사용 — 승인 후 제거 */}
      <div style={{ padding: "0 28px 32px", textAlign: "center" }}>
        <Link
          href="/auth/test-login"
          className="font-sans"
          style={{
            fontSize: 10,
            letterSpacing: "1.5px",
            textTransform: "uppercase",
            opacity: 0.3,
            color: "var(--color-ink)",
            textDecoration: "underline",
            textUnderlineOffset: 3,
          }}
        >
          PG 심사 테스트 로그인
        </Link>
      </div>

      <SiteFooter />
    </div>
  );
}
