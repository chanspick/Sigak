// SIGAK MVP v1.2 — AnalyzingScreen
//
// 2026-04-27: SigakLoading 으로 흡수. 시각 자체는 SigakLoading 에 위임,
// 본 컴포넌트는 done/onFinish 타이밍 머신 + step constant export 만 유지.
//
// done / onFinish 흐름:
//   1. mount → CLIMB_MS 동안 progress 누적 (UI 미노출, 내부 timer 만)
//   2. done=true 도달 시 COMPLETE_MS 후 onFinish 호출 → 상위 navigate
"use client";

import { useEffect, useRef, useState } from "react";

import { SigakLoading } from "@/components/ui/sigak";

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

  useEffect(() => {
    const t = setTimeout(() => setClimbed(true), CLIMB_MS);
    return () => clearTimeout(t);
  }, []);

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

  return <SigakLoading message="sia가 피드를 분석중이에요." />;
}
