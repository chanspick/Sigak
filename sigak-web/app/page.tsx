// SIGAK MVP v1.2 — / (홈 = 마케터 프로필 디자인 / 비로그인 랜딩)
//
// IA (2026-04-26 정합):
//   - 로그인 + 가드 통과 → 마케터 프로필 디자인 (3탭 + menu)
//   - 비로그인 → 마케터 랜딩 (Hero + ChatDemo + NumList + Voices + CTA)
//   - /profile (별도) = 마케터 설정 디자인 (계정 / 약관 / 로그아웃)
"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { getCurrentUser, getToken } from "@/lib/auth";
import { getKakaoRedirectUri } from "@/lib/kakao";
import { TopBar } from "@/components/ui/sigak";
import { VerdictGrid } from "@/components/sigak/verdict-grid";
import { AspirationGrid } from "@/components/sigak/aspiration-grid";
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
//  로그인 + 가드 통과 시 홈 (= 마케터 프로필 디자인)
//
//  구조: HomeTopNav (sigak + 토큰 pill) → me (아바타+이름+이메일)
//        → 3탭 (피드/시각/변화) → menu (01/02) → SiteFooter
//
//  ACCOUNT 영역 (약관 / 로그아웃 / 계정 탈퇴) 은 /profile (설정) 로 분리.
// ─────────────────────────────────────────────

type HomeTab = "feed" | "sigak" | "change";

function LoggedInFeed() {
  const router = useRouter();
  const { status } = useOnboardingGuard();
  const { balance } = useTokenBalance();

  const [tab, setTab] = useState<HomeTab>("feed");
  const [profile, setProfile] = useState<{
    name: string;
    email: string;
    profileImage: string;
  } | null>(null);

  useEffect(() => {
    const u = getCurrentUser();
    if (u) {
      setProfile({
        name: u.name || "",
        email: u.email || "",
        profileImage: u.profileImage || "",
      });
    }
  }, []);

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
      {/* HomeTopNav — sigak 중앙 + 토큰 pill 우측 + /profile 진입 좌측 */}
      <header
        style={{
          padding: "28px 24px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid var(--color-line)",
          maxWidth: 480,
          margin: "0 auto",
        }}
      >
        <Link
          href="/profile"
          aria-label="설정"
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            color: "var(--color-ink)",
            opacity: 0.55,
            textDecoration: "none",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </Link>
        <div
          className="font-serif"
          style={{
            fontSize: 15,
            fontWeight: 500,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
          }}
        >
          sigak
        </div>
        <div style={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
          <button
            type="button"
            onClick={() => router.push("/tokens/purchase")}
            aria-label="토큰 충전"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: "var(--color-ink)",
              color: "var(--color-paper)",
              borderRadius: 100,
              padding: "5px 12px",
              border: "none",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 500,
              letterSpacing: "0.04em",
              cursor: "pointer",
            }}
          >
            <span
              aria-hidden
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "var(--color-danger)",
              }}
            />
            <span className="tabular-nums">{balance == null ? "—" : balance.toLocaleString()}</span>
          </button>
        </div>
      </header>

      {/* PROFILE ME */}
      <section style={{ padding: "32px 24px 28px", textAlign: "center", maxWidth: 480, margin: "0 auto" }}>
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            margin: "0 auto 16px",
            overflow: "hidden",
            background: profile?.profileImage
              ? "transparent"
              : "linear-gradient(135deg, #e8d9c8, #b8a58a)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
          }}
        >
          {profile?.profileImage && (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={profile.profileImage}
              alt=""
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
            />
          )}
        </div>
        <div
          className="font-serif"
          style={{
            fontSize: 22,
            fontWeight: 500,
            letterSpacing: "-0.018em",
            color: "var(--color-ink)",
            marginBottom: 6,
          }}
        >
          {profile?.name || "익명"}
        </div>
        {profile?.email && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--color-mute)",
              letterSpacing: "0.02em",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              padding: "0 24px",
            }}
          >
            {profile.email}
          </div>
        )}
      </section>

      {/* TABS */}
      <nav
        style={{
          display: "flex",
          justifyContent: "center",
          gap: 32,
          padding: "0 24px",
          borderBottom: "1px solid var(--color-line)",
          maxWidth: 480,
          margin: "0 auto",
        }}
      >
        {[
          { key: "feed", label: "피드" },
          { key: "sigak", label: "시각" },
          { key: "change", label: "변화" },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key as HomeTab)}
            className="font-serif"
            style={{
              padding: "16px 0",
              fontSize: 14.5,
              fontWeight: 500,
              letterSpacing: "-0.01em",
              color: tab === t.key ? "var(--color-ink)" : "var(--color-mute)",
              background: "transparent",
              border: "none",
              borderBottom:
                tab === t.key
                  ? "1.5px solid var(--color-danger)"
                  : "1.5px solid transparent",
              marginBottom: -1,
              cursor: "pointer",
              userSelect: "none",
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* TAB CONTENT */}
      {tab === "feed" && (
        <section style={{ padding: "20px 0 0" }}>
          <VerdictGrid />
          {/* 추구미 분석 이력 — VerdictGrid 와 동일 3-col 패턴, 자체 SectionHeader 내장 */}
          <AspirationGrid />
        </section>
      )}
      {tab === "sigak" && <PiEntryCard />}
      {tab === "change" && <SoonCard emoji="🌱" text="coming soon.." />}

      {/* MENU — 00 sia 대화 / 01 피드 분석 (verdict) / 02 추구미 살펴보기 */}
      <section style={{ padding: "44px 24px 0", maxWidth: 480, margin: "0 auto" }}>
        <div
          style={{
            paddingBottom: 16,
            borderBottom: "1px solid var(--color-line)",
            marginBottom: 4,
          }}
        >
          <div
            className="font-serif"
            style={{
              fontSize: 20,
              fontWeight: 500,
              letterSpacing: "-0.018em",
              color: "var(--color-ink)",
            }}
          >
            menu
          </div>
        </div>
        <MenuStep
          num="00"
          title="sia와 대화하기"
          sub={"나보다 내 추구미를 더 잘아는 sia와 다시 대화하고\n내 추구미를 정확하게 짚어요."}
          href="/sia"
        />
        <MenuStep
          num="01"
          title="피드 분석하기"
          sub={"올린 사진 중에 가장 잘 맞는 한 장을\n시각이 골라드려요"}
          href="/verdict/new"
        />
        <MenuStep
          num="02"
          title="추구미 살펴보기"
          sub={"추구미에 부합하는 인스타 계정 및 핀터레스트를\n알려주시면 유사도와 개선점을 알려드려요"}
          href="/aspiration"
        />
        <MenuStep
          num="03"
          title="시각 비밀 레포트"
          sub="내 현재 위치와 액션플랜 알아보기"
          href="/photo-upload"
        />
      </section>

      <div style={{ height: 60 }} />
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  MenuStep — 마케터 nextstep 스타일 (홈 + /profile 공유 가능)
// ─────────────────────────────────────────────

function MenuStep({
  num,
  title,
  sub,
  href,
}: {
  num: string;
  title: string;
  sub: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "grid",
        gridTemplateColumns: "44px 1fr",
        gap: 14,
        padding: "22px 0",
        borderBottom: "1px solid var(--color-line)",
        alignItems: "flex-start",
        textDecoration: "none",
        color: "var(--color-ink)",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          fontWeight: 500,
          color: "var(--color-danger)",
          letterSpacing: "0.06em",
          paddingTop: 2,
        }}
      >
        {num}
      </div>
      <div style={{ minWidth: 0 }}>
        <div
          className="font-serif"
          style={{
            fontSize: 15,
            fontWeight: 500,
            color: "var(--color-ink)",
            letterSpacing: "-0.013em",
            marginBottom: 5,
          }}
        >
          {title}
        </div>
        <div
          className="font-sans"
          style={{
            fontSize: 12.5,
            color: "var(--color-mute)",
            lineHeight: 1.55,
            letterSpacing: "-0.005em",
            wordBreak: "keep-all",
            whiteSpace: "pre-line",
          }}
        >
          {sub}
        </div>
      </div>
    </Link>
  );
}

// ─────────────────────────────────────────────
//  PiEntryCard — 시각 탭. PI ("시각이 본 당신") 진입 카드.
//  PI Revival v5 부활 후 BETA 5/15 까지 무료. 클릭 → /photo-upload.
// ─────────────────────────────────────────────

function PiEntryCard() {
  return (
    <section style={{ padding: "32px 24px 0", maxWidth: 480, margin: "0 auto" }}>
      <div
        style={{
          background: "rgba(0, 0, 0, 0.04)",
          borderRadius: 14,
          padding: "44px 28px",
          textAlign: "center",
        }}
      >
        {/* SIGAK 로고 */}
        <svg
          width="44"
          height="44"
          viewBox="0 0 40 40"
          xmlns="http://www.w3.org/2000/svg"
          style={{ marginBottom: 18 }}
          aria-hidden
        >
          <rect width="40" height="40" rx="7" fill="#1a1a1a" />
          <g stroke="#ffffff" strokeWidth="1.5" fill="none" strokeLinecap="round">
            <line x1="20" y1="6" x2="20" y2="13" />
            <path d="M 6 19.5 Q 20 11.5 34 19.5 Q 20 27.5 6 19.5 Z" />
            <circle cx="20" cy="19.5" r="2.6" />
          </g>
          <path
            d="M 20 22.5 C 18.4 25, 17.4 28, 17.4 30 C 17.4 31.9, 18.6 32.8, 20 32.8 C 21.4 32.8, 22.6 31.9, 22.6 30 C 22.6 28, 21.6 25, 20 22.5 Z"
            fill="#ffffff"
          />
        </svg>

        <h3
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 20,
            fontWeight: 500,
            color: "var(--color-ink)",
            letterSpacing: "-0.018em",
            marginBottom: 10,
          }}
        >
          시각 비밀 레포트
        </h3>
        <p
          className="font-sans"
          style={{
            margin: "0 0 26px",
            fontSize: 13.5,
            color: "var(--color-mute)",
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
            wordBreak: "keep-all",
          }}
        >
          내 현재 위치와 다음 액션플랜을
          <br />
          시각이 직접 분석해드려요.
        </p>

        <Link
          href="/photo-upload"
          className="font-sans"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            width: "100%",
            maxWidth: 280,
            padding: "15px 24px",
            background: "var(--color-ink)",
            color: "var(--color-paper)",
            border: "none",
            borderRadius: 100,
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            textDecoration: "none",
          }}
        >
          분석 시작하기 →
        </Link>

        <div
          style={{
            marginTop: 14,
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--color-mute)",
            letterSpacing: "0.08em",
          }}
        >
          BETA 기간 무료
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  SoonCard — 변화 탭 placeholder (Monthly v1.1+ 자리)
// ─────────────────────────────────────────────

function SoonCard({ emoji, text, sub }: { emoji: string; text: string; sub?: string }) {
  return (
    <section style={{ padding: "32px 24px 0", maxWidth: 480, margin: "0 auto" }}>
      <div
        style={{
          background: "rgba(0, 0, 0, 0.04)",
          borderRadius: 14,
          padding: "48px 28px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 14 }}>{emoji}</div>
        <div
          className="font-sans"
          style={{
            fontSize: 16,
            color: "var(--color-ink)",
            opacity: 0.75,
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
            marginBottom: sub ? 8 : 0,
          }}
        >
          {text}
        </div>
        {sub && (
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              letterSpacing: "0.18em",
              color: "var(--color-mute)",
              textTransform: "uppercase",
            }}
          >
            {sub}
          </div>
        )}
      </div>
    </section>
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

      {/* CHAT DEMO (무한반복) */}
      <section style={{ padding: "28px 24px 0" }}>
        <ChatDemo />
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

      {/* VOICES (stats + REVIEWS carousel) */}
      <VoicesSection />

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

// ─────────────────────────────────────────────
//  ChatDemo — 마케터 랜딩의 12 버블 sequential 등장 + 페이드아웃 → 무한반복.
//  타이밍은 redesign/랜딩_1815.html JS 그대로 (~10.5s 사이클).
// ─────────────────────────────────────────────

const CHAT_DEMO_MESSAGES: Array<{ side: "ai" | "user"; text: string; delay: number }> = [
  { side: "ai",   delay:  300, text: "@sigak_official님 피드 다 훑어봤어요\n몇 가지 짚어드려도 될까요?" },
  { side: "ai",   delay: 1000, text: "셀카가 거의 다 오른쪽에서 살짝 위 각도던데\n왼쪽 광대가 좀 더 도드라지는 편이세요?" },
  { side: "user", delay: 1650, text: "헐 맞아요 그게 컴플렉스예요" },
  { side: "ai",   delay: 2300, text: "그래서 그 각도를 본능적으로 고르신 거예요\n오른쪽 턱선이 더 살아서 광대가 덜 보이거든요" },
  { side: "ai",   delay: 2950, text: "근데 본인 장점이 콧대랑 눈매라\n그 각도가 두 개 다 잘 살리고 있어요" },
  { side: "user", delay: 3700, text: "아 그래서 그쪽이 나은 느낌이었구나\n그럼 정면 사진은 어떻게 찍어야 돼요?" },
  { side: "ai",   delay: 4300, text: "정면 찍을 땐 카메라를 살짝 더 위로 올리세요" },
  { side: "ai",   delay: 4850, text: "앞머리로 광대 끝부분만 살짝 가려주면\n콧대는 더 길어 보이고 광대는 안 도드라져요" },
  { side: "user", delay: 5450, text: "오 그건 진짜 몰랐네" },
  { side: "ai",   delay: 6050, text: "옷 색도 그래요 베이지 그레이 카키 위주던데\n혹시 흰옷 입으면 얼굴 부어 보이세요?" },
  { side: "user", delay: 6650, text: "맞아요 그래서 잘 안 입어요" },
  { side: "ai",   delay: 7300, text: "본인 쿨톤이라 새하얀 흰색은 얼굴이 떠요\n근데 아이보리나 오프화이트는 잘 받으실 거예요" },
];
const CHAT_DEMO_PAUSE = 2500;
const CHAT_DEMO_FADE = 400;

function ChatDemo() {
  const [visibleCount, setVisibleCount] = useState(0);
  const [fadingOut, setFadingOut] = useState(false);
  const [cycleKey, setCycleKey] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    setVisibleCount(0);
    setFadingOut(false);

    CHAT_DEMO_MESSAGES.forEach((msg, i) => {
      timers.push(setTimeout(() => setVisibleCount(i + 1), msg.delay));
    });

    const lastDelay = CHAT_DEMO_MESSAGES[CHAT_DEMO_MESSAGES.length - 1].delay;
    timers.push(
      setTimeout(() => setFadingOut(true), lastDelay + CHAT_DEMO_PAUSE),
    );
    timers.push(
      setTimeout(
        () => setCycleKey((k) => k + 1),
        lastDelay + CHAT_DEMO_PAUSE + CHAT_DEMO_FADE + 200,
      ),
    );

    return () => {
      timers.forEach((t) => clearTimeout(t));
    };
  }, [cycleKey]);

  // 새 메시지 등장 시 자동 스크롤 (마지막이 보이도록)
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [visibleCount]);

  return (
    <div
      style={{
        position: "relative",
        height: 320,
        background: "rgba(0, 0, 0, 0.04)",
        borderRadius: 14,
        padding: "20px 18px",
        overflow: "hidden",
      }}
    >
      <div
        ref={scrollRef}
        style={{
          height: "100%",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          gap: 7,
          opacity: fadingOut ? 0 : 1,
          transition: `opacity ${CHAT_DEMO_FADE}ms ease`,
        }}
      >
        {CHAT_DEMO_MESSAGES.map((msg, i) => {
          const isAi = msg.side === "ai";
          const visible = i < visibleCount;
          return (
            <div
              key={`${cycleKey}-${i}`}
              style={{
                alignSelf: isAi ? "flex-start" : "flex-end",
                maxWidth: isAi ? "82%" : "78%",
                background: isAi ? "var(--color-bubble-ai)" : "var(--color-bubble-user)",
                color: isAi ? "var(--color-ink)" : "var(--color-paper)",
                borderRadius: isAi ? "20px 20px 20px 5px" : "20px 20px 5px 20px",
                padding: "9px 13px",
                fontSize: 13,
                lineHeight: 1.55,
                whiteSpace: "pre-line",
                flexShrink: 0,
                opacity: visible ? 1 : 0,
                transform: visible ? "scale(1)" : "scale(0.87)",
                transition:
                  "opacity 280ms cubic-bezier(0.34, 1.45, 0.64, 1), transform 280ms cubic-bezier(0.34, 1.45, 0.64, 1)",
              }}
            >
              {msg.text}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  VoicesSection — EARLY READERS stats + REVIEWS carousel (6초 회전)
// ─────────────────────────────────────────────

const REVIEWS: Array<{ text: string; meta: string }> = [
  {
    text: "솔직히 기대 안 했는데 소름. 저번 주에 제주도 사진 세 장 중에 고민하다가 결국 일주일 넘게 못 올렸는데, 두 번째가 그동안 피드 톤이랑 비교했을 때 가장 덜 튄다고 함. 친구한테 물어보면 다 이쁘다고만 하는데 얘는 이유를 말해줘서 납득이 됐음.",
    meta: "24 · 여성",
  },
  {
    text: "무슨 좌표로 내 얼굴 설명해주는 거 처음 봄. 퍼컬 같은 건 유형 찍어놓고 끝인데 이건 뭐 엄청 자세하게 얼굴 포인트 하나하나 수치로 설명하니까 너무 유용함.",
    meta: "29 · 여성",
  },
  {
    text: "재미로 들어가봤는데 무료 토큰으로 제 피드 검사 받아봤는데 이 사진은 네가 추구하는 톤이랑 어디가 어떻게 어긋남 이런 식으로 말해줘요.",
    meta: "22 · 여성",
  },
  {
    text: "제 얼굴형 인정하기 싫은데 다 맞는 말이라 할 말이 없네요..",
    meta: "23 · 남성",
  },
  {
    text: "피드 뭐 올릴지 여사친들한테 물어봐도 친구들마다 말이 달라서 결정장애 왔는데 이제 여기서 그냥 골라달라고 해요.",
    meta: "30 · 남성",
  },
];
const REVIEW_INTERVAL = 6000;
const REVIEW_FADE = 400;

function VoicesSection() {
  const [idx, setIdx] = useState(0);
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const tick = setInterval(() => {
      setVisible(false);
      const t = setTimeout(() => {
        setIdx((i) => (i + 1) % REVIEWS.length);
        setVisible(true);
      }, REVIEW_FADE);
      return () => clearTimeout(t);
    }, REVIEW_INTERVAL);
    return () => clearInterval(tick);
  }, []);

  return (
    <section
      style={{
        padding: "80px 24px 64px",
        marginTop: 60,
        borderTop: "1px solid var(--color-line)",
        background: "rgba(0, 0, 0, 0.025)",
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.3em",
          color: "var(--color-mute)",
          marginBottom: 26,
        }}
      >
        EARLY READERS
      </div>

      <div
        style={{
          maxWidth: 400,
          margin: "0 auto 44px",
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: "20px 16px",
        }}
      >
        <StatItem num="209" label="누적 피드 분석 수" />
        <StatItem num="61" label="누적 시각 리포트 분석 수" />
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          maxWidth: 300,
          margin: "0 auto 32px",
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          letterSpacing: "0.22em",
          color: "var(--color-mute)",
        }}
      >
        <div style={{ flex: 1, height: 1, background: "var(--color-line-strong)" }} />
        REVIEWS
        <div style={{ flex: 1, height: 1, background: "var(--color-line-strong)" }} />
      </div>

      <p
        className="font-serif"
        style={{
          fontWeight: 300,
          fontSize: 16.5,
          lineHeight: 1.82,
          color: "var(--color-ink)",
          letterSpacing: "-0.012em",
          maxWidth: 400,
          margin: "0 auto",
          minHeight: 200,
          padding: "0 8px",
          opacity: visible ? 0.85 : 0,
          transition: `opacity ${REVIEW_FADE}ms ease`,
          wordBreak: "keep-all",
        }}
      >
        {REVIEWS[idx].text}
      </p>

      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          letterSpacing: "0.16em",
          color: "var(--color-mute)",
          marginTop: 20,
          opacity: visible ? 1 : 0,
          transition: `opacity ${REVIEW_FADE}ms ease`,
        }}
      >
        {REVIEWS[idx].meta}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginTop: 32,
        }}
      >
        {REVIEWS.map((_, i) => (
          <div
            key={i}
            style={{
              width: 20,
              height: 1,
              margin: "0 3px",
              background: i === idx ? "var(--color-danger)" : "var(--color-line-strong)",
              transition: "background 0.3s ease",
            }}
          />
        ))}
      </div>
    </section>
  );
}

function StatItem({ num, label }: { num: string; label: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div
        className="font-serif"
        style={{
          fontWeight: 500,
          fontSize: 28,
          letterSpacing: "-0.018em",
          color: "var(--color-danger)",
          lineHeight: 1,
          marginBottom: 6,
        }}
      >
        {num}
        <sup style={{ fontSize: 16, fontWeight: 500, marginLeft: 1 }}>+</sup>
      </div>
      <div
        style={{
          fontSize: 11.5,
          color: "var(--color-mute)",
          lineHeight: 1.4,
          letterSpacing: "-0.005em",
        }}
      >
        {label}
      </div>
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
