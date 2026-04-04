"use client";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
}

// 공통 버튼 컴포넌트
export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base = "inline-flex items-center justify-center font-medium transition-colors";
  const variants = {
    primary: "bg-[var(--color-fg)] text-[var(--color-bg)] hover:opacity-90",
    secondary:
      "border border-[var(--color-fg)] text-[var(--color-fg)] hover:bg-[var(--color-fg)] hover:text-[var(--color-bg)]",
    ghost: "text-[var(--color-fg)] hover:opacity-70",
  };
  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-5 py-2.5 text-base",
    lg: "px-8 py-3.5 text-lg",
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
