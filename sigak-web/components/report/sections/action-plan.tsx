// 실행 가이드 섹션 (full 잠금)
// 블러 시: category + priority 선명, 추천 내용 블러
// 공개 시: 전체 items with recommendations 표시

interface ActionItem {
  category: string;
  priority: string;
  recommendations: string[];
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

// 실행 가이드 - 카테고리별 우선순위와 추천 항목 표시
export function ActionPlan({ content, locked }: ActionPlanProps) {
  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-xs font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-6">
        ACTION PLAN
      </h2>

      {/* 카테고리 + 우선순위 태그 - 항상 선명 (블러 위) */}
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

      {/* 상세 추천 내용 - 잠금 시 블러 처리 */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          <div className="flex flex-col gap-6">
            {content.items.map((item) => (
              <div key={item.category}>
                {/* 카테고리 헤더 */}
                <h3 className="text-sm font-bold mb-2">
                  {item.category}
                </h3>
                {/* 추천 리스트 */}
                <ul className="flex flex-col gap-1.5">
                  {item.recommendations.map((rec) => (
                    <li
                      key={rec}
                      className="flex items-start gap-2 text-sm leading-relaxed"
                    >
                      <span className="w-1 h-1 rounded-full bg-[var(--color-fg)] mt-2 shrink-0" />
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* 블러 오버레이 - 추천 내용만 덮음 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out" />
          )}
        </div>
      </div>
    </section>
  );
}
