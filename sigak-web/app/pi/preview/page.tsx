/**
 * /pi/preview — PI v3 무료 preview (혼합 iii visibility).
 *
 * 흐름:
 *   /pi/upload 성공 → router.replace("/pi/preview") → previewPIv3() 호출
 *   응답 = is_preview=true PIv3Report → PIv3Screen 렌더 (cover/celeb 풀 + 4 teaser + 3 lock)
 *
 * 가드:
 *   - 401 → 홈으로
 *   - 409 (baseline 없음) → /pi/upload
 *   - 그 외 에러 → error UI
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { previewPIv3 } from "@/lib/api/pi";
import type { PIv3Report } from "@/lib/api/pi";
import { PIv3Screen } from "@/components/pi-v3/PIv3Screen";

export default function PIPreviewPage() {
  const router = useRouter();
  const [report, setReport] = useState<PIv3Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await previewPIv3();
        if (!cancelled) {
          // 이미 unlocked 상태면 풀 화면으로 직진
          if (!res.is_preview) {
            router.replace(`/pi/${encodeURIComponent(res.report_id)}`);
            return;
          }
          setReport(res);
        }
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        if (e instanceof ApiError && e.status === 409) {
          router.replace("/pi/upload?next=preview");
          return;
        }
        setError(e instanceof Error ? e.message : "PI 준비에 실패했어요.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

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
        <div style={{ textAlign: "center", maxWidth: 320 }}>
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
        </div>
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
          분석 준비 중...
        </p>
      </main>
    );
  }

  return <PIv3Screen report={report} />;
}
