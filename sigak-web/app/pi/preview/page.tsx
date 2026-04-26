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

// LLM 호출 (Sonnet + Haiku) 합산 ~30-60s 가능. 90s 후 timeout 으로 stuck 방어.
const PREVIEW_TIMEOUT_MS = 90_000;

// 단계별 로딩 메시지 — 정적 텍스트보다 진행 인지 강화.
// 실제 backend 단일 호출이므로 시간 기반 추정. 단계당 ~10s.
const LOADING_STAGES: Array<{ at: number; msg: string }> = [
  { at: 0, msg: "사진 분석 중" },
  { at: 8_000, msg: "결 정리 중" },
  { at: 18_000, msg: "유형 매칭 중" },
  { at: 28_000, msg: "트렌드 + 방향성 비교 중" },
  { at: 40_000, msg: "리포트 작성 중" },
  { at: 60_000, msg: "마무리 중 — 곧 도착해요" },
];

export default function PIPreviewPage() {
  const router = useRouter();
  const [report, setReport] = useState<PIv3Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [slowHint, setSlowHint] = useState(false);
  const [loadingStage, setLoadingStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let settled = false;   // fetch 성공/실패 시 true → timeout 무력화
    const startedAt = Date.now();
    setError(null);
    setReport(null);
    setSlowHint(false);
    setLoadingStage(0);
    setElapsed(0);

    // 단계별 로딩 메시지 — at(ms) 시점에 stage++
    const stageTimers = LOADING_STAGES.map((s, i) =>
      window.setTimeout(() => {
        if (!cancelled && !settled) setLoadingStage(i);
      }, s.at)
    );

    // 1초마다 elapsed 업데이트 (progress dots 동적)
    const tickTimer = window.setInterval(() => {
      if (!cancelled && !settled) {
        setElapsed(Math.floor((Date.now() - startedAt) / 1000));
      }
    }, 1_000);

    // 15s 후 "조금 오래 걸리고 있어요" 안내 (loading 인식)
    const slowTimer = window.setTimeout(() => {
      if (!cancelled && !settled) setSlowHint(true);
    }, 15_000);

    // 90s 후 timeout — fetch 가 아직 응답 없을 때만 발화 (report 보고 있을 땐 무관)
    const timeoutTimer = window.setTimeout(() => {
      if (!cancelled && !settled) {
        settled = true;
        setError(
          "응답이 너무 늦어요. 잠시 후 다시 시도해 주세요.",
        );
      }
    }, PREVIEW_TIMEOUT_MS);

    const clearAllTimers = () => {
      window.clearTimeout(timeoutTimer);
      window.clearTimeout(slowTimer);
      window.clearInterval(tickTimer);
      stageTimers.forEach((t) => window.clearTimeout(t));
    };

    (async () => {
      try {
        const res = await previewPIv3();
        settled = true;   // ✅ fetch 끝남 — timeout 무력화
        clearAllTimers();
        if (!cancelled) {
          // 이미 unlocked 상태면 풀 화면으로 직진
          if (!res.is_preview) {
            router.replace(`/pi/${encodeURIComponent(res.report_id)}`);
            return;
          }
          setReport(res);
        }
      } catch (e) {
        settled = true;   // ✅ 실패도 settled — timeout 무력화
        clearAllTimers();
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        if (e instanceof ApiError && e.status === 409) {
          router.replace("/pi/upload?next=preview");
          return;
        }
        // 친화 메시지 — 기술 메시지는 작은 글씨로 별도 노출
        if (e instanceof ApiError && e.status === 500) {
          setError("분석 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.");
        } else if (e instanceof TypeError) {
          // "Failed to fetch" 등 네트워크 레벨
          setError("연결이 끊겼어요. 네트워크 확인 후 다시 시도해 주세요.");
        } else {
          setError(
            e instanceof Error
              ? e.message
              : "PI 준비에 실패했어요. 잠시 후 다시 시도해 주세요.",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
      window.clearTimeout(slowTimer);
      window.clearTimeout(timeoutTimer);
      window.clearInterval(tickTimer);
      stageTimers.forEach((t) => window.clearTimeout(t));
    };
  }, [router, retryKey]);

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
            className="font-serif"
            style={{
              fontSize: 18,
              fontWeight: 400,
              lineHeight: 1.5,
              letterSpacing: "-0.005em",
              marginBottom: 12,
            }}
          >
            분석 준비에 실패했어요
          </p>
          <p
            className="font-sans"
            role="alert"
            style={{
              fontSize: 12,
              lineHeight: 1.6,
              opacity: 0.65,
              letterSpacing: "-0.005em",
              marginBottom: 24,
            }}
          >
            {error}
          </p>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 10,
              marginTop: 8,
            }}
          >
            <button
              type="button"
              onClick={() => setRetryKey((k) => k + 1)}
              className="font-sans"
              style={{
                height: 48,
                background: "var(--color-ink)",
                color: "var(--color-paper)",
                border: "none",
                borderRadius: 0,
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: "0.5px",
                cursor: "pointer",
              }}
            >
              다시 시도
            </button>
            <button
              type="button"
              onClick={() => router.replace("/")}
              className="font-sans"
              style={{
                height: 44,
                background: "transparent",
                color: "var(--color-ink)",
                border: "1px solid rgba(0,0,0,0.15)",
                borderRadius: 0,
                fontSize: 12,
                fontWeight: 500,
                letterSpacing: "0.3px",
                cursor: "pointer",
                opacity: 0.7,
              }}
            >
              홈으로
            </button>
          </div>
        </div>
      </main>
    );
  }

  if (!report) {
    const currentMsg = LOADING_STAGES[loadingStage]?.msg || "분석 중";
    const dotCount = (elapsed % 3) + 1;   // 1-2-3 점 sweep (1초 주기)
    const dots = ".".repeat(dotCount);
    // 진행도 추정 (총 60s 기준 시각화 — 실제 응답 기준 X, UX 만)
    const progressPct = Math.min(95, Math.floor((elapsed / 60) * 100));

    return (
      <main
        style={{
          minHeight: "100vh",
          background: "var(--color-paper)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: 28,
          gap: 18,
        }}
        aria-busy
        aria-live="polite"
      >
        <p
          className="font-serif"
          style={{
            fontSize: 16,
            opacity: 0.85,
            letterSpacing: "-0.005em",
            margin: 0,
            minHeight: 24,
          }}
        >
          {currentMsg}
          <span style={{ display: "inline-block", width: 18, textAlign: "left" }}>
            {dots}
          </span>
        </p>

        {/* 진행도 막대 — 시각 진행 인지. 60s 가정으로 추정. */}
        <div
          style={{
            width: 220,
            height: 2,
            background: "rgba(0,0,0,0.06)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 0,
              height: "100%",
              width: `${progressPct}%`,
              background: "var(--color-ink)",
              transition: "width 0.6s ease-out",
            }}
          />
        </div>

        <p
          className="font-sans"
          style={{
            fontSize: 11,
            opacity: 0.4,
            letterSpacing: "-0.005em",
            margin: 0,
            textAlign: "center",
            maxWidth: 280,
            lineHeight: 1.6,
          }}
        >
          {slowHint
            ? `평소보다 조금 오래 걸리고 있어요 · ${elapsed}s 경과`
            : `${elapsed}s 경과 · 30초~1분 정도 걸려요`}
        </p>
      </main>
    );
  }

  return <PIv3Screen report={report} />;
}
