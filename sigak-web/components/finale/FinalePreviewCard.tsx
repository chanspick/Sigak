// FinalePreviewCard — SPEC-PI-FINALE-001 Card 1 (preview).
//
// /vision 탭 (홈 시각 탭) 카드 — 안내 텍스트 + "내 레포트 보기" 버튼 자리를
// 대체. headline + lead_paragraph 2~3줄 truncate + "— sia" 시그.
// 카드 전체 클릭 영역 → /report/{id}/note (Card 1 hero hero 페이지).

"use client";

import Link from "next/link";

interface FinalePreviewCardProps {
  reportId: string;
  headline: string;
  leadPreview: string;
}

export function FinalePreviewCard({
  reportId,
  headline,
  leadPreview,
}: FinalePreviewCardProps) {
  return (
    <Link
      href={`/report/${encodeURIComponent(reportId)}/note`}
      aria-label="시각 비밀 레포트 — 자세히 보기"
      className="block rounded-[14px] no-underline transition-all duration-200 hover:opacity-95"
      style={{
        background: "var(--color-bg-soft)",
        border: "1px solid var(--color-rule)",
        padding: "32px 28px",
        textAlign: "left",
        color: "var(--color-ink)",
      }}
      data-testid="finale-preview-card"
    >
      {/* 카드 라벨 */}
      <div
        className="font-sans uppercase mb-4"
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.18em",
          color: "var(--color-fog)",
        }}
      >
        시각 비밀 레포트
      </div>

      {/* Headline — serif 큰 글씨 (시그니처 한 줄) */}
      <h3
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 19,
          fontWeight: 500,
          letterSpacing: "-0.018em",
          lineHeight: 1.45,
          color: "var(--color-ink)",
          wordBreak: "keep-all",
          marginBottom: 12,
        }}
      >
        {headline}
      </h3>

      {/* Lead preview — 2~3줄 truncate (CSS line-clamp 3) */}
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 13.5,
          lineHeight: 1.7,
          letterSpacing: "-0.005em",
          color: "var(--color-ink-body)",
          wordBreak: "keep-all",
          // line-clamp 3 — 2~3줄 잘림
          display: "-webkit-box",
          WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical" as const,
          overflow: "hidden",
        }}
      >
        {leadPreview}
      </p>

      {/* 푸터 — 시그 + arrow */}
      <div
        style={{
          marginTop: 18,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          className="font-serif"
          style={{
            fontSize: 11.5,
            letterSpacing: "0.04em",
            color: "var(--color-fog)",
          }}
        >
          — sia
        </span>
        <span
          aria-hidden
          style={{
            fontSize: 13,
            color: "var(--color-ember)",
            fontWeight: 500,
          }}
        >
          자세히 보기 →
        </span>
      </div>
    </Link>
  );
}
