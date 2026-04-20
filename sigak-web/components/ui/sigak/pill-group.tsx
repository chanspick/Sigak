// SIGAK MVP v1.2 — PillGroup
// 선택 chip 그룹. single/multi 두 variant를 별도 props 타입으로 노출.
// 온보딩 step 1~3에서 사용.
"use client";

export interface PillOption {
  value: string;
  label: string;
}

interface PillButtonProps {
  option: PillOption;
  selected: boolean;
  onClick: () => void;
  role: "radio" | "checkbox";
}

function PillButton({ option, selected, onClick, role }: PillButtonProps) {
  return (
    <button
      type="button"
      role={role}
      aria-checked={selected}
      onClick={onClick}
      className="font-sans text-[13px] font-normal transition-[background,color,border] duration-150"
      style={{
        padding: "9px 14px",
        borderRadius: 999,
        letterSpacing: "-0.005em",
        lineHeight: 1,
        border: selected
          ? "0.5px solid var(--color-ink)"
          : "0.5px solid var(--color-line-strong)",
        background: selected ? "var(--color-ink)" : "transparent",
        color: selected ? "var(--color-paper)" : "var(--color-ink)",
        cursor: "pointer",
      }}
    >
      {option.label}
    </button>
  );
}

interface CommonProps {
  /** aria-label용. */
  name: string;
  options: PillOption[];
  className?: string;
}

interface SinglePillGroupProps extends CommonProps {
  value: string | null;
  onChange: (value: string) => void;
}

export function PillGroup({
  name,
  options,
  value,
  onChange,
  className,
}: SinglePillGroupProps) {
  return (
    <div
      className={className}
      role="radiogroup"
      aria-label={name}
      style={{ display: "flex", flexWrap: "wrap", gap: 8 }}
    >
      {options.map((opt) => (
        <PillButton
          key={opt.value}
          option={opt}
          selected={value === opt.value}
          role="radio"
          onClick={() => onChange(opt.value)}
        />
      ))}
    </div>
  );
}

interface MultiPillGroupProps extends CommonProps {
  value: string[];
  onChange: (value: string[]) => void;
  /** 최대 선택 수. 기본 무제한. */
  max?: number;
}

export function PillGroupMulti({
  name,
  options,
  value,
  onChange,
  max,
  className,
}: MultiPillGroupProps) {
  const toggle = (v: string) => {
    if (value.includes(v)) {
      onChange(value.filter((x) => x !== v));
    } else {
      if (max != null && value.length >= max) return;
      onChange([...value, v]);
    }
  };
  return (
    <div
      className={className}
      role="group"
      aria-label={name}
      style={{ display: "flex", flexWrap: "wrap", gap: 8 }}
    >
      {options.map((opt) => (
        <PillButton
          key={opt.value}
          option={opt}
          selected={value.includes(opt.value)}
          role="checkbox"
          onClick={() => toggle(opt.value)}
        />
      ))}
    </div>
  );
}
