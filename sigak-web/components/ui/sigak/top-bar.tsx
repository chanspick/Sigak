// SIGAK MVP v1.2 — TopBar (2026-04-27 마케터 정합 + 홈 통일)
//
// 본인 결정: "상단 뒤로가기 포함된 바를 홈하고 통일시켜야 좋을 것 같아요"
// 이전 ink 검정 52px → paper 베이지 28px padding (홈 HomeTopNav 정합).
//
// 구조:
//   좌측 ← 뒤로 (옵션, backTarget/onBack 있을 때만)
//   중앙 sigak (Noto Serif 15px 500)
//   우측 토큰 pill (옵션, hideTokens=true 면 X)
//
// 모든 페이지 (onboarding/welcome/essentials/complete, tokens/purchase/fail/
// confirmed, aspiration, best-shot, photo-upload, verdict/new HomeScreen 등)
// 자동 정합.
"use client";

import { useRouter } from "next/navigation";

import { useTokenBalance } from "@/hooks/use-token-balance";

interface TopBarProps {
  /** 지정 시 왼쪽에 ← 뒤로 렌더. 클릭 → router.push. */
  backTarget?: string;
  /** 지정 시 왼쪽에 ← 뒤로 렌더. 클릭 → 콜백. backTarget보다 우선. */
  onBack?: () => void;
  /** 우측 토큰 pill 숨김 (auth 전 / 토큰 의미 없는 페이지). default false. */
  hideTokens?: boolean;

  // 하위 호환 무시 props
  variant?: string;
  tokens?: number;
  stepLabel?: string;
}

export function TopBar({
  backTarget,
  onBack,
  hideTokens = false,
}: TopBarProps = {}) {
  const router = useRouter();
  const { balance } = useTokenBalance();
  const showBack = onBack != null || backTarget != null;

  function handleBack() {
    if (onBack) onBack();
    else if (backTarget) router.push(backTarget);
  }

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "var(--color-paper)",
        borderBottom: "1px solid var(--color-line)",
        flexShrink: 0,
      }}
    >
      <div
        style={{
          maxWidth: 480,
          margin: "0 auto",
          padding: "20px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Left — ← 뒤로 (옵션) */}
        <div style={{ flex: 1, display: "flex", alignItems: "center" }}>
          {showBack && (
            <button
              type="button"
              onClick={handleBack}
              aria-label="뒤로"
              className="font-sans"
              style={{
                fontSize: 13.5,
                color: "var(--color-ink)",
                opacity: 0.75,
                fontWeight: 500,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                padding: 0,
                letterSpacing: "-0.005em",
              }}
            >
              ← 뒤로
            </button>
          )}
        </div>

        {/* Center — sigak Noto Serif (홈 정합) */}
        <div
          className="font-serif"
          style={{
            fontSize: 15,
            fontWeight: 500,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
          }}
        >
          sigak
        </div>

        {/* Right — 토큰 pill (옵션) */}
        <div style={{ flex: 1, display: "flex", justifyContent: "flex-end" }}>
          {!hideTokens && (
            <button
              type="button"
              onClick={() => router.push("/tokens/purchase")}
              aria-label="토큰 충전"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 5,
                background: "var(--color-ink)",
                color: "var(--color-paper)",
                borderRadius: 100,
                padding: "5px 12px",
                border: "none",
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                fontWeight: 500,
                letterSpacing: "0.04em",
                cursor: "pointer",
              }}
            >
              <span
                aria-hidden
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "var(--color-danger)",
                }}
              />
              <span className="tabular-nums">
                {balance == null ? "—" : balance.toLocaleString()}
              </span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
