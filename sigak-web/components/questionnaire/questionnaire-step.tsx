// 질문 렌더러 컴포넌트

import type { InterviewQuestion } from "@/lib/types/dashboard";

interface QuestionnaireStepProps {
  questions: InterviewQuestion[];
  answers: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

/** 인터뷰 질문 목록을 textarea로 렌더링 */
export function QuestionnaireStep({
  questions,
  answers,
  onChange,
}: QuestionnaireStepProps) {
  return (
    <div className="flex flex-col gap-5">
      {questions.map((q) => (
        <div key={q.key}>
          <label className="block text-[11px] font-semibold tracking-[0.5px] opacity-50 mb-1.5">
            {q.label}
          </label>
          <textarea
            className="w-full px-3.5 py-3 text-sm bg-transparent border border-black/[0.12] outline-none transition-[border-color] duration-200 placeholder:opacity-25 focus:border-[var(--color-fg)] resize-none"
            rows={q.rows}
            placeholder={q.placeholder}
            value={answers[q.key] ?? ""}
            onChange={(e) => onChange(q.key, e.target.value)}
          />
        </div>
      ))}
    </div>
  );
}
