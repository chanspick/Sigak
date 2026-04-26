// 리포트 커버 섹션 (항상 공개)
// 에디토리얼 매거진 스타일 — 첫인상이 리포트 전체 만족도를 결정

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

// 리포트 상단 커버 영역
// Phase B-5 (PI-REVIVE 2026-04-26): "Edition standard" 태그 숨김.
// standard tier 는 BETA 기본값이라 라벨 노출이 의미 없음. creator/wedding 등
// 차별화 tier 일 때만 노출.
export function Cover({ content }: CoverProps) {
  const tierLabels: Record<string, string> = {
    basic: "Basic Diagnostic",
    creator: "Creator Edition",
    wedding: "Wedding Edition",
  };
  const showEdition = !!tierLabels[content.tier]; // standard / 미정의 tier 는 미노출

  return (
    <section className="pt-16 pb-12 border-b border-[var(--color-border)]">
      {/* 서비스 로고 마크 */}
      <div className="flex items-center gap-2 mb-10">
        <div className="w-6 h-6 bg-[var(--color-fg)] rounded-full" />
        <span className="text-xs font-semibold tracking-[5px] uppercase">
          SIGAK
        </span>
      </div>

      {/* 메인 타이틀 — 큰 세리프 */}
      <h1 className="text-4xl md:text-5xl font-bold font-serif leading-tight mb-6">
        {content.title}
      </h1>

      {/* 구분선 */}
      <div className="w-12 h-px bg-[var(--color-fg)] mb-6" />

      {/* 메타 정보 — 수직 스택 */}
      <div className="flex flex-col gap-1.5 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-muted)] w-16">Client</span>
          <span className="font-medium">{content.user_name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-muted)] w-16">Date</span>
          <span>{content.date}</span>
        </div>
        {showEdition && (
          <div className="flex items-center gap-2">
            <span className="text-[var(--color-muted)] w-16">Edition</span>
            <span className="text-xs tracking-[2px] uppercase font-semibold">
              {tierLabels[content.tier]}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
