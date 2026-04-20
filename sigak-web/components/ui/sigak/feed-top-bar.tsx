// SIGAK MVP v1.2 — FeedTopBar
//
// 검정 바 52px.
//   - backTarget/onBack 없으면 (/feed 루트): 좌 SIGAK, 우 [balance / profile / +]
//   - backTarget/onBack 있으면 (/profile 등 서브): 좌 back chevron, 중앙 SIGAK,
//     우 [balance / profile / +]
"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";

import { useTokenBalance } from "@/hooks/use-token-balance";
import { getCurrentUser } from "@/lib/auth";

interface FeedTopBarProps {
  /** 왼쪽 back chevron 활성화 (이 경로로 push). */
  backTarget?: string;
  /** 왼쪽 back chevron 활성화 (커스텀 콜백). backTarget보다 우선. */
  onBack?: () => void;
}

export function FeedTopBar({ backTarget, onBack }: FeedTopBarProps = {}) {
  const router = useRouter();
  const { balance } = useTokenBalance();
  const showBack = onBack != null || backTarget != null;

  const profileImage = useMemo(() => {
    if (typeof window === "undefined") return "";
    const u = getCurrentUser();
    return u?.profileImage || "";
  }, []);

  function handleBack() {
    if (onBack) onBack();
    else if (backTarget) router.push(backTarget);
  }

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
        flexShrink: 0,
        padding: "0 20px",
      }}
    >
      {/* Left — back chevron 또는 SIGAK 워드마크 */}
      {showBack ? (
        <button
          type="button"
          onClick={handleBack}
          aria-label="뒤로"
          style={{
            width: 32,
            height: 32,
            padding: 0,
            marginLeft: -8,
            background: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-start",
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
      ) : (
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
      )}

      {/* Center — back 있을 때만 SIGAK 중앙 */}
      {showBack && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: 0,
            height: "100%",
            transform: "translateX(-50%)",
            display: "flex",
            alignItems: "center",
            pointerEvents: "none",
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
      )}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Right — balance + profile + plus */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
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
                color: "var(--color-paper)",
                opacity: 0.7,
              }}
            >
              •
            </span>
          )}
        </button>

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
