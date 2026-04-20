// SIGAK MVP v1.2 — FeedTopBar
//
// 홈/프로필 전용. 검정 바 52px + 좌우 분할:
//   좌: letterspaced SIGAK
//   우: [토큰잔액] [프로필아이콘] [+ 버튼 → /verdict/new]
//
// 온보딩/로그인/결제/verdict/terms 같은 서브 화면은 기존 TopBar(centered SIGAK) 사용.
"use client";

import Image from "next/image";
import { useMemo } from "react";
import { useRouter } from "next/navigation";

import { useTokenBalance } from "@/hooks/use-token-balance";
import { getCurrentUser } from "@/lib/auth";

export function FeedTopBar() {
  const router = useRouter();
  const { balance } = useTokenBalance();

  const profileImage = useMemo(() => {
    if (typeof window === "undefined") return "";
    const u = getCurrentUser();
    return u?.profileImage || "";
  }, []);

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        height: 52,
        background: "var(--color-ink)",
        color: "var(--color-paper)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        flexShrink: 0,
      }}
    >
      {/* Left: SIGAK */}
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

      {/* Right: balance + profile + plus */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {/* Token balance */}
        <span
          className="font-sans tabular-nums"
          style={{
            fontSize: 13,
            fontWeight: 400,
            color: "var(--color-paper)",
            opacity: 0.85,
            letterSpacing: "0.02em",
            minWidth: 18,
            textAlign: "right",
          }}
        >
          {balance ?? 0}
        </span>

        {/* Profile icon → /profile */}
        <button
          type="button"
          onClick={() => router.push("/profile")}
          aria-label="프로필"
          style={{
            width: 28,
            height: 28,
            padding: 0,
            border: "none",
            borderRadius: "50%",
            overflow: "hidden",
            background: "rgba(243, 240, 235, 0.15)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {profileImage ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={profileImage}
              alt="profile"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
          ) : (
            <span
              className="font-sans"
              style={{
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: "1px",
                color: "var(--color-paper)",
                opacity: 0.7,
              }}
            >
              •
            </span>
          )}
        </button>

        {/* Plus icon → /verdict/new */}
        <button
          type="button"
          onClick={() => router.push("/verdict/new")}
          aria-label="새 판정"
          style={{
            width: 28,
            height: 28,
            padding: 0,
            background: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden>
            <path
              d="M10 2v16M2 10h16"
              stroke="var(--color-paper)"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>
    </nav>
  );
}
