// SIGAK MVP v1.2 (Rebrand) — AnalyzingScreen
//
// 4-step pipeline 제거 → 중앙 serif 헤드라인 + 1px 진행바만.
// 지속시간 4.4s → 3.2s. Home이 analyzing 상태일 때 inline 교체.
//
// ONBOARDING_ANALYSIS_STEPS / VERDICT_STEPS 상수는 유지(향후 재사용).
"use client";

import { useEffect, useState } from "react";

import { ProgressBar, TopBar } from "@/components/ui/sigak";

export interface AnalyzingStep {
  id: string;
  ko: string;
  en: string;
}

export const VERDICT_STEPS: AnalyzingStep[] = [
  { id: "001", ko: "후보 정렬", en: "ORDERING CANDIDATES" },
  { id: "002", ko: "구도 분석", en: "COMPOSITION READ" },
  { id: "003", ko: "표정 해석", en: "EXPRESSION READ" },
  { id: "004", ko: "교차 비교", en: "CROSS-COMPARE" },
];

export const ONBOARDING_ANALYSIS_STEPS: AnalyzingStep[] = [
  { id: "001", ko: "얼굴 기준점 검출", en: "FACIAL LANDMARKS" },
  { id: "002", ko: "3축 스코어링", en: "3-AXIS SCORING" },
  { id: "003", ko: "8-타입 매칭", en: "8-TYPE MATCHING" },
  { id: "004", ko: "리포트 생성", en: "REPORT GENERATION" },
];

interface AnalyzingScreenProps {
  candidateCount: number;
  /** 헤드라인 override. 기본 "읽고 있습니다." */
  headline?: string;
  /** 총 진행 시간 (ms). 기본 3200. */
  durationMs?: number;
}

export function AnalyzingScreen({
  candidateCount,
  headline = "읽고 있습니다.",
  durationMs = 3200,
}: AnalyzingScreenProps) {
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      setPct(Math.round(eased * 100));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [durationMs]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <TopBar />

      {/* 중앙 헤드라인 */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 28px",
        }}
      >
        <h1
          className="font-serif"
          style={{
            fontSize: 32,
            fontWeight: 400,
            lineHeight: 1.4,
            letterSpacing: "-0.01em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          {headline}
        </h1>
        {candidateCount > 0 && (
          <p
            className="font-sans"
            style={{
              marginTop: 14,
              fontSize: 13,
              opacity: 0.5,
              lineHeight: 1.6,
              color: "var(--color-ink)",
            }}
          >
            사진 {candidateCount}장.
          </p>
        )}
      </div>

      {/* 진행바 */}
      <div style={{ padding: "0 28px 48px" }}>
        <ProgressBar pct={pct} label="진행" />
      </div>
    </div>
  );
}
