// SIGAK MVP v1.2 — PrimaryButton
// Full-width INK CTA. 54px 높이, 우측 화살표(sage).
// disabled 상태: 반투명 ink 배경 + mute_2 텍스트.
// Source: refactor/home-screen.jsx HomeCTA.
"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

interface PrimaryButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  children: ReactNode;
  /** 우측 sage 화살표 표시. ready 상태에서만. 기본 true. */
  showArrow?: boolean;
  /** 비활성 텍스트 override. disabled 상태에서 children 대신 표시. */
  disabledLabel?: ReactNode;
}

export function PrimaryButton({
  children,
  showArrow = true,
  disabledLabel,
  disabled,
  className,
  style,
  ...rest
}: PrimaryButtonProps) {
  const ready = !disabled;
  return (
    <button
      {...rest}
      disabled={disabled}
      className={className}
      style={{
        width: "100%",
        height: 54,
        background: ready ? "var(--color-ink)" : "rgba(15,15,14,0.06)",
        color: ready ? "var(--color-paper)" : "var(--color-mute-2)",
        border: "none",
        borderRadius: 12,
        fontFamily: "var(--font-sans)",
        fontSize: 14,
        fontWeight: 500,
        letterSpacing: "-0.005em",
        cursor: ready ? "pointer" : "default",
        display: "flex",
        alignItems: "center",
        justifyContent: showArrow && ready ? "space-between" : "center",
        padding: "0 22px",
        ...style,
      }}
    >
      <span>{ready ? children : (disabledLabel ?? children)}</span>
      {ready && showArrow && (
        <span
          aria-hidden
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 18,
            color: "var(--color-sage)",
            lineHeight: 1,
          }}
        >
          →
        </span>
      )}
    </button>
  );
}
