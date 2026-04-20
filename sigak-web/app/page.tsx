// SIGAK MVP v1.2 — / (루트 랜딩)
//
// 로그인 + 온보딩 완료 유저 → HomeScreen (upload zone)
// 비로그인 유저 → minimal 랜딩 (SIGAK 워드마크 + 한 줄 pitch + 카카오 CTA)
//
// useOnboardingGuard는 로그인 유저 경로에서만 호출 (비로그인에서 호출하면
// guard가 즉시 /auth/login으로 redirect시켜 랜딩이 안 보이게 됨).
//
// 가드가 통과시킨(ready) 유저만 HomeScreen 렌더. consent/onboarding 미완은
// 가드가 알아서 /onboarding/welcome 또는 /onboarding/step/{n}으로 redirect.
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { getToken } from "@/lib/auth";
import { HomeScreen } from "@/components/sigak/home-screen";

type RootPhase = "loading" | "logged_out" | "logged_in";

export default function RootPage() {
  const [phase, setPhase] = useState<RootPhase>("loading");

  useEffect(() => {
    setPhase(getToken() ? "logged_in" : "logged_out");
  }, []);

  if (phase === "loading") {
    return <div className="min-h-screen bg-paper" aria-busy />;
  }

  if (phase === "logged_out") {
    return <LoggedOutLanding />;
  }

  return <LoggedInHome />;
}

// ─────────────────────────────────────────────
//  로그인 유저: 가드 통과 후 HomeScreen
// ─────────────────────────────────────────────

function LoggedInHome() {
  const { status } = useOnboardingGuard();
  if (status !== "ready") {
    return <div className="min-h-screen bg-paper" aria-busy />;
  }
  return <HomeScreen />;
}

// ─────────────────────────────────────────────
//  비로그인 랜딩 (minimal)
// ─────────────────────────────────────────────

function LoggedOutLanding() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      {/* Top spacer */}
      <div className="pt-[15vh]" />

      {/* Wordmark + pitch */}
      <div className="px-6 text-center">
        <h1
          className="font-display font-medium text-ink"
          style={{
            fontSize: 34,
            letterSpacing: "0.32em",
            paddingLeft: "0.32em",
            lineHeight: 1,
          }}
        >
          SIGAK
        </h1>
        <p
          className="mt-10 font-sans text-ink"
          style={{ fontSize: 16, lineHeight: 1.6, letterSpacing: "-0.005em" }}
        >
          이 중에서는,
          <br />이 한{" "}
          <span
            className="font-serif"
            style={{ fontStyle: "italic", fontWeight: 400 }}
          >
            장
          </span>
          .
        </p>
        <p
          className="mt-6 font-sans text-mute"
          style={{ fontSize: 13, lineHeight: 1.7, letterSpacing: "-0.005em" }}
        >
          후보 사진을 올리면 AI가 오늘의 한 장을 골라드려요.
        </p>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Proof points */}
      <div className="px-5 pb-8">
        <ul className="mx-auto mb-10 max-w-[320px] space-y-2">
          {[
            "3~10장 업로드, 즉시 판정",
            "GOLD 결과와 짧은 해석은 무료",
            "상세 진단은 50토큰으로 해제",
          ].map((t, i) => (
            <li key={t} className="flex items-center gap-3">
              <span
                className="font-mono tabular-nums text-mute"
                style={{ fontSize: 10, letterSpacing: "0.14em" }}
              >
                /00{i + 1}
              </span>
              <span
                className="font-sans text-ink"
                style={{ fontSize: 13, letterSpacing: "-0.005em" }}
              >
                {t}
              </span>
            </li>
          ))}
        </ul>

        {/* Kakao CTA */}
        <button
          type="button"
          onClick={() => router.push("/auth/login")}
          aria-label="카카오로 시작하기"
          className="flex w-full items-center justify-center gap-2 font-sans font-medium"
          style={{
            height: 54,
            background: "#FEE500",
            color: "rgba(0, 0, 0, 0.85)",
            border: "none",
            borderRadius: 12,
            fontSize: 15,
            letterSpacing: "-0.005em",
            cursor: "pointer",
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

        <p
          className="mt-4 text-center font-sans text-mute"
          style={{ fontSize: 11, lineHeight: 1.7, letterSpacing: "-0.005em" }}
        >
          계속 진행하면{" "}
          <Link href="/terms" className="underline underline-offset-2">
            이용약관
          </Link>
          {" · "}
          <Link href="/terms#privacy" className="underline underline-offset-2">
            개인정보처리방침
          </Link>
          에 동의하는 것으로 간주됩니다.
        </p>
      </div>
    </div>
  );
}
