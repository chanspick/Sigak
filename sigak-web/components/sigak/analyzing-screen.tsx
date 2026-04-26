// SIGAK MVP v1.2 — AnalyzingScreen
//
// 2026-04-26 마케터 정합: photo-upload 분석 로딩 화면과 동일 패턴.
//   - SIGAK 로고 60x60 검정
//   - "sia가 피드를 분석중이에요." (마케터 redesign/로딩_1815.html 차용)
//   - dotPulse 3-dot stagger 애니메이션 (var(--color-danger))
//   - "최대 30초 정도 걸릴 수 있어요" 서브 힌트
//   - TopBar / ProgressBar 제거 (단순화)
//
// done / onFinish 흐름은 보존:
//   1. mount → CLIMB_MS 동안 progress 누적 (UI 미노출, 내부 timer 만)
//   2. done=true 도달 시 COMPLETE_MS 후 onFinish 호출 → 상위 navigate
"use client";

import { useEffect, useRef, useState } from "react";

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

const CLIMB_MS = 2500;
const COMPLETE_MS = 400;
const POST_COMPLETE_BUFFER_MS = 120;

interface AnalyzingScreenProps {
  candidateCount: number;
  /** 호환용 — 사용 X (내부 단순화). */
  headline?: string;
  /** 실제 비동기 작업 완료 여부. true 도달 시 COMPLETE_MS 후 onFinish. */
  done?: boolean;
  /** 완료 후 호출 — 상위가 navigate. */
  onFinish?: () => void;
}

export function AnalyzingScreen({
  candidateCount: _candidateCount,
  headline: _headline,
  done = false,
  onFinish,
}: AnalyzingScreenProps) {
  const [climbed, setClimbed] = useState(false);
  const finishedRef = useRef(false);

  // CLIMB_MS 후 climbed=true (내부 progress 신호 — UI 미노출)
  useEffect(() => {
    const t = setTimeout(() => setClimbed(true), CLIMB_MS);
    return () => clearTimeout(t);
  }, []);

  // done && climbed → COMPLETE_MS 후 onFinish
  useEffect(() => {
    if (!done || !climbed) return;
    if (finishedRef.current) return;
    finishedRef.current = true;
    const t = setTimeout(
      () => onFinish?.(),
      COMPLETE_MS + POST_COMPLETE_BUFFER_MS,
    );
    return () => clearTimeout(t);
  }, [done, climbed, onFinish]);

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 28px",
        textAlign: "center",
      }}
      aria-busy
    >
      {/* SIGAK 로고 60x60 (마케터 로딩_1815.html 정합) */}
      <svg
        width="60"
        height="60"
        viewBox="0 0 40 40"
        xmlns="http://www.w3.org/2000/svg"
        style={{ marginBottom: 40 }}
        aria-hidden
      >
        <rect width="40" height="40" rx="7" fill="#1a1a1a" />
        <g stroke="#ffffff" strokeWidth="1.5" fill="none" strokeLinecap="round">
          <line x1="20" y1="6" x2="20" y2="13" />
          <path d="M 6 19.5 Q 20 11.5 34 19.5 Q 20 27.5 6 19.5 Z" />
          <circle cx="20" cy="19.5" r="2.6" />
        </g>
        <path
          d="M 20 22.5 C 18.4 25, 17.4 28, 17.4 30 C 17.4 31.9, 18.6 32.8, 20 32.8 C 21.4 32.8, 22.6 31.9, 22.6 30 C 22.6 28, 21.6 25, 20 22.5 Z"
          fill="#ffffff"
        />
      </svg>

      <p
        className="font-sans"
        style={{
          fontSize: 16,
          color: "var(--color-ink)",
          opacity: 0.75,
          lineHeight: 1.7,
          letterSpacing: "-0.005em",
          marginBottom: 28,
        }}
      >
        sia가 피드를 분석중이에요.
      </p>

      {/* dot-pulse 3-dot */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          marginBottom: 36,
        }}
        aria-hidden
      >
        <span
          className="animate-dot-pulse"
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "var(--color-danger)",
          }}
        />
        <span
          className="animate-dot-pulse-delay-1"
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "var(--color-danger)",
          }}
        />
        <span
          className="animate-dot-pulse-delay-2"
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: "var(--color-danger)",
          }}
        />
      </div>

      <p
        className="font-sans"
        style={{
          fontSize: 12,
          color: "var(--color-mute)",
          letterSpacing: "-0.003em",
        }}
      >
        최대 30초 정도 걸릴 수 있어요
      </p>
    </main>
  );
}
