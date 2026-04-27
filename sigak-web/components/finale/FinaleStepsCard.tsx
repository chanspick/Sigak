// FinaleStepsCard — SPEC-PI-FINALE-001 Card 2 (4-step).
//
// PI 레포트 끝, 공유하기 위에 위치. 마케터 redesign 1815 톤 정합.
// 4 step: 관찰 / 해석 / 진단 / 다음 한 걸음 — mono 넘버 (01~04) + ember 액센트.
//
// data 가 null/undefined 면 렌더 안 함 (graceful — 레거시 레포트 백필 전).

import type { SiaFinale } from "@/lib/types/report";

interface FinaleStepsCardProps {
  finale: SiaFinale | null | undefined;
}

const STEPS: Array<{
  num: string;
  label: string;
  field: keyof Pick<
    SiaFinale,
    | "step_1_observation"
    | "step_2_interpretation"
    | "step_3_diagnosis"
    | "step_4_closing"
  >;
}> = [
  { num: "01", label: "관찰", field: "step_1_observation" },
  { num: "02", label: "해석", field: "step_2_interpretation" },
  { num: "03", label: "진단", field: "step_3_diagnosis" },
  { num: "04", label: "다음 한 걸음", field: "step_4_closing" },
];

export function FinaleStepsCard({ finale }: FinaleStepsCardProps) {
  if (!finale) return null;

  // 4 step 중 하나라도 비어있으면 (스키마 위반 방어) 렌더 안 함
  const hasAllSteps = STEPS.every((s) => {
    const v = finale[s.field];
    return typeof v === "string" && v.trim().length > 0;
  });
  if (!hasAllSteps) return null;

  return (
    <section
      className="my-12"
      aria-label="Sia 의 자세한 분석"
      data-testid="finale-steps-card"
    >
      {/* 디저트 호흡 — section divider */}
      <div className="flex items-center justify-center gap-3 mb-10">
        <span className="block h-px w-12 bg-[var(--color-line)]" />
        <span
          aria-hidden
          className="block w-1.5 h-1.5 rounded-full"
          style={{ background: "var(--color-ember)" }}
        />
        <span className="block h-px w-12 bg-[var(--color-line)]" />
      </div>

      <div
        className="rounded-2xl p-7"
        style={{
          background: "var(--color-bg-soft)",
          border: "1px solid var(--color-rule)",
        }}
      >
        {/* 카드 헤더 */}
        <h2
          className="font-sans uppercase mb-6"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "3px",
            color: "var(--color-fog)",
          }}
        >
          Sia 의 자세한 분석
        </h2>

        {/* 4 steps */}
        <div className="flex flex-col gap-7">
          {STEPS.map((step, idx) => (
            <div key={step.num} className="min-w-0 break-keep">
              {/* 헤딩 — mono 넘버 + 한국어 라벨 + ember 액센트 라인 */}
              <div className="flex items-baseline gap-3 mb-2">
                <span
                  className="font-mono"
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: "0.08em",
                    color: "var(--color-ember)",
                  }}
                >
                  {step.num}
                </span>
                <h3
                  className="font-serif"
                  style={{
                    fontSize: 16,
                    fontWeight: 500,
                    letterSpacing: "-0.012em",
                    color: "var(--color-ink)",
                  }}
                >
                  {step.label}
                </h3>
                <span
                  aria-hidden
                  className="flex-1 h-px"
                  style={{
                    background: "var(--color-line)",
                    marginLeft: 4,
                  }}
                />
              </div>

              {/* 본문 */}
              <p
                className="font-sans"
                style={{
                  fontSize: 14,
                  lineHeight: 1.75,
                  letterSpacing: "-0.005em",
                  color: "var(--color-ink-body)",
                }}
              >
                {finale[step.field]}
              </p>

              {/* step 사이 미세 spacer — 마지막 step 은 생략 */}
              {idx < STEPS.length - 1 && (
                <span aria-hidden className="block h-px mt-7" />
              )}
            </div>
          ))}
        </div>

        {/* 시그니처 — sia */}
        <div className="mt-8 text-right">
          <span
            className="font-serif"
            style={{
              fontSize: 12,
              letterSpacing: "0.04em",
              color: "var(--color-fog)",
            }}
          >
            — sia
          </span>
        </div>
      </div>
    </section>
  );
}
