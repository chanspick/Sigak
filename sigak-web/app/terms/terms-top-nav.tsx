// SIGAK — Terms page sticky top nav (client boundary)
//
// /terms 페이지는 Server Component (정적 prerender) 이라 onClick 이벤트 핸들러를
// 인라인으로 못 둠. 여기로 분리해서 "use client" 경계 확보.
"use client";

import Link from "next/link";

export function TermsTopNav() {
  function handleBack() {
    if (typeof window === "undefined") return;
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  }

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        height: 52,
        background: "var(--color-ink)",
        color: "var(--color-paper)",
      }}
    >
      {/* Back chevron */}
      <button
        type="button"
        onClick={handleBack}
        aria-label="뒤로"
        style={{
          position: "absolute",
          left: 0,
          top: 0,
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

      {/* Center wordmark */}
      <div
        style={{
          height: 52,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Link
          href="/"
          className="font-sans"
          style={{
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "6px",
            color: "var(--color-paper)",
            textDecoration: "none",
          }}
        >
          SIGAK
        </Link>
      </div>
    </nav>
  );
}
