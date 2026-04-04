// 통계 카드 컴포넌트 — 가설 검증 지표 뷰에서 사용

interface StatCardProps {
  label: string;
  value: number;
  unit: string;
  target?: string;
  alert?: boolean;
}

// 개별 지표를 표시하는 카드
export function StatCard({ label, value, unit, target, alert }: StatCardProps) {
  // 소수점이 있는 숫자는 1자리까지 표시
  const displayValue =
    typeof value === "number" && value % 1 !== 0
      ? value.toFixed(1)
      : value;

  return (
    <div className="px-[22px] py-5 border-r border-black/[0.08] last:border-r-0">
      {/* 라벨: 10px, 대문자, 투명도 */}
      <p className="text-[10px] font-semibold tracking-[1.5px] opacity-30 mb-2.5">
        {label}
      </p>
      {/* 값: serif 폰트, 큰 숫자 (clamp 24-32px) */}
      <p
        className={`font-[family-name:var(--font-serif)] text-[clamp(24px,3vw,32px)] font-light leading-none ${
          alert ? "text-[var(--color-danger)]" : "text-[var(--color-fg)]"
        }`}
      >
        {displayValue}
        {/* 단위: sans 폰트, 12px, 투명도 */}
        <span className="font-[family-name:var(--font-sans)] text-xs font-normal opacity-35 ml-1">
          {unit}
        </span>
      </p>
      {/* 목표: optional 텍스트 */}
      {target && (
        <p className="text-[10px] opacity-30 mt-1.5">{target}</p>
      )}
    </div>
  );
}
