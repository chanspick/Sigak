// 실행 가이드 섹션 (full 잠금)
// Fix #13: CumulativeProgressBar 제거, 한국어 우선순위 배지
// Fix #16: 영문 존 이름 → 한국어 매핑
// Fix #17: delta 수치, axis+delta 텍스트 완전 제거

interface ActionRecommendation {
  action: string;
  expected_effect: string;
  beginner_tip?: string;
}

interface ActionItem {
  category: string;
  priority: string;
  recommendations: ActionRecommendation[];
}

interface ActionPlanContent {
  items: ActionItem[];
}

interface ActionPlanProps {
  content: ActionPlanContent;
  locked: boolean;
}

// 존 이름 영문 → 한국어 매핑 (Fix #16)
const ZONE_KR: Record<string, string> = {
  overall: "전체 베이스",
  cheek_apple: "볼 사과존",
  lip: "입술",
  under_eye: "눈 밑",
  jawline: "턱선",
  brow: "눈썹",
  eye_crease: "눈두덩",
  nose_bridge: "콧대",
};

// 우선순위 배지 스타일 — 한국어 라벨 기반 (Fix #13)
function getPriorityBadge(priority: string): {
  className: string;
  label: string;
} {
  if (priority === "핵심 포인트" || priority === "HIGH") {
    return {
      className:
        "bg-[var(--color-fg)] text-[var(--color-bg)] px-2.5 py-0.5 text-[11px] font-semibold rounded-full",
      label: "핵심 포인트",
    };
  }
  if (priority === "추가하면 좋은 포인트" || priority === "MEDIUM") {
    return {
      className:
        "border border-[var(--color-fg)] text-[var(--color-fg)] px-2.5 py-0.5 text-[11px] font-semibold rounded-full",
      label: "추가하면 좋은 포인트",
    };
  }
  // 보너스 / LOW / 기타
  return {
    className:
      "border border-[var(--color-border)] text-[var(--color-muted)] px-2.5 py-0.5 text-[11px] font-semibold rounded-full",
    label: priority === "LOW" ? "보너스" : priority || "보너스",
  };
}

// 카테고리 이름에 영문 존 이름이 포함되어 있으면 한국어로 변환
function localizeCategory(category: string): string {
  return ZONE_KR[category] ?? category;
}

// 실행 가이드 — 우선순위 배지 + 액션 + 팁
export function ActionPlan({ content, locked }: ActionPlanProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        ACTION PLAN
      </h2>

      {/* 카테고리 + 우선순위 배지 — 항상 선명 (블러 위) */}
      <div className="flex flex-wrap gap-2 mb-6">
        {content.items.map((item) => {
          const badge = getPriorityBadge(item.priority);
          return (
            <span key={item.category} className={badge.className}>
              {localizeCategory(item.category)}
            </span>
          );
        })}
      </div>

      {/* 상세 추천 내용 — 잠금 시 블러 처리 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          <div className="flex flex-col gap-8">
            {content.items.map((item) => {
              const badge = getPriorityBadge(item.priority);
              return (
                <div key={item.category}>
                  {/* 카테고리 헤더 + 우선순위 배지 (Fix #13, #17: delta/axis 제거) */}
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="text-sm font-bold">
                      {localizeCategory(item.category)}
                    </h3>
                    <span className={badge.className}>{badge.label}</span>
                  </div>

                  {/* 추천 리스트 — 액션 + 효과 + 팁만 표시 */}
                  <ul className="flex flex-col gap-3">
                    {item.recommendations.map((rec) => (
                      <li key={rec.action} className="flex flex-col gap-1">
                        <div className="flex items-start gap-2">
                          <span className="w-1 h-1 rounded-full bg-[var(--color-fg)] mt-2 shrink-0" />
                          <div className="flex flex-col gap-0.5">
                            <span className="text-sm leading-relaxed">
                              {rec.action}
                            </span>
                            <span className="text-xs text-[var(--color-muted)] leading-relaxed">
                              {rec.expected_effect}
                            </span>
                            {/* 비기너 팁 (Fix #17: 수치 없이 텍스트만) */}
                            {rec.beginner_tip && (
                              <span className="text-xs text-[var(--color-muted)] leading-relaxed italic">
                                {rec.beginner_tip}
                              </span>
                            )}
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
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
