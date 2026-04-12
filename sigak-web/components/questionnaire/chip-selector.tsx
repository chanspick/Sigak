"use client";

// 칩 기반 선택 컴포넌트 (single / multi)

import type { SelectOption } from "@/lib/types/dashboard";

interface ChipSelectorProps {
  options: SelectOption[];
  /** 현재 선택값 — 단일: "value", 다중: "a,b,c" (쉼표 구분) */
  value: string;
  onChange: (value: string) => void;
  /** true면 복수 선택 허용 */
  multi?: boolean;
  /** multi 모드 최대 선택 수 */
  maxSelect?: number;
}

export function ChipSelector({
  options,
  value,
  onChange,
  multi = false,
  maxSelect,
}: ChipSelectorProps) {
  const selected = multi
    ? value ? value.split(",").filter(Boolean) : []
    : [value];

  function handleClick(optValue: string) {
    if (multi) {
      const set = new Set(selected);

      if (set.has(optValue)) {
        // "none" 해제 or 일반 해제
        set.delete(optValue);
      } else {
        // "none" 선택 시 다른 것 모두 해제
        if (optValue === "none") {
          set.clear();
          set.add("none");
        } else {
          set.delete("none");
          // maxSelect 제한
          if (maxSelect && set.size >= maxSelect) return;
          set.add(optValue);
        }
      }

      onChange(Array.from(set).join(","));
    } else {
      onChange(optValue === value ? "" : optValue);
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => {
        const isActive = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => handleClick(opt.value)}
            className={[
              "px-3.5 py-2 text-[13px] border transition-all duration-150 select-none",
              isActive
                ? "border-[var(--color-fg)] bg-[var(--color-fg)] text-[var(--color-bg)]"
                : "border-black/[0.12] text-[var(--color-fg)] hover:border-black/30",
            ].join(" ")}
          >
            <span>{opt.label}</span>
            {opt.description && (
              <span className="block text-[10px] opacity-60 mt-0.5">
                {opt.description}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
