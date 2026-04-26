"use client";

// 리포트 페이지 전용 네비게이션 바.
// Phase B-6 (PI-REVIVE 2026-04-26): 옛 PI v3 시절 nav 시각 → TopBar 정합.
// Phase B-6.1 (2026-04-26): 본인 결정 — 우측 OVERVIEW / 내 리포트 /
// NotificationBell 모두 제거. 중앙 SIGAK 워드마크만 (TopBar 와 완전 동일).
// rightLink prop 은 backward compat 위해 유지 (caller 변경 안 해도 무시됨).

import Link from "next/link";

interface ReportNavProps {
  /** Phase B-6.1: 사용 안 함 (backward compat). caller 가 전달해도 무시. */
  rightLink?: { href: string; label: string };
}

export function ReportNav(_props: ReportNavProps = {}) {
  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        height: 52,
        background: "var(--color-ink)",
        color: "var(--color-paper)",
        flexShrink: 0,
      }}
    >
      {/* Center: SIGAK wordmark — TopBar 와 동일 */}
      <Link
        href="/"
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          bottom: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textDecoration: "none",
          color: "var(--color-paper)",
        }}
        aria-label="홈으로"
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
      </Link>
    </nav>
  );
}
