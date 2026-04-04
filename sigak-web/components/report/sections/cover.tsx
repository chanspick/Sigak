// 리포트 커버 섹션 (항상 공개)

interface CoverContent {
  title: string;
  user_name: string;
  date: string;
  tier: string;
}

interface CoverProps {
  content: CoverContent;
  locked: boolean;
}

// 리포트 상단 커버 영역 - 타이틀, 유저명, 날짜, 티어 표시
export function Cover({ content }: CoverProps) {
  // 티어 라벨 매핑
  const tierLabels: Record<string, string> = {
    basic: "Basic",
    creator: "Creator",
    wedding: "Wedding",
  };

  return (
    <section className="py-12 border-b border-[var(--color-border)]">
      {/* 서비스 라벨 */}
      <p className="text-xs font-semibold tracking-[4px] uppercase text-[var(--color-muted)] mb-4">
        SIGAK REPORT
      </p>
      {/* 리포트 타이틀 */}
      <h1 className="text-3xl font-bold mb-2 font-serif">
        {content.title}
      </h1>
      {/* 유저명 + 날짜 */}
      <div className="flex items-center gap-3 mt-4 text-sm text-[var(--color-muted)]">
        <span className="font-medium text-[var(--color-fg)]">
          {content.user_name}
        </span>
        <span className="w-px h-3 bg-[var(--color-border)]" />
        <span>{content.date}</span>
        <span className="w-px h-3 bg-[var(--color-border)]" />
        <span className="text-xs tracking-[1px] uppercase">
          {tierLabels[content.tier] ?? content.tier}
        </span>
      </div>
    </section>
  );
}
