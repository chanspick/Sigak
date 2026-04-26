"use client";

// 리포트 페이지 전용 네비게이션 바
// Phase B-6 (PI-REVIVE 2026-04-26): 옛 PI v3 시절 nav (60px, SIGAK + REPORT
// 라벨, 오른쪽 OVERVIEW/내리포트/벨) → 일반 TopBar 시각 (52px / 중앙 SIGAK
// 워드마크) 와 정합. 차이: 우측에 보조 링크 + 알림 벨 유지 (기능 보존).

import { useState, useEffect } from "react";
import Link from "next/link";
import { NotificationBell } from "@/components/notification/notification-bell";

interface ReportNavProps {
  /** 오른쪽에 표시할 보조 링크 (예: OVERVIEW) */
  rightLink?: { href: string; label: string };
}

export function ReportNav({ rightLink }: ReportNavProps) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem("sigak_user_id"));
  }, []);

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
      {/* Center: SIGAK wordmark — TopBar 와 동일 스타일 */}
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

      {/* Right: rightLink (옵션) + 내 리포트 + 알림 벨 */}
      <div
        style={{
          position: "absolute",
          right: 12,
          top: 0,
          height: 52,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        {rightLink && (
          <Link
            href={rightLink.href}
            className="font-sans"
            style={{
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: "1px",
              opacity: 0.5,
              color: "var(--color-paper)",
              textDecoration: "none",
            }}
          >
            {rightLink.label}
          </Link>
        )}
        {isLoggedIn && (
          <Link
            href="/my"
            className="font-sans"
            style={{
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: "1px",
              opacity: 0.5,
              color: "var(--color-paper)",
              textDecoration: "none",
            }}
          >
            내 리포트
          </Link>
        )}
        {isLoggedIn && <NotificationBell />}
      </div>
    </nav>
  );
}
