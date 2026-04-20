// SIGAK MVP v1.2 (Rebrand) — TopBar
//
// 단일 variant. 검정 52px 바 + 중앙 letterspaced "SIGAK" 워드마크.
// variants/토큰 카운터/back chevron 전부 제거. 브랜딩 일관성.
//
// Props는 하위 호환을 위해 받지만 전부 무시 — 호출부 한꺼번에 수정하지 않아도 됨.
"use client";

type LegacyVariant = "minimal" | "home" | "result" | "onboarding";

interface TopBarProps {
  /** 하위 호환 — 무시됨. */
  variant?: LegacyVariant;
  /** 하위 호환 — 무시됨. */
  tokens?: number;
  /** 하위 호환 — 무시됨. */
  stepLabel?: string;
  /** 하위 호환 — 무시됨. */
  onBack?: () => void;
  /** 하위 호환 — 무시됨. */
  hideTokens?: boolean;
}

export function TopBar(_props: TopBarProps = {}) {
  return (
    <nav
      style={{
        height: 52,
        background: "var(--color-ink)",
        color: "var(--color-paper)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
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
    </nav>
  );
}
