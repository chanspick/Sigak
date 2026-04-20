// SIGAK MVP v1.2 — /auth/login
// 미니멀 로그인 랜딩: 대형 SIGAK 워드마크 + 한 줄 카피 + Kakao 공식 버튼 + 약관 링크.
//
// 흐름:
//   1. "카카오로 시작하기" 클릭 → GET /api/v1/auth/kakao/login?redirect_uri=...
//   2. 응답의 auth_url(카카오 OAuth 페이지)로 이동
//   3. 유저 동의 → Kakao가 redirect_uri로 code 반환 → /auth/kakao/callback
//
// 이미 로그인된 유저는 useEffect로 즉시 / 로 redirect (유저가 뒤로 가기로 로그인 페이지 재방문 방지).
"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getToken } from "@/lib/auth";
import { getKakaoRedirectUri } from "@/lib/kakao";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Next.js 16은 useSearchParams()를 쓰는 컴포넌트가 prerender 시점에
// <Suspense>로 감싸져야 한다. LoginContent(실제 UI) + 기본 export(Suspense 래퍼) 분리.
function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 이미 로그인된 상태면 홈으로
  useEffect(() => {
    if (getToken()) {
      router.replace("/");
    }
  }, [router]);

  // 로그인 후 복귀할 페이지를 sessionStorage에 보존 (콜백이 소비)
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
      if (!res.ok) {
        throw new Error(`서버 응답 오류 (${res.status})`);
      }
      const data = (await res.json()) as { auth_url?: string };
      if (!data.auth_url) throw new Error("카카오 인증 URL을 받지 못했습니다");
      window.location.href = data.auth_url;
    } catch (e) {
      setBusy(false);
      setError(e instanceof Error ? e.message : "카카오 로그인 시작에 실패했습니다");
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      {/* 상단 여백 */}
      <div className="flex-1" />

      {/* Hero */}
      <div className="px-6">
        <div
          className="font-display font-medium text-ink"
          style={{
            fontSize: 28,
            letterSpacing: "0.32em",
            paddingLeft: "0.32em",
            lineHeight: 1,
            textAlign: "center",
          }}
        >
          SIGAK
        </div>
        <p
          className="mt-6 text-center font-sans text-ink"
          style={{ fontSize: 15, lineHeight: 1.6, letterSpacing: "-0.005em" }}
        >
          이 중에서는,
          <br />
          이 한{" "}
          <span
            className="font-serif"
            style={{ fontStyle: "italic", fontWeight: 400 }}
          >
            장
          </span>
          .
        </p>
      </div>

      {/* 가운데 여백 */}
      <div className="flex-1" />

      {/* CTA */}
      <div className="px-5 pb-10">
        {error && (
          <p
            className="mb-3 text-center"
            style={{
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
            role="alert"
          >
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={startKakaoLogin}
          disabled={busy}
          aria-label="카카오로 시작하기"
          className="flex w-full items-center justify-center gap-2 font-sans font-medium transition-opacity"
          style={{
            height: 54,
            background: "#FEE500",
            color: "rgba(0, 0, 0, 0.85)",
            border: "none",
            borderRadius: 12,
            fontSize: 15,
            letterSpacing: "-0.005em",
            cursor: busy ? "default" : "pointer",
            opacity: busy ? 0.6 : 1,
          }}
        >
          {/* Kakao 공식 말풍선 아이콘 */}
          <svg width="18" height="16" viewBox="0 0 18 16" aria-hidden>
            <path
              d="M9 0C4.029 0 0 3.14 0 7.015c0 2.496 1.66 4.69 4.162 5.943-.183.667-.664 2.423-.76 2.8-.12.467.172.46.36.335.148-.098 2.358-1.6 3.311-2.247.625.09 1.27.137 1.927.137 4.971 0 9-3.14 9-7.015C18 3.14 13.971 0 9 0Z"
              fill="currentColor"
            />
          </svg>
          <span>{busy ? "이동 중..." : "카카오로 시작하기"}</span>
        </button>

        {/* 약관 fine print */}
        <p
          className="mt-5 text-center font-sans text-mute"
          style={{ fontSize: 11, lineHeight: 1.7, letterSpacing: "-0.005em" }}
        >
          계속 진행하면{" "}
          <Link href="/terms" className="underline underline-offset-2">
            이용약관
          </Link>
          {" · "}
          <Link href="/terms" className="underline underline-offset-2">
            개인정보처리방침
          </Link>
          에
          <br />
          동의하는 것으로 간주됩니다.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-paper" />}>
      <LoginContent />
    </Suspense>
  );
}
