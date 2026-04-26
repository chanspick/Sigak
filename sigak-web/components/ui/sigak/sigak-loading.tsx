/**
 * SigakLoading — 표준 로딩 화면 (redesign/로딩_1815.html 차용).
 *
 * Phase B-8 (PI-REVIVE 2026-04-26): 본인 결정 — 앱 전반의 로딩 UI 통일.
 * 기존: LoadingSlides (5장 carousel) / AnalyzingScreen / aspiration[id] 빈 div
 *      / vision-view "불러오는 중..." 등 메시지 + 디자인 제각각.
 * 통일: 본 컴포넌트 1개 — SIGAK 로고 + message + 3-dot pulse + hint.
 *
 * 구조:
 *   - SIGAK 로고 60x60 (검정 배경 + 흰색 디테일)
 *   - message (Pretendard 16px, line-height 1.7)
 *   - 3-dot pulse 애니메이션 (var(--color-danger))
 *   - hint (Pretendard 12px, mute color)
 *
 * 토큰: globals.css (var(--color-paper) / --color-ink / --color-mute / --color-danger).
 * redesign HTML 의 #F5F1EB / #2D2D2D / ember 등 hardcode 미사용 (memory rule).
 */

"use client";

interface SigakLoadingProps {
  /** 본 메시지 (예: "분석 중이에요"). 기본: "잠시만요, 분석중이에요." */
  message?: string;
  /** 힌트 텍스트 (mute). 기본: "최대 30초 정도 걸릴 수 있어요" */
  hint?: string;
  /** aria-label override (스크린리더). 기본: message */
  ariaLabel?: string;
}

export function SigakLoading({
  message = "잠시만요, 분석중이에요.",
  hint = "최대 30초 정도 걸릴 수 있어요",
  ariaLabel,
}: SigakLoadingProps = {}) {
  return (
    <main
      role="status"
      aria-live="polite"
      aria-label={ariaLabel ?? message}
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
      {/* SIGAK 로고 60x60 (redesign/로딩_1815.html 정합) */}
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

      {/* Message */}
      <p
        className="font-sans"
        style={{
          fontSize: 16,
          color: "var(--color-ink)",
          opacity: 0.75,
          lineHeight: 1.7,
          letterSpacing: "-0.005em",
          marginBottom: 28,
          margin: 0,
        }}
      >
        {message}
      </p>

      {/* 3-dot pulse */}
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          marginTop: 28,
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

      {/* Hint */}
      {hint && (
        <p
          className="font-sans"
          style={{
            fontSize: 12,
            color: "var(--color-mute)",
            letterSpacing: "-0.003em",
            margin: 0,
          }}
        >
          {hint}
        </p>
      )}
    </main>
  );
}
