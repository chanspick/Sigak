"use client";

// Yes/No 토글 선택 컴포넌트

interface YesNoSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export function YesNoSelector({ value, onChange }: YesNoSelectorProps) {
  return (
    <div className="flex gap-2">
      {[
        { val: "yes", label: "네" },
        { val: "no", label: "아니오" },
      ].map(({ val, label }) => {
        const isActive = value === val;
        return (
          <button
            key={val}
            type="button"
            onClick={() => onChange(val === value ? "" : val)}
            className={[
              "flex-1 py-2.5 text-[13px] border transition-all duration-150 select-none",
              isActive
                ? "border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)]"
                : "border-black/[0.12] text-[var(--color-fg)] hover:border-black/30",
            ].join(" ")}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
