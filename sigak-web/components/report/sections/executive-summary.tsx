// 핵심 요약 섹션 (항상 공개)
// 매거진 풀아웃 스타일 — 큰 세리프 + 인용부호 느낌

interface ExecutiveSummaryContent {
  summary: string;
}

interface ExecutiveSummaryProps {
  content: ExecutiveSummaryContent;
  locked: boolean;
}

// 핵심 요약 — 에디토리얼 풀아웃 스타일
export function ExecutiveSummary({ content }: ExecutiveSummaryProps) {
  return (
    <section className="py-12 border-b border-[var(--color-border)]">
      {/* 대형 따옴표 장식 */}
      <span className="block text-6xl font-serif leading-none text-[var(--color-border)] select-none mb-2">
        &ldquo;
      </span>
      {/* 요약 텍스트 */}
      <p className="text-xl md:text-2xl leading-relaxed font-serif pl-1">
        {content.summary}
      </p>
    </section>
  );
}
