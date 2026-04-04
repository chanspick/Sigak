// 구분선 컴포넌트
export function Divider({ className = "" }: { className?: string }) {
  return <hr className={`border-[var(--color-border)] ${className}`} />;
}
