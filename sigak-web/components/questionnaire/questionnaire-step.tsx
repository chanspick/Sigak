// 질문 렌더러 컴포넌트 — text / single_select / multi_select / yes_no 지원

import type { InterviewQuestion } from "@/lib/types/dashboard";
import { ChipSelector } from "@/components/questionnaire/chip-selector";
import { YesNoSelector } from "@/components/questionnaire/yes-no-selector";

interface QuestionnaireStepProps {
  questions: InterviewQuestion[];
  answers: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

/** 질문 목록을 타입에 따라 적절한 입력 컴포넌트로 렌더링 */
export function QuestionnaireStep({
  questions,
  answers,
  onChange,
}: QuestionnaireStepProps) {
  return (
    <div className="flex flex-col gap-6">
      {questions.map((q) => {
        const type = q.type ?? "text";
        const value = answers[q.key] ?? "";

        return (
          <div key={q.key}>
            {/* 라벨 */}
            <label className="block text-[13px] font-semibold tracking-[0.3px] mb-1">
              {q.label}
              {q.required === false && (
                <span className="text-[11px] font-normal opacity-30 ml-1">
                  선택
                </span>
              )}
            </label>

            {/* 보조 설명 */}
            {q.description && (
              <p className="text-[11px] opacity-40 mb-2 leading-relaxed">
                {q.description}
              </p>
            )}

            {/* 입력 컴포넌트 */}
            {type === "text" && (
              <textarea
                className="w-full px-3.5 py-3 text-sm bg-transparent border border-black/[0.12] outline-none transition-[border-color] duration-200 placeholder:opacity-25 focus:border-[var(--color-fg)] resize-none"
                rows={q.rows ?? 2}
                placeholder={q.placeholder}
                value={value}
                onChange={(e) => onChange(q.key, e.target.value)}
              />
            )}

            {type === "single_select" && q.options && (
              <ChipSelector
                options={q.options}
                value={value}
                onChange={(v) => onChange(q.key, v)}
              />
            )}

            {type === "multi_select" && q.options && (
              <ChipSelector
                options={q.options}
                value={value}
                onChange={(v) => onChange(q.key, v)}
                multi
                maxSelect={q.maxSelect}
              />
            )}

            {type === "yes_no" && (
              <YesNoSelector
                value={value}
                onChange={(v) => onChange(q.key, v)}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
