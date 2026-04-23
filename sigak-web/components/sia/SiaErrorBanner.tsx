/**
 * SiaErrorBanner — Sia 대화 중 에러 5종 노출.
 *
 * code 별 카피:
 *   network  : 연결 불안정 — 재시도 가능
 *   timeout  : 응답 지연 — 재시도 가능
 *   server   : 서버 오류 — 재시도 가능
 *   auth     : JWT 만료 — 재시도 불가 (재로그인)
 *   expired  : 세션 TTL 만료 — 재시도 불가 (리포트로 자동 이동)
 *
 * a11y: role="alert" + aria-live="polite".
 * 페르소나 B 톤: 해요체. 이모지/ㅋ/ㅎ/~ 0건.
 */

"use client";

import type { SiaErrorCode } from "@/lib/api/sia";

interface SiaErrorBannerProps {
  code: SiaErrorCode;
  onRetry: () => void;
}

const MESSAGES: Record<SiaErrorCode, string> = {
  network: "연결이 끊겼어요. 다시 시도해주세요.",
  timeout: "응답이 늦어지고 있어요. 다시 시도해주세요.",
  server: "잠시 문제가 있었어요. 다시 시도해주세요.",
  auth: "로그인이 만료됐어요. 다시 로그인해주세요.",
  expired: "대화 시간이 끝났어요. 마무리해드릴게요.",
};

const RETRY_ALLOWED: Record<SiaErrorCode, boolean> = {
  network: true,
  timeout: true,
  server: true,
  auth: false,
  expired: false,
};

export function SiaErrorBanner({ code, onRetry }: SiaErrorBannerProps) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className="animate-fade-in"
      style={{
        borderTop: "1px solid var(--color-danger)",
        background: "var(--color-paper)",
        padding: "14px 20px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        flexWrap: "wrap",
      }}
    >
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 13,
          lineHeight: 1.5,
          letterSpacing: "-0.005em",
          color: "var(--color-ink)",
          flex: 1,
          minWidth: 200,
        }}
      >
        {MESSAGES[code]}
      </p>
      {RETRY_ALLOWED[code] && (
        <button
          type="button"
          onClick={onRetry}
          className="font-sans"
          style={{
            height: 36,
            padding: "0 16px",
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.3px",
            color: "var(--color-paper)",
            background: "var(--color-ink)",
            border: "none",
            borderRadius: 0,
            cursor: "pointer",
          }}
        >
          다시
        </button>
      )}
    </div>
  );
}
