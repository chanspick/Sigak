"use client";

// 로그인 상태일 때만 표시되는 글로벌 헤더.
// 자체 nav가 있는 페이지에서는 숨김.

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { NotificationBell } from "@/components/notification/notification-bell";

// SiteHeader를 숨길 경로 (자체 nav가 있거나 전용 UI인 페이지)
const HIDDEN_ROUTES = ["/", "/start", "/questionnaire", "/auth", "/report", "/admin"];

function shouldHide(pathname: string): boolean {
  return HIDDEN_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/"),
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    setUserId(localStorage.getItem("sigak_user_id"));
  }, []);

  if (shouldHide(pathname) || !userId) return null;

  const isMyPage = pathname === "/my";

  return (
    <header className="sticky top-0 z-[100] flex items-center justify-between px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)] h-[60px] bg-[var(--color-fg)] text-[var(--color-bg)]">
      {/* 로고 */}
      <Link
        href="/"
        className="text-[12px] font-semibold tracking-[5px] uppercase no-underline text-[var(--color-bg)]"
      >
        SIGAK
      </Link>

      {/* 오른쪽: 내 리포트 + 알림 벨 */}
      <div className="flex items-center gap-4">
        {isMyPage ? (
          <span className="text-[11px] font-medium tracking-[1.5px] uppercase opacity-100 text-[var(--color-bg)]">
            내 리포트
          </span>
        ) : (
          <Link
            href="/my"
            className="text-[11px] font-medium tracking-[1.5px] uppercase opacity-70 transition-opacity duration-200 hover:opacity-100 no-underline text-[var(--color-bg)]"
          >
            내 리포트
          </Link>
        )}
        <NotificationBell />
      </div>
    </header>
  );
}
