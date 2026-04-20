// SIGAK MVP v1.2 (Rebrand) — /auth/login
//
// 서브 페이지지만 브랜딩은 동일. TopBar + 짧은 카피 + Kakao 버튼.
// Kakao 규정상 노란 공식 색상은 유지 — 브랜드 일관성보다 규정 우선.
"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getToken } from "@/lib/auth";
import { getKakaoRedirectUri } from "@/lib/kakao";
import { TopBar } from "@/components/ui/sigak";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (getToken()) {
      router.replace("/");
    }
  }, [router]);

  useEffect(() => {
    const next = searchParams.get("next");
    if (next && next.startsWith("/")) {
      sessionStorage.setItem("sigak_redirect", next);
    }
  }, [searchParams]);

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
      setError(
        e instanceof Error ? e.message : "카카오 로그인 시작에 실패했습니다",
      );
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

      <section style={{ padding: "72px 28px 0" }}>
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
          시작하기.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 16,
            fontSize: 13,
            opacity: 0.5,
            lineHeight: 1.6,
            color: "var(--color-ink)",
          }}
        >
          카카오 계정으로 30초.
        </p>
      </section>

      <div style={{ flex: 1 }} />

      {error && (
        <p
          className="font-sans"
          role="alert"
          style={{
            padding: "0 28px",
            fontSize: 12,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
            textAlign: "center",
            marginBottom: 12,
          }}
        >
          {error}
        </p>
      )}

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

export default function LoginPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", background: "var(--color-paper)" }} />}>
      <LoginContent />
    </Suspense>
  );
}
