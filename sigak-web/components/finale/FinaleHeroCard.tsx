// FinaleHeroCard — SPEC-PI-FINALE-001 Card 1 (hero).
//
// /report/{id}/note 라우트 hero 컴포넌트. headline 큰 serif + 풀 lead_paragraph
// + "— sia" 시그. 단일 의식 — 디저트 트레이 1장.
//
// "자세한 분석 보기 →" CTA 는 페이지 단에서 별도 렌더 (이 카드는 콘텐츠만).

interface FinaleHeroCardProps {
  headline: string;
  leadParagraph: string;
}

export function FinaleHeroCard({
  headline,
  leadParagraph,
}: FinaleHeroCardProps) {
  return (
    <article
      className="mx-auto"
      style={{
        maxWidth: 480,
        padding: "48px 28px 56px",
        textAlign: "left",
      }}
      data-testid="finale-hero-card"
    >
      {/* 카드 라벨 + ember 액센트 */}
      <div
        className="font-sans uppercase mb-8"
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.22em",
          color: "var(--color-fog)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <span
          aria-hidden
          className="block"
          style={{
            width: 28,
            height: 2,
            background: "var(--color-ember)",
          }}
        />
        Sia 의 마무리
      </div>

      {/* Headline — serif 큰 글씨, 모바일 28~30, 태블릿 36~40 */}
      <h1
        className="font-serif"
        style={{
          margin: 0,
          fontSize: "clamp(26px, 6vw, 36px)",
          fontWeight: 500,
          letterSpacing: "-0.022em",
          lineHeight: 1.32,
          color: "var(--color-ink)",
          wordBreak: "keep-all",
          marginBottom: 28,
        }}
      >
        {headline}
      </h1>

      {/* Lead paragraph — 풀 본문 */}
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 16,
          lineHeight: 1.85,
          letterSpacing: "-0.005em",
          color: "var(--color-ink-body)",
          wordBreak: "keep-all",
          whiteSpace: "pre-wrap",
        }}
      >
        {leadParagraph}
      </p>

      {/* 시그니처 */}
      <div
        style={{
          marginTop: 36,
          textAlign: "right",
        }}
      >
        <span
          className="font-serif"
          style={{
            fontSize: 13,
            letterSpacing: "0.04em",
            color: "var(--color-fog)",
          }}
        >
          — sia
        </span>
      </div>
    </article>
  );
}
