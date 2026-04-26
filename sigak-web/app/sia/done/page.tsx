/**
 * /sia/done — Sia 세션 종료 직후 로딩 슬라이드 (15초) → 완료 축하 페이지.
 *
 * query: ?report={report_id}  필수. 없으면 홈으로.
 *   Phase H5 완료 전까지 report_id = sessionId fallback.
 *
 * PI Revival v5 (2026-04-26): CTA → `/photo-upload` 새 page.
 *   /sia (대화) → /sia/done (LoadingSlides 15s + CTA)
 *   → /photo-upload (사진 multipart picker)
 *   → /api/v1/submit + /api/v1/analyze (옛 SIGAK_V3 시스템)
 *   → /report/{report_id}/full
 */

"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { LoadingSlides } from "@/components/sia/LoadingSlides";

function DoneContent() {
  const router = useRouter();
  const params = useSearchParams();
  const reportId = params.get("report");
  const [slidesDone, setSlidesDone] = useState(false);

  useEffect(() => {
    if (!reportId) {
      router.replace("/");
    }
  }, [reportId, router]);

  if (!reportId) {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-hidden
      />
    );
  }

  if (!slidesDone) {
    return <LoadingSlides onComplete={() => setSlidesDone(true)} />;
  }

  return <CompletionScreen reportId={reportId} />;
}

function CompletionScreen({ reportId }: { reportId: string }) {
  // PI Revival v5: LoadingSlides 끝나면 Sia → 옛 SIGAK_V3 PI entry 로 직진.
  // CTA → /photo-upload (multipart picker) → /api/v1/submit + analyze → /report/{id}/full.
  // 마케터 톤 정합 (2026-04-26): Noto Serif 24-26 700 + period accent ember + pill CTA.
  return (
    <main
      className="animate-fade-in"
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        display: "flex",
        flexDirection: "column",
        padding: "60px 24px 40px",
      }}
    >
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          maxWidth: 480,
          margin: "0 auto",
          width: "100%",
        }}
      >
        <span
          className="uppercase"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.14em",
            color: "var(--color-danger)",
            marginBottom: 14,
          }}
        >
          NEXT STEP
        </span>
        <h1
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 26,
            fontWeight: 700,
            lineHeight: 1.42,
            letterSpacing: "-0.022em",
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          대화 고마워요
          <span style={{ color: "var(--color-danger)" }}>.</span>
          <br />
          시각이 본 나, 완성하려면<br />
          정면 사진 한 장이 필요해요
          <span style={{ color: "var(--color-danger)" }}>.</span>
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 14,
            fontSize: 14,
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
            color: "var(--color-mute)",
            wordBreak: "keep-all",
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
          gap: 10,
          maxWidth: 480,
          margin: "0 auto",
          width: "100%",
        }}
      >
        {/* Primary CTA — 마케터 pill (radius 100, ink) */}
        <Link
          href={`/photo-upload?from_session=${encodeURIComponent(reportId)}`}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            width: "100%",
            padding: "17px 24px",
            background: "var(--color-ink)",
            color: "var(--color-paper)",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            textDecoration: "none",
          }}
        >
          분석 시작하기 →
        </Link>

        {/* Secondary 옵션 (다른 흐름) */}
        <CtaLink href="/best-shot" label="Best Shot" subtitle="사진 여러 장에서 한 장" />
        <CtaLink href="/aspiration" label="추구미 살펴보기" subtitle="따라가는 이미지, 실제로 뭐가 다른지" />

        <Link
          href="/"
          className="font-sans"
          style={{
            display: "block",
            height: 44,
            lineHeight: "44px",
            textAlign: "center",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.3px",
            color: "var(--color-mute)",
            textDecoration: "none",
            marginTop: 4,
          }}
        >
          나중에 (홈으로)
        </Link>
      </div>
    </main>
  );
}

interface CtaLinkProps {
  href: string;
  label: string;
  subtitle: string;
}

function CtaLink({ href, label, subtitle }: CtaLinkProps) {
  return (
    <Link
      href={href}
      className="font-sans"
      style={{
        display: "block",
        padding: "16px 18px",
        background: "rgba(0, 0, 0, 0.04)",
        border: "1px solid var(--color-line)",
        borderRadius: 12,
        color: "var(--color-ink)",
        textDecoration: "none",
        transition: "background 180ms ease-out",
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
            className="font-serif"
            style={{
              fontSize: 15,
              fontWeight: 500,
              letterSpacing: "-0.013em",
              color: "var(--color-ink)",
            }}
          >
            {label}
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 12.5,
              lineHeight: 1.55,
              letterSpacing: "-0.005em",
              color: "var(--color-mute)",
            }}
          >
            {subtitle}
          </div>
        </div>
        <span
          aria-hidden
          style={{
            fontSize: 16,
            color: "var(--color-mute-2)",
          }}
        >
          ›
        </span>
      </div>
    </Link>
  );
}

export default function SiaDonePage() {
  return (
    <Suspense
      fallback={
        <div
          style={{ minHeight: "100vh", background: "var(--color-paper)" }}
          aria-hidden
        />
      }
    >
      <DoneContent />
    </Suspense>
  );
}
