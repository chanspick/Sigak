/**
 * /sia/done — Sia 세션 종료 직후 로딩 슬라이드 (15초) → 완료 축하 페이지.
 *
 * query: ?report={report_id}  필수. 없으면 홈으로.
 *   Phase H5 완료 전까지 report_id = sessionId fallback.
 *
 * 4 기능 런칭 스코프: PI 전용 라우트 `/pi/[id]` 미구현.
 *   LoadingSlides 15초 → 정적 완료 페이지 (Best Shot / 추구미 / 홈 cross-link).
 *   리포트 수신/이메일 발송 약속 카피 금지 (인프라 미준비).
 *   PI 통합 시점에 router.replace("/pi/{id}") 로 교체.
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

  return <CompletionScreen />;
}

function CompletionScreen() {
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
          DONE
        </span>
        <h1
          className="font-serif"
          style={{
            marginTop: 16,
            fontSize: 34,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
          }}
        >
          대화 고마워요.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 16,
            fontSize: 14,
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
            opacity: 0.6,
          }}
        >
          오늘 나눈 얘기는 잘 정리해뒀어요.
          <br />그 사이에 다른 기능도 둘러봐요.
        </p>
      </section>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <CtaLink href="/best-shot" label="Best Shot" subtitle="사진 여러 장에서 한 장" />
        <CtaLink href="/aspiration" label="추구미 분석" subtitle="따라가는 이미지, 실제로 뭐가 다른지" />
        <Link
          href="/"
          className="font-sans"
          style={{
            display: "block",
            height: 48,
            lineHeight: "48px",
            textAlign: "center",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.3px",
            opacity: 0.5,
            color: "var(--color-ink)",
            textDecoration: "none",
            marginTop: 4,
          }}
        >
          홈으로
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
        background: "var(--color-paper)",
        border: "1px solid var(--color-line-strong)",
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
            style={{
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
            }}
          >
            {label}
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 12,
              lineHeight: 1.5,
              letterSpacing: "-0.005em",
              opacity: 0.55,
              color: "var(--color-ink)",
            }}
          >
            {subtitle}
          </div>
        </div>
        <span
          aria-hidden
          style={{
            fontSize: 18,
            opacity: 0.4,
            color: "var(--color-ink)",
          }}
        >
          →
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
