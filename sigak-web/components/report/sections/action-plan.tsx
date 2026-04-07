// 실행 가이드 섹션 (full 잠금)
// 카테고리별: target_axis + target_delta + 누적 진행 바
// 각 추천: action + metric current→target + expected_effect + 기여율

import {
  CumulativeProgressBar,
  ContributionBadge,
} from "@/components/report/charts/cumulative-progress-bar";

interface ActionRecommendation {
  action: string;
  metric?: string;
  current_value?: number;
  target_value?: number;
  unit?: string;
  expected_effect: string;
  delta_contribution?: number;
}

interface ActionItem {
  category: string;
  priority: string;
  target_axis?: string;
  target_delta?: number;
  recommendations: ActionRecommendation[];
}

interface ActionPlanContent {
  items: ActionItem[];
}

interface ActionPlanProps {
  content: ActionPlanContent;
  locked: boolean;
}

// 우선순위 배지 스타일 매핑
function getPriorityStyle(priority: string): string {
  switch (priority) {
    case "HIGH":
      return "bg-[var(--color-fg)] text-[var(--color-bg)]";
    case "MEDIUM":
      return "border border-[var(--color-fg)] text-[var(--color-fg)]";
    default:
      return "border border-[var(--color-border)] text-[var(--color-muted)]";
  }
}

// 축 이름 매핑 (영문 → 한글)
const AXIS_LABELS: Record<string, string> = {
  maturity: "성숙도",
  intensity: "강도",
  structure: "구조",
  impression: "인상",
};

// 수치 포맷
function formatMetricValue(value: number, unit?: string): string {
  if (value == null) return "";
  const formatted = value >= 1 ? value.toFixed(1) : value.toFixed(3);
  return `${formatted}${unit ?? ""}`;
}

// 실행 가이드 — 정량 메트릭 기반 추천
export function ActionPlan({ content, locked }: ActionPlanProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        ACTION PLAN
      </h2>

      {/* 카테고리 + 우선순위 태그 — 항상 선명 (블러 위) */}
      <div className="flex flex-wrap gap-2 mb-6">
        {content.items.map((item) => (
          <span
            key={item.category}
            className={`px-3 py-1 text-xs font-semibold rounded-full ${getPriorityStyle(item.priority)}`}
          >
            {item.category} {item.priority}
          </span>
        ))}
      </div>

      {/* 상세 추천 내용 — 잠금 시 블러 처리 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          <div className="flex flex-col gap-8">
            {content.items.map((item) => (
              <div key={item.category}>
                {/* 카테고리 헤더 + 대상 축/델타 */}
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="text-sm font-bold">{item.category}</h3>
                  {item.target_axis && item.target_delta !== undefined && (
                    <span className="text-xs tabular-nums text-[var(--color-muted)]">
                      {AXIS_LABELS[item.target_axis] ?? item.target_axis} delta{" "}
                      {(item.target_delta ?? 0).toFixed(2)}
                    </span>
                  )}
                </div>

                {/* 누적 진행 바 — 액션별 기여를 스택으로 시각화 */}
                {item.target_delta !== undefined && item.target_delta > 0 && (
                  <div className="mb-4">
                    <CumulativeProgressBar
                      targetDelta={item.target_delta}
                      segments={item.recommendations
                        .filter((r) => r.delta_contribution && r.delta_contribution > 0)
                        .map((r) => ({
                          label: r.action,
                          contribution: r.delta_contribution!,
                        }))}
                    />
                  </div>
                )}

                {/* 추천 리스트 */}
                <ul className="flex flex-col gap-3">
                  {item.recommendations.map((rec) => (
                    <li key={rec.action} className="flex flex-col gap-1">
                      {/* 액션 + 메트릭 current→target */}
                      <div className="flex items-start gap-2">
                        <span className="w-1 h-1 rounded-full bg-[var(--color-fg)] mt-2 shrink-0" />
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm leading-relaxed">
                            {rec.action}
                            {/* 인라인 메트릭 수치 */}
                            {rec.metric &&
                              rec.current_value !== undefined &&
                              rec.target_value !== undefined && (
                                <span className="ml-1.5 text-xs tabular-nums text-[var(--color-muted)]">
                                  ({formatMetricValue(rec.current_value, rec.unit)}{" "}
                                  &rarr;{" "}
                                  {formatMetricValue(rec.target_value, rec.unit)})
                                </span>
                              )}
                          </span>
                          {/* 예상 효과 + 기여율 배지 */}
                          <span className="text-xs text-[var(--color-muted)] leading-relaxed flex items-center gap-1.5">
                            {rec.expected_effect}
                            {rec.delta_contribution !== undefined &&
                              item.target_delta !== undefined &&
                              item.target_delta > 0 && (
                                <ContributionBadge
                                  contribution={rec.delta_contribution}
                                  targetDelta={item.target_delta}
                                />
                              )}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* 블러 오버레이 — 추천 내용만 덮음 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out" />
          )}
        </div>
      </div>
    </section>
  );
}
