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
import { AspirationGrid } from "@/components/sigak/aspiration-grid";
import { FeatureCards } from "@/components/sigak/feature-cards";
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
        <AspirationGrid />
        <FeatureCards />
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
      }}
    >
      <TopBar />

      {/* HERO */}
      <section style={{ padding: "32px 24px 0", textAlign: "center" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 32,
            fontWeight: 700,
            lineHeight: 1.35,
            letterSpacing: "-0.028em",
            margin: 0,
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          나만의 미감 비서,
          <br />
          <span style={{ color: "var(--color-danger)" }}>시각</span>
        </h1>
      </section>

      {/* CHAT PREVIEW (정적) */}
      <section style={{ padding: "28px 24px 0" }}>
        <div
          style={{
            background: "rgba(0, 0, 0, 0.04)",
            borderRadius: 14,
            padding: "20px 18px",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <ChatBubble side="ai">
            @sigak_official님 피드 다 훑어봤어요
            <br />
            몇 가지 짚어드려도 될까요?
          </ChatBubble>
          <ChatBubble side="ai">
            셀카가 거의 다 오른쪽에서 살짝 위 각도던데
            <br />
            왼쪽 광대가 좀 더 도드라지는 편이세요?
          </ChatBubble>
          <ChatBubble side="user">헐 맞아요 그게 컴플렉스예요</ChatBubble>
          <ChatBubble side="ai">
            그래서 그 각도를 본능적으로 고르신 거예요
            <br />
            오른쪽 턱선이 더 살아서 광대가 덜 보이거든요
          </ChatBubble>
        </div>
        <p
          className="font-sans"
          style={{
            marginTop: 16,
            fontSize: 14,
            fontWeight: 700,
            color: "var(--color-ink)",
            letterSpacing: "-0.01em",
            textAlign: "center",
          }}
        >
          인스타 넣고 대화 3분이면 끝!
        </p>
      </section>

      {/* NUMLIST */}
      <section style={{ padding: "60px 24px 0" }}>
        <NumStep num="01" title="대화로 시작해요" desc="sia와 몇 마디만 나누면 취향이 정리돼요." />
        <NumStep num="02" title="인스타를 읽어와요" desc="인스타 아이디만 넣으면 내 추구미 분석 시작!" />
        <NumStep
          num="03"
          title="피드 분석 리포트를 제공해요"
          desc="내 피드가 추구미를 잘 따라가고 있는지, 개선할 점도 제공해요"
        />
      </section>

      {/* FINAL CTA */}
      <section style={{ padding: "60px 24px 24px", textAlign: "center" }}>
        <h2
          className="font-serif"
          style={{
            fontSize: 26,
            fontWeight: 500,
            lineHeight: 1.48,
            letterSpacing: "-0.024em",
            color: "var(--color-ink)",
            margin: "0 0 14px",
          }}
        >
          시각이 본 당신,
          <br />
          <strong style={{ fontWeight: 700 }}>궁금하지 않나요?</strong>
        </h2>
        <p
          className="font-sans"
          style={{
            fontSize: 14,
            lineHeight: 1.75,
            color: "var(--color-mute)",
            margin: "0 0 24px",
          }}
        >
          무료로 지금 시작해요.
          <br />
          3분이면 나를 알 수 있어요.
        </p>

        {error && (
          <p
            className="font-sans"
            role="alert"
            style={{
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              marginBottom: 12,
            }}
          >
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={startKakaoLogin}
          disabled={busy}
          aria-label="카카오 로그인"
          style={{
            width: "100%",
            maxWidth: 320,
            margin: "0 auto",
            padding: "17px 24px",
            background: "#FEE500",
            color: "rgba(0, 0, 0, 0.85)",
            border: "none",
            borderRadius: 100,
            fontFamily: "var(--font-sans)",
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
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
          <span>{busy ? "이동 중..." : "카카오 로그인"}</span>
        </button>

        <p
          className="font-sans"
          style={{
            marginTop: 14,
            fontSize: 11.5,
            color: "var(--color-mute-2)",
            lineHeight: 1.6,
          }}
        >
          <Link href="/terms" style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>
            이용약관
          </Link>
          {" · "}
          <Link href="/terms#privacy" style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>
            개인정보처리방침
          </Link>
          에 동의합니다.
        </p>
      </section>

      <SiteFooter />
    </div>
  );
}

function ChatBubble({ side, children }: { side: "ai" | "user"; children: React.ReactNode }) {
  const isAi = side === "ai";
  return (
    <div
      style={{
        alignSelf: isAi ? "flex-start" : "flex-end",
        maxWidth: isAi ? "82%" : "78%",
        background: isAi ? "var(--color-bubble-ai)" : "var(--color-bubble-user)",
        color: isAi ? "var(--color-ink)" : "var(--color-paper)",
        borderRadius: isAi ? "16px 16px 16px 4px" : "16px 16px 4px 16px",
        padding: "8px 12px",
        fontSize: 13,
        lineHeight: 1.55,
      }}
    >
      {children}
    </div>
  );
}

function NumStep({ num, title, desc }: { num: string; title: string; desc: string }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "44px 1fr",
        gap: 20,
        marginBottom: 32,
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 14,
          fontWeight: 500,
          color: "var(--color-danger)",
          letterSpacing: "0.04em",
          paddingTop: 2,
        }}
      >
        {num}
      </div>
      <div>
        <div
          className="font-serif"
          style={{
            fontSize: 16,
            fontWeight: 500,
            color: "var(--color-ink)",
            letterSpacing: "-0.012em",
            marginBottom: 8,
          }}
        >
          {title}
        </div>
        <div
          className="font-sans"
          style={{
            fontSize: 13.5,
            lineHeight: 1.7,
            color: "var(--color-mute)",
            letterSpacing: "-0.005em",
          }}
        >
          {desc}
        </div>
      </div>
    </div>
  );
}
