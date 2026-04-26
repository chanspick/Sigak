// SIGAK PI-REVIVE v5 — VisionView (옛 SIGAK_V3 system 진입점, 2026-04-26).
//
// 신 PI v3 (PIv3Status / getPIv3Status / deletePIv3) 폐기.
// 옛 system (`/api/v1/my/reports` + `/report/{id}/full`) 사용.
//
// /vision 탭 컨텐츠. my reports 분기 (2 states):
//
//   1) reports.length === 0 → 사진 보여드리기 CTA → /photo-upload
//   2) reports.length > 0   → 최신 report 카드 → /report/{id}/full

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getMyReports } from "@/lib/api/client";

interface MyReport {
  id: string;
  access_level: string;
  created_at: string;
  url: string;
}

export function VisionView() {
  const router = useRouter();

  const [state, setState] = useState<{
    loading: boolean;
    reports: MyReport[] | null;
    error: string | null;
  }>({ loading: true, reports: null, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // 옛 system = localStorage("sigak_user_id") 패턴 (app/my/page.tsx 정합)
      const userId = typeof window !== "undefined"
        ? localStorage.getItem("sigak_user_id")
        : null;

      if (!userId) {
        // auth 없음 = 홈 redirect (옛 system 정합)
        router.replace("/");
        return;
      }

      try {
        const data = await getMyReports(userId);
        if (!cancelled) {
          setState({ loading: false, reports: data.reports, error: null });
        }
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        setState({
          loading: false,
          reports: null,
          error: e instanceof Error ? e.message : "리포트 로드 실패",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state.loading) return <LoadingPlaceholder />;
  if (state.error || !state.reports)
    return <ErrorBlock message={state.error ?? "알 수 없는 오류"} />;

  const reports = state.reports;

  // 1) 리포트 없음 — 사진 업로드 entry
  if (reports.length === 0) {
    return <PhotoUploadNeededBlock />;
  }

  // 2) 리포트 있음 — 최신 report 카드 (created_at 내림차순 가정. 백엔드가 보장 안 하면 정렬)
  const sortedReports = [...reports].sort((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
    return tb - ta;
  });
  const latest = sortedReports[0];

  return <MyReportsBlock report={latest} />;
}

// ─────────────────────────────────────────────
//  Blocks
// ─────────────────────────────────────────────

function LoadingPlaceholder() {
  return (
    <div
      style={{
        minHeight: "40vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: 0.3,
        fontSize: 12,
        fontFamily: "var(--font-sans)",
        color: "var(--color-ink)",
      }}
      aria-busy
    >
      불러오는 중...
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div style={{ padding: "40px 28px", textAlign: "center" }}>
      <p
        className="font-sans"
        role="alert"
        style={{
          fontSize: 13,
          color: "var(--color-danger)",
          letterSpacing: "-0.005em",
        }}
      >
        {message}
      </p>
    </div>
  );
}

// 1) 리포트 없음 — 정면 사진 한 컷 안내 (transition 카피 보존)
function PhotoUploadNeededBlock() {
  return (
    <section style={{ padding: "32px 28px 60px" }}>
      <div
        style={{
          padding: "20px 22px",
          border: "1px solid rgba(0, 0, 0, 0.12)",
          background: "rgba(0, 0, 0, 0.02)",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
            marginBottom: 10,
          }}
        >
          PI — Personal Image
        </div>
        <p
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 18,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
          }}
        >
          시각이 본 나, 완성하려면<br />정면 사진 한 장이 필요해요.
        </p>
        <p
          className="font-sans"
          style={{
            margin: "12px 0 0",
            fontSize: 12,
            lineHeight: 1.7,
            opacity: 0.6,
            letterSpacing: "-0.005em",
          }}
        >
          얼굴이 또렷하게 잡히는 정면 한 컷이면 돼요. 화장은 안 하셔도 분석 가능해요.
        </p>
      </div>

      <Link
        href="/photo-upload"
        className="font-sans"
        style={{
          marginTop: 18,
          width: "100%",
          height: 54,
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          border: "none",
          borderRadius: 0,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "0.5px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          textDecoration: "none",
        }}
      >
        📷 사진 한 장 보여드리기
      </Link>
    </section>
  );
}

// 2) 리포트 있음 — 최신 report 카드 + 풀 화면 link + 다시 받기 (옛 system, BETA 무료)
function MyReportsBlock({ report }: { report: MyReport }) {
  const dateLabel = report.created_at
    ? new Date(report.created_at).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <section style={{ padding: "32px 28px 60px" }}>
      <Link
        href={`/report/${encodeURIComponent(report.id)}/full`}
        className="font-sans"
        style={{
          display: "block",
          padding: "24px 22px",
          border: "1px solid rgba(0,0,0,0.15)",
          color: "var(--color-ink)",
          textDecoration: "none",
          background: "var(--color-paper)",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
          }}
        >
          시각이 본 당신
        </div>
        <p
          className="font-serif"
          style={{
            margin: "10px 0 0",
            fontSize: 18,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
          }}
        >
          현재 리포트 열기 →
        </p>
        {dateLabel && (
          <p
            className="font-sans"
            style={{
              margin: "8px 0 0",
              fontSize: 11,
              opacity: 0.5,
              letterSpacing: "-0.005em",
            }}
          >
            {dateLabel} 분석
          </p>
        )}
      </Link>

      <div
        style={{
          marginTop: 18,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <Link
          href="/photo-upload"
          className="font-sans"
          style={{
            display: "flex",
            width: "100%",
            height: 48,
            alignItems: "center",
            justifyContent: "center",
            background: "transparent",
            color: "var(--color-ink)",
            border: "1px solid rgba(0,0,0,0.15)",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "-0.005em",
            textDecoration: "none",
            borderRadius: 0,
          }}
        >
          📷 사진 다시 올려서 새로 받기
        </Link>
      </div>
    </section>
  );
}
