// SIGAK MVP v1.2 — AnalyzingScreen
//
// Home이 verdict 생성 중일 때 inline으로 렌더. refactor/analyzing-screen.jsx v0.3
// 에디토리얼 포팅 — TopBar + ProgressBar + § PIPELINE 4스텝.
//
// STEPS prop으로 verdict용 / onboarding용 / 기타 분기 가능. 기본은 verdict.
// durationMs prop으로 최소 표시 시간 제어 (실제 POST 응답과 무관).
"use client";

import { useEffect, useState } from "react";

import { ProgressBar, TopBar } from "@/components/ui/sigak";

export interface AnalyzingStep {
  id: string;         // "001", "002" etc.
  ko: string;         // 한국어 라벨
  en: string;         // 상단 메타 우측 (영문 code)
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
  /** 상단 토큰 카운터. null이면 TopBar 토큰 숨김. */
  tokens?: number | null;
  /** 후보 개수 (헤드라인용). */
  candidateCount: number;
  /** 스텝 목록. 기본 VERDICT_STEPS. */
  steps?: AnalyzingStep[];
  /** 헤드라인 커스터마이즈. 기본 "N장의 후보를 진단 중입니다". */
  headline?: string;
  /** 애니메이션 총 시간 (ms). 기본 4400. */
  durationMs?: number;
}

export function AnalyzingScreen({
  tokens = null,
  candidateCount,
  steps = VERDICT_STEPS,
  headline,
  durationMs = 4400,
}: AnalyzingScreenProps) {
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / durationMs);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - p, 3);
      setPct(Math.round(eased * 100));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [durationMs]);

  const stepCount = steps.length;
  const perStep = 100 / stepCount;
  const activeIdx = Math.min(stepCount - 1, Math.floor(pct / perStep));

  const stateFor = (i: number): "done" | "active" | "idle" => {
    if (pct >= 100) return "done";
    if (i < activeIdx) return "done";
    if (i === activeIdx) return "active";
    return "idle";
  };

  const defaultHeadline = `${candidateCount}장의 후보를\n진단 중입니다.`;
  const lines = (headline ?? defaultHeadline).split("\n");

  return (
    <div className="min-h-screen bg-paper pb-10 text-ink">
      <TopBar
        variant="minimal"
        tokens={tokens ?? 0}
        hideTokens={tokens == null}
      />

      {/* RUN meta */}
      <div className="mt-[14px] flex items-baseline justify-between px-5">
        <span
          className="font-mono uppercase text-mute"
          style={{ fontSize: 10, letterSpacing: "0.14em" }}
        >
          RUN
        </span>
        <span
          className="font-mono uppercase text-mute tabular-nums"
          style={{ fontSize: 10, letterSpacing: "0.14em" }}
        >
          {String(candidateCount).padStart(3, "0")}·CAND
        </span>
      </div>

      {/* Headline */}
      <div className="px-5 pt-6">
        <h1
          className="font-sans font-medium text-ink"
          style={{
            fontSize: 26,
            fontWeight: 500,
            lineHeight: 1.3,
            letterSpacing: "-0.02em",
          }}
        >
          {lines.map((l, i) => (
            <span key={i}>
              {l}
              {i < lines.length - 1 && <br />}
            </span>
          ))}
        </h1>
      </div>

      {/* Progress */}
      <div className="mt-8">
        <ProgressBar pct={pct} className="px-5" />
      </div>

      {/* § 01 — PIPELINE */}
      <section className="mt-10">
        <div className="mb-[6px] flex items-baseline gap-2.5 px-5">
          <span
            className="font-mono text-mute"
            style={{ fontSize: 10, letterSpacing: "0.14em" }}
          >
            § 01
          </span>
          <span
            className="font-display font-medium uppercase text-ink"
            style={{ fontSize: 10, letterSpacing: "0.22em" }}
          >
            — PIPELINE
          </span>
        </div>

        <div className="px-5">
          {steps.map((s, i) => (
            <StepRow key={s.id} step={s} state={stateFor(i)} />
          ))}
        </div>
      </section>

      {/* Footer disclaimer */}
      <div className="mt-9 px-5">
        <p
          className="font-sans text-mute"
          style={{
            fontSize: 11,
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
          }}
        >
          SIGAK의 판정은 해석이지 정답이 아닙니다.
          <br />
          결과는 당신의 판단을 돕기 위한 참고입니다.
        </p>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  StepRow
// ─────────────────────────────────────────────

function Dot({ state }: { state: "done" | "active" | "idle" }) {
  if (state === "done") {
    return (
      <span
        aria-hidden
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "var(--color-sage)",
          flexShrink: 0,
          display: "block",
        }}
      />
    );
  }
  if (state === "active") {
    return (
      <span
        aria-hidden
        className="animate-active-pulse"
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          border: "1px solid var(--color-sage)",
          background: "transparent",
          flexShrink: 0,
          display: "block",
        }}
      />
    );
  }
  return (
    <span
      aria-hidden
      style={{
        width: 8,
        height: 8,
        borderRadius: "50%",
        border: "1px solid var(--color-line-strong)",
        background: "transparent",
        flexShrink: 0,
        display: "block",
      }}
    />
  );
}

function StepRow({ step, state }: { step: AnalyzingStep; state: "done" | "active" | "idle" }) {
  const muted = state === "idle";
  const done = state === "done";
  return (
    <div
      className="border-b"
      style={{
        display: "grid",
        gridTemplateColumns: "16px 44px 1fr auto",
        alignItems: "center",
        gap: 12,
        padding: "13px 0",
        borderColor: "var(--color-line)",
      }}
    >
      <Dot state={state} />
      <span
        className="font-mono tabular-nums"
        style={{
          fontSize: 10,
          letterSpacing: "0.14em",
          color: muted ? "var(--color-mute-2)" : "var(--color-mute)",
        }}
      >
        /{step.id}
      </span>
      <span
        className="font-sans"
        style={{
          fontSize: 15,
          fontWeight: done ? 400 : 500,
          letterSpacing: "-0.01em",
          color: muted ? "var(--color-mute)" : "var(--color-ink)",
        }}
      >
        {step.ko}
      </span>
      <span
        className="font-display uppercase"
        style={{
          fontSize: 10,
          letterSpacing: "0.14em",
          color: muted ? "var(--color-mute-2)" : "var(--color-mute)",
        }}
      >
        {step.en}
      </span>
    </div>
  );
}
