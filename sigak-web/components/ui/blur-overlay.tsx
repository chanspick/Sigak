"use client";

interface BlurOverlayProps {
  visible: boolean;
  className?: string;
  children?: React.ReactNode;
}

// 블러 오버레이 컴포넌트 (backdrop-filter: blur(12px))
export function BlurOverlay({ visible, className = "", children }: BlurOverlayProps) {
  return (
    <div
      className={`absolute inset-0 blur-overlay blur-fade-out flex items-center justify-center transition-opacity duration-300 ${visible ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"} ${className}`}
    >
      {children}
    </div>
  );
}
