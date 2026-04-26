"use client";

import { forwardRef } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

// 입력 필드 컴포넌트
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label className="text-sm text-[var(--color-muted)]">{label}</label>
        )}
        <input
          ref={ref}
          className={`border border-[var(--color-line)] bg-transparent px-4 py-2.5 text-[var(--color-fg)] placeholder:text-[var(--color-muted)] focus:outline-none focus:border-[var(--color-fg)] transition-colors ${className}`}
          {...props}
        />
        {error && <span className="text-sm text-[var(--color-danger)]">{error}</span>}
      </div>
    );
  },
);
Input.displayName = "Input";
