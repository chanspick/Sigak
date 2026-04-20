// SIGAK MVP v1.2 (Rebrand) — TopBar
//
// 검정 52px 바 + 중앙 letterspaced "SIGAK" 워드마크.
// 필요한 화면에서만 back chevron 노출:
//   - backTarget="/" → router.push(target)
//   - onBack={() => ...} → 커스텀 콜백
//   - 둘 다 안 주면 chevron 안 보임 (루트/터미널 화면용)
//
// SIGAK 중앙 정렬은 chevron 유무와 무관하게 유지 (absolute positioning).
"use client";

import { useRouter } from "next/navigation";

interface TopBarProps {
  /** 지정 시 왼쪽에 back chevron 렌더. 클릭 → router.push. */
  backTarget?: string;
  /** 지정 시 왼쪽에 back chevron 렌더. 클릭 → 콜백. backTarget보다 우선. */
  onBack?: () => void;

  // 하위 호환 무시 props (레거시 호출부 깨지지 않도록)
  variant?: string;
  tokens?: number;
  stepLabel?: string;
  hideTokens?: boolean;
}

export function TopBar({ backTarget, onBack }: TopBarProps = {}) {
  const router = useRouter();
  const showBack = onBack != null || backTarget != null;

  function handleBack() {
    if (onBack) onBack();
    else if (backTarget) router.push(backTarget);
  }

  return (
    <nav
      style={{
        position: "relative",
        height: 52,
        background: "var(--color-ink)",
        color: "var(--color-paper)",
        flexShrink: 0,
      }}
    >
      {/* Left: back chevron (absolute) */}
      {showBack && (
        <button
          type="button"
          onClick={handleBack}
          aria-label="뒤로"
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 52,
            height: 52,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "transparent",
            border: "none",
            padding: 0,
            cursor: "pointer",
          }}
        >
          <svg width="10" height="16" viewBox="0 0 10 16" aria-hidden>
            <path
              d="M8 1L1 8l7 7"
              stroke="var(--color-paper)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
              opacity="0.85"
            />
          </svg>
        </button>
      )}

      {/* Center: SIGAK wordmark (always centered) */}
      <div
        style={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span
          className="font-sans"
          style={{
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "6px",
            color: "var(--color-paper)",
          }}
        >
          SIGAK
        </span>
      </div>
    </nav>
  );
}
