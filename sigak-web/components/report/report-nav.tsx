"use client";

// 리포트 페이지 전용 네비게이션 바
// SIGAK REPORT 로고 + 알림 벨 (로그인 시)

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
    <nav className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
      <div className="flex items-center">
        <span className="text-xs font-bold tracking-[5px]">SIGAK</span>
        <span className="ml-3 text-[10px] font-medium tracking-[2.5px] opacity-40">
          REPORT
        </span>
      </div>

      <div className="flex items-center gap-4">
        {rightLink && (
          <Link
            href={rightLink.href}
            className="text-[10px] font-medium tracking-[1px] opacity-50 hover:opacity-80 transition-opacity no-underline text-[var(--color-bg)]"
          >
            {rightLink.label}
          </Link>
        )}
        {isLoggedIn && (
          <Link
            href="/my"
            className="text-[10px] font-medium tracking-[1px] opacity-50 hover:opacity-80 transition-opacity no-underline text-[var(--color-bg)]"
          >
            내 리포트
          </Link>
        )}
        {isLoggedIn && <NotificationBell />}
      </div>
    </nav>
  );
}
