/**
 * LoadingSlides — 분석 / 리포트 생성 대기 화면.
 *
 * 5 슬라이드 × 5초 = 총 25초 후 마지막 슬라이드 hold.
 *   - onComplete 있으면 마지막 슬라이드 5초 후 콜백 (Sia → 리포트 redirect)
 *   - onComplete 없으면 응답 올 때까지 마지막 슬라이드 무한 hold
 *     (Aspiration: Sonnet cross-analysis ~35-40초 — 사진 10장 fetch + base64
 *     + Sonnet 응답 + JSON parse + Hard Rules 검증)
 *
 * 마지막 슬라이드는 fade-out 안 함 — 하얀 화면 회귀 방지.
 *
 * 스킵 불가 (클릭/터치/키보드 무반응).
 * 카피: 마케터 세션 #5 확정 대기 — 현재 placeholder.
 *      페르소나 B 톤 (해요체). 이모지/ㅋ/ㅎ/~ 0건.
 * 접근성: aria-live="polite". prefers-reduced-motion 시 transition 비활성.
 */

"use client";

import { useEffect, useRef, useState } from "react";

interface Slide {
  title: string;
  subtitle: string;
}

const SLIDES: Slide[] = [
  {
    title: "피드를 다시 보고 있어요",
    subtitle: "올리신 사진들 안에서 살핀 흐름을 정리하는 중이에요",
  },
  {
    title: "관찰을 조립하는 중이에요",
    subtitle: "반복되는 선택이 가리키는 방향을 맞춰보고 있어요",
  },
  {
    title: "톤을 정돈하는 중이에요",
    subtitle: "색과 구도가 한 사람 안에서 어떻게 엮이는지 보고 있어요",
  },
  {
    title: "문장을 고르는 중이에요",
    subtitle: "읽는 글처럼 와닿게 다듬는 중이에요",
  },
  {
    title: "거의 다 왔어요",
    subtitle: "마지막 부분을 확인하고 있어요",
  },
];

const SLIDE_DURATION_MS = 5000;
const FADE_DURATION_MS = 500;

interface LoadingSlidesProps {
  onComplete?: () => void;
}

export function LoadingSlides({ onComplete }: LoadingSlidesProps) {
  const [index, setIndex] = useState(0);
  const [fading, setFading] = useState(false);
  const completedRef = useRef(false);

  useEffect(() => {
    if (completedRef.current) return;

    const isLast = index >= SLIDES.length - 1;

    if (isLast) {
      // 마지막 슬라이드는 fade-out 안 만듬 (하얀 화면 회귀 방지).
      // onComplete 있을 때만 SLIDE_DURATION_MS 후 콜백 (Sia → redirect).
      // onComplete 없으면 응답 올 때까지 그대로 hold.
      if (!onComplete) return;
      const completeTimer = setTimeout(() => {
        if (!completedRef.current) {
          completedRef.current = true;
          onComplete();
        }
      }, SLIDE_DURATION_MS);
      return () => clearTimeout(completeTimer);
    }

    // 일반 슬라이드 — 페이드 아웃 → 다음 슬라이드 전환
    const fadeTimer = setTimeout(
      () => setFading(true),
      SLIDE_DURATION_MS - FADE_DURATION_MS,
    );
    const nextTimer = setTimeout(() => {
      setIndex((i) => i + 1);
      setFading(false);
    }, SLIDE_DURATION_MS);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(nextTimer);
    };
  }, [index, onComplete]);

  const current = SLIDES[index];

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="리포트를 준비하고 있어요"
      className="flex min-h-screen flex-col items-center justify-center"
      style={{
        background: "var(--color-paper)",
        padding: "0 28px",
        position: "relative",
      }}
    >
      {/* 페이지 인디케이터 (1 / 5) */}
      <div
        className="type-serif-numeric"
        style={{
          position: "absolute",
          top: 20,
          right: 24,
          color: "var(--ink-40, rgba(0,0,0,0.4))",
        }}
      >
        {index + 1} / {SLIDES.length}
      </div>

      <div
        style={{
          maxWidth: 360,
          textAlign: "center",
          transition: `opacity ${FADE_DURATION_MS}ms ease-out`,
          opacity: fading ? 0 : 1,
        }}
        key={index}
      >
        <h1
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 28,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
          }}
        >
          {current.title}
        </h1>
        <p
          className="font-sans"
          style={{
            margin: "16px 0 0",
            fontSize: 13,
            lineHeight: 1.6,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
            opacity: 0.55,
          }}
        >
          {current.subtitle}
        </p>
      </div>

      {/* 하단 진행 인디케이터 (5 dots → 5 bars) */}
      <div
        aria-hidden
        style={{
          position: "absolute",
          bottom: 48,
          display: "flex",
          gap: 8,
        }}
      >
        {SLIDES.map((_, i) => (
          <span
            key={i}
            style={{
              height: 2,
              width: 24,
              background:
                i <= index ? "var(--color-ink)" : "rgba(0, 0, 0, 0.15)",
              transition: `background ${FADE_DURATION_MS}ms ease-out`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
