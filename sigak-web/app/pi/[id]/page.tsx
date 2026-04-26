/**
 * /pi/[id] — PI v3 풀 리포트 조회 (unlock 후).
 *
 * 흐름:
 *   /pi/preview → unlock CTA → unlockPIv3() → router.replace(`/pi/${reportId}`)
 *   /pi/list 또는 /vision 의 PI 카드에서 진입
 *
 * 응답:
 *   is_preview=false PIv3Report → PIv3Screen 풀 노출
 *
 * 가드:
 *   - 401 → 홈
 *   - 403 → my page (다른 유저 리포트)
 *   - 404 → list
 */

"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getPIv3Report } from "@/lib/api/pi";
import type { PIv3Report } from "@/lib/api/pi";
import { PIv3Screen } from "@/components/pi-v3/PIv3Screen";

interface PIDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function PIDetailPage({ params }: PIDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const [report, setReport] = useState<PIv3Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await getPIv3Report(id);
        if (!cancelled) setReport(res);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        if (e instanceof ApiError && e.status === 403) {
          router.replace("/my");
          return;
        }
        if (e instanceof ApiError && e.status === 404) {
          router.replace("/vision");
          return;
        }
        setError(e instanceof Error ? e.message : "리포트 불러오기 실패");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, router]);

  if (error) {
    return (
      <main
        style={{
          minHeight: "100vh",
          background: "var(--color-paper)",
          color: "var(--color-ink)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 28,
        }}
      >
        <p
          className="font-sans"
          role="alert"
          style={{
            fontSize: 13,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
          }}
        >
          {error}
        </p>
      </main>
    );
  }

  if (!report) {
    return (
      <main
        style={{
          minHeight: "100vh",
          background: "var(--color-paper)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        aria-busy
      >
        <p
          className="font-sans"
          style={{
            fontSize: 12,
            opacity: 0.4,
            letterSpacing: "-0.005em",
          }}
        >
          불러오는 중...
        </p>
      </main>
    );
  }

  return <PIv3Screen report={report} />;
}
