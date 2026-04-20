// SIGAK MVP v1.2 — TopBar (variants)
// 3가지 variant:
//   - "minimal": 토큰 카운터만 (right aligned). Home, Verdict 화면.
//   - "home":    위 + SIGAK 워드마크(center, large). (옵션) Home only.
//   - "result":  왼쪽 back chevron + 오른쪽 토큰 카운터. Result, detail 화면.
//   - "onboarding": 왼쪽 back chevron + 중앙 step 라벨. 온보딩 진행 시.
"use client";

import { useRouter } from "next/navigation";

interface TokenIndicatorProps {
  tokens: number;
}

function TokenIndicator({ tokens }: TokenIndicatorProps) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="relative block h-2.5 w-2.5">
        <span className="absolute inset-0 rounded-full border border-ink" />
        <span className="absolute left-[2.5px] top-[2.5px] h-[5px] w-[5px] rounded-full bg-sage" />
      </span>
      <span className="font-display text-[11px] font-normal tracking-[0.02em] text-ink tabular-nums">
        {tokens}
      </span>
    </div>
  );
}

function BackChevron({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-label="뒤로"
      className="flex h-6 w-6 items-center justify-start border-0 bg-transparent p-0"
    >
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path
          d="M9 2L4 7l5 5"
          stroke="var(--color-ink)"
          strokeWidth="1"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

interface TopBarProps {
  variant?: "minimal" | "home" | "result" | "onboarding";
  tokens?: number;
  /** "onboarding" variant 전용 step 라벨 (e.g. "STEP 01 / 04"). */
  stepLabel?: string;
  /** back chevron 동작. 지정 안 하면 router.back(). */
  onBack?: () => void;
  /** 토큰 카운터 숨김. 기본 false. */
  hideTokens?: boolean;
}

export function TopBar({
  variant = "minimal",
  tokens = 0,
  stepLabel,
  onBack,
  hideTokens = false,
}: TopBarProps) {
  const router = useRouter();
  const handleBack = onBack ?? (() => router.back());

  return (
    <div className="flex items-center px-5 pt-[62px]" style={{ minHeight: 48 }}>
      {/* Left */}
      <div className="flex flex-1 items-center justify-start">
        {(variant === "result" || variant === "onboarding") && (
          <BackChevron onClick={handleBack} />
        )}
      </div>

      {/* Center */}
      <div className="flex flex-1 items-center justify-center">
        {variant === "home" && (
          <span
            className="font-display font-medium text-ink"
            style={{
              fontSize: 22,
              letterSpacing: "0.32em",
              paddingLeft: "0.32em",
              lineHeight: 1,
            }}
          >
            SIGAK
          </span>
        )}
        {variant === "onboarding" && stepLabel && (
          <span
            className="font-display font-medium uppercase text-ink"
            style={{ fontSize: 10, letterSpacing: "0.22em" }}
          >
            {stepLabel}
          </span>
        )}
      </div>

      {/* Right */}
      <div className="flex flex-1 items-center justify-end">
        {!hideTokens && <TokenIndicator tokens={tokens} />}
      </div>
    </div>
  );
}
