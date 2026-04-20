// SIGAK MVP v1.2 (Rebrand) — AnalyzingScreen
//
// 진행바 동작 (실제 POST 응답과 동기화):
//   1. 마운트 → 2.5초 동안 cubic ease로 0% → 90% 도달
//   2. POST가 아직 진행 중이면 90%에서 hold (부드러운 pulse)
//   3. POST 응답 오면(done=true) 90% → 100%로 400ms snap
//   4. 100% 도달 후 onFinish 콜백 호출 → 상위가 navigate
//
// 이 설계로 "100% 찍고 멍때리는" 상황 제거. 빠른 응답이면 2.9초 안에 완료,
// 느린 응답이면 90%에서 합리적으로 대기.
"use client";

import { useEffect, useRef, useState } from "react";

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

type Phase = "climbing" | "holding" | "completing";

const CLIMB_MS = 2500;       // 0% → 90%
const HOLD_CAP_PCT = 90;     // hold 단계 상한
const COMPLETE_MS = 400;     // 90% → 100% snap
const POST_COMPLETE_BUFFER_MS = 120; // 100% 도달 후 navigate 전 짧은 여유

interface AnalyzingScreenProps {
  candidateCount: number;
  /** 헤드라인 override. 기본 "읽고 있습니다." */
  headline?: string;
  /** 실제 비동기 작업 완료 여부. true가 되면 100%로 snap. */
  done?: boolean;
  /** 100% 도달 + 버퍼 후 호출. 상위가 navigate 하는 용도. */
  onFinish?: () => void;
}

export function AnalyzingScreen({
  candidateCount,
  headline = "고르고 있어요.",
  done = false,
  onFinish,
}: AnalyzingScreenProps) {
  const [pct, setPct] = useState(0);
  const [phase, setPhase] = useState<Phase>("climbing");
  const finishedRef = useRef(false);

  // Phase 1: 0% → 90% cubic ease over CLIMB_MS
  useEffect(() => {
    if (phase !== "climbing") return;
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / CLIMB_MS);
      const eased = 1 - Math.pow(1 - p, 3);
      setPct(Math.round(eased * HOLD_CAP_PCT));
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        setPct(HOLD_CAP_PCT);
        setPhase("holding");
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [phase]);

  // Phase 2 → 3: done + holding 도달 시 completing으로
  useEffect(() => {
    if (done && phase === "holding") setPhase("completing");
  }, [done, phase]);

  // Phase 3: 현재 pct → 100% linear over COMPLETE_MS, 완료 시 onFinish
  useEffect(() => {
    if (phase !== "completing") return;
    const start = performance.now();
    const from = pct;
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / COMPLETE_MS);
      setPct(Math.round(from + (100 - from) * p));
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        setPct(100);
        if (!finishedRef.current) {
          finishedRef.current = true;
          setTimeout(() => onFinish?.(), POST_COMPLETE_BUFFER_MS);
        }
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
    // from을 dep에 넣으면 매 렌더 리셋되므로 고정 — phase 변화 시에만 실행.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

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

      <div
        style={{
          padding: "0 28px 48px",
          // holding 단계에서 부드러운 opacity 펄스 → "멈춘 것 아님" 시그널
          opacity: phase === "holding" ? undefined : 1,
          animation:
            phase === "holding"
              ? "sigak-hold-pulse 1600ms ease-in-out infinite"
              : undefined,
        }}
      >
        <ProgressBar pct={pct} label="진행" />
      </div>

      {/* inline keyframes — globals에 안 넣어도 이 화면 전용 */}
      <style>{`
        @keyframes sigak-hold-pulse {
          0%, 100% { opacity: 1; }
          50%      { opacity: 0.75; }
        }
      `}</style>
    </div>
  );
}
