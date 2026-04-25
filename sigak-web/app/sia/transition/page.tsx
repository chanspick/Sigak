/**
 * /sia/transition — Sia → PI 진입 transition 화면 (Phase I PI-D, 본인 결정 2026-04-25).
 *
 * 흐름:
 *   Sia 종료 → /sia/done (LoadingSlides 15초) → CompletionScreen → ENTER /sia/transition
 *   query: ?report={report_id}  Sia 세션 link carry over (옵션)
 *
 * 설계:
 *   - "정면 사진 한 장이 필요해요" 카피 (PI 풀 분석 = baseline raw 사진 필수)
 *   - [📷 사진 한 장 보여드리기]  → /pi/upload (native picker + 자동 분석)
 *   - [홈 둘러보기]                → /vision (시각 탭 default — PI 미체험 분기)
 *
 * 톤: Sia 친밀체 (~인가봐요? / ~잖아요) — transition 은 아직 PI 전이라 Sia 영역.
 *      PI 본문 진입 후엔 리포트체로 전환.
 */

"use client";

import { Suspense } from "react";
import Link from "next/link";

function TransitionContent() {
  return (
    <main
      className="animate-fade-in"
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
          maxWidth: 380,
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
          }}
        >
          NEXT
        </span>
        <h1
          className="font-serif"
          style={{
            marginTop: 16,
            fontSize: 30,
            fontWeight: 400,
            lineHeight: 1.4,
            letterSpacing: "-0.01em",
          }}
        >
          시각이 본 나,<br />완성하려면
          <br />
          정면 사진 한 장이 필요해요.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 18,
            fontSize: 14,
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
            opacity: 0.6,
          }}
        >
          얼굴이 또렷하게 잡히는 정면 한 컷이면 돼요.
          <br />
          화장은 안 하셔도 분석 가능해요.
        </p>
      </section>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <PrimaryCTA
          href="/pi/upload?next=preview"
          icon="camera"
          label="사진 한 장 보여드리기"
          subtitle="갤러리 또는 카메라"
        />
        <Link
          href="/vision"
          className="font-sans"
          style={{
            display: "block",
            height: 48,
            lineHeight: "48px",
            textAlign: "center",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.3px",
            opacity: 0.55,
            color: "var(--color-ink)",
            textDecoration: "none",
            marginTop: 4,
          }}
        >
          나중에 (홈 둘러보기)
        </Link>
      </div>
    </main>
  );
}

interface PrimaryCTAProps {
  href: string;
  icon: "camera";
  label: string;
  subtitle: string;
}

function PrimaryCTA({ href, label, subtitle }: PrimaryCTAProps) {
  return (
    <Link
      href={href}
      className="font-sans"
      style={{
        display: "block",
        padding: "18px 22px",
        background: "var(--color-ink)",
        color: "var(--color-paper)",
        textDecoration: "none",
        transition: "opacity 180ms ease-out",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 15,
              fontWeight: 600,
              letterSpacing: "-0.005em",
              color: "var(--color-paper)",
            }}
          >
            📷 {label}
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 12,
              lineHeight: 1.5,
              letterSpacing: "-0.005em",
              opacity: 0.7,
              color: "var(--color-paper)",
            }}
          >
            {subtitle}
          </div>
        </div>
        <span
          aria-hidden
          style={{
            fontSize: 18,
            opacity: 0.85,
            color: "var(--color-paper)",
          }}
        >
          →
        </span>
      </div>
    </Link>
  );
}

export default function SiaTransitionPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{ minHeight: "100vh", background: "var(--color-paper)" }}
          aria-hidden
        />
      }
    >
      <TransitionContent />
    </Suspense>
  );
}
