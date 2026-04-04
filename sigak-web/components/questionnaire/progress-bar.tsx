// 진행률 표시 컴포넌트

interface ProgressBarProps {
  current: number;
  total: number;
}

/** 단계 진행 표시기 (스텝 닷 + 숫자) */
export function ProgressBar({ current, total }: ProgressBarProps) {
  return (
    <div className="flex items-center gap-3 mb-6">
      {/* 스텝 닷 */}
      <div className="flex gap-2">
        {Array.from({ length: total }, (_, i) => {
          const step = i + 1;
          const isActive = step === current;
          const isDone = step < current;
          return (
            <div
              key={step}
              className={
                isActive
                  ? "w-2.5 h-2.5 rounded-full bg-[var(--color-fg)] transition-colors duration-200"
                  : isDone
                    ? "w-2.5 h-2.5 rounded-full bg-[var(--color-fg)] opacity-30 transition-colors duration-200"
                    : "w-2.5 h-2.5 rounded-full border border-black/20 transition-colors duration-200"
              }
            />
          );
        })}
      </div>
      {/* 숫자 표시 */}
      <span className="text-[11px] font-semibold tracking-[1px] opacity-40">
        {current}/{total}
      </span>
    </div>
  );
}
