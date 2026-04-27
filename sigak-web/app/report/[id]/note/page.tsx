// SPEC-PI-FINALE-001 — /report/{id}/note
//
// Card 1 hero 페이지. 홈 시각 탭 카드 클릭 시 도착하는 위치.
// "디저트 트레이 1장" — 단일 의식.
//
// 흐름:
//   /vision 시각 탭 → FinalePreviewCard 클릭 → /report/{id}/note (이 페이지)
//   → "자세한 분석 보기 →" CTA → /report/{id}/full (전체 PI + Card 2 4-step)
//
// 50토큰 갱신 CTA 는 본 페이지에 없음 (홈 시각 탭 단일 위치 정책).

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getReportFinale } from "@/lib/api/client";
import { getToken } from "@/lib/auth";
import { SigakLoading, TopBar } from "@/components/ui/sigak";
import { FinaleHeroCard } from "@/components/finale/FinaleHeroCard";

interface FinaleData {
  headline: string;
  leadParagraph: string;
}

export default function NotePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const [state, setState] = useState<{
    loading: boolean;
    finale: FinaleData | null;
    error: string | null;
  }>({ loading: true, finale: null, error: null });

  useEffect(() => {
    if (!getToken()) {
      router.replace(`/auth/login?next=/report/${encodeURIComponent(id)}/note`);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const data = await getReportFinale(id);
        if (cancelled) return;
        setState({
          loading: false,
          finale: {
            headline: data.sia_finale.headline,
            leadParagraph: data.sia_finale.lead_paragraph,
          },
          error: null,
        });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        const message =
          e instanceof Error
            ? e.message
            : "마무리 한 마디를 불러오지 못했어요.";
        setState({ loading: false, finale: null, error: message });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  if (state.loading) {
    return <SigakLoading message="잠시만요" hint="" />;
  }

  if (state.error || !state.finale) {
    return (
      <>
        <TopBar backTarget="/" hideTokens />
        <main
          style={{
            minHeight: "calc(100vh - 64px)",
            background: "var(--color-paper)",
            padding: "60px 28px",
            textAlign: "center",
          }}
        >
          <p
            className="font-sans"
            role="alert"
            style={{
              fontSize: 14,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              marginBottom: 24,
            }}
          >
            {state.error ?? "마무리 한 마디를 불러오지 못했어요."}
          </p>
          <Link
            href={`/report/${encodeURIComponent(id)}/full`}
            className="font-sans"
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "13px 24px",
              background: "transparent",
              color: "var(--color-mute)",
              border: "1.5px solid var(--color-line)",
              borderRadius: 100,
              fontSize: 13,
              fontWeight: 500,
              textDecoration: "none",
            }}
          >
            전체 분석 보기 →
          </Link>
        </main>
      </>
    );
  }

  return (
    <>
      <TopBar backTarget="/" hideTokens />
      <main
        style={{
          minHeight: "calc(100vh - 64px)",
          background: "var(--color-paper)",
          color: "var(--color-ink)",
        }}
      >
        <FinaleHeroCard
          headline={state.finale.headline}
          leadParagraph={state.finale.leadParagraph}
        />

        {/* 단일 CTA — "자세한 분석 보기 →" → /report/{id}/full
            50토큰 갱신 CTA 는 본 페이지에 없음 (홈 시각 탭 단일 위치 정책). */}
        <div
          style={{
            maxWidth: 480,
            margin: "0 auto",
            padding: "0 28px 80px",
          }}
        >
          <Link
            href={`/report/${encodeURIComponent(id)}/full`}
            className="font-sans"
            style={{
              display: "inline-flex",
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
            자세한 분석 보기 →
          </Link>
        </div>
      </main>
    </>
  );
}
