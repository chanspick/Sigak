/**
 * /aspiration/[id] — 추구미 분석 결과 (Phase J).
 *
 * 진입 경로:
 *   1. /aspiration 에서 분석 완료 후 자동 redirect
 *   2. 직접 URL 진입 (북마크, 공유 — 본인 소유만 200, 타 유저 → 403)
 *
 * 백엔드: GET /api/v2/aspiration/{id} → AspirationAnalysis
 *
 * 렌더 순서:
 *   1. Target header (target_identifier / target_display_name)
 *   2. Gap narrative (큰 메시지)
 *   3. Photo pairs 좌우 병치 (3-5쌍)
 *   4. Sia 종합 메시지
 *   5. CTA (다시 분석 / 홈으로)
 */

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import { ApiError } from "@/lib/api/fetch";
import {
  deleteAspirationAnalysis,
  getAspirationAnalysis,
} from "@/lib/api/aspiration";
import type {
  AspirationAnalysis,
  MatchedTrendView,
  PhotoPair,
} from "@/lib/types/aspiration";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

export default function AspirationResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const analysisId = params.id;

  const [analysis, setAnalysis] = useState<AspirationAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    if (deleting || !analysisId) return;
    const ok = window.confirm(
      "이 추구미 분석을 삭제할까요? 사진 비교와 트렌드 매칭이 모두 사라져요.",
    );
    if (!ok) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deleteAspirationAnalysis(analysisId);
      router.replace("/aspiration");
    } catch (e) {
      setDeleting(false);
      setDeleteError(
        e instanceof Error ? e.message : "삭제에 실패했어요. 잠시 후 다시 시도.",
      );
    }
  }

  useEffect(() => {
    if (!analysisId) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getAspirationAnalysis(analysisId);
        if (!cancelled) setAnalysis(data);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError) {
          if (e.status === 401) {
            router.replace("/auth/login");
            return;
          }
          if (e.status === 404) {
            setError("이 분석을 찾을 수 없어요.");
            return;
          }
          if (e.status === 403) {
            setError("본인 분석만 열람할 수 있어요.");
            return;
          }
          setError(e.message || "조회에 실패했어요.");
          return;
        }
        setError("연결이 잠깐 끊겼어요. 다시 시도해 주세요.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [analysisId, router]);

  if (error) {
    return (
      <SimpleStatePage
        title="안내"
        message={error}
        primary={{ label: "다시 분석하기", href: "/aspiration" }}
        secondary={{ label: "홈으로", href: "/" }}
      />
    );
  }

  if (!analysis) {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-busy
        aria-label="결과를 불러오는 중"
      />
    );
  }

  const targetLabel =
    analysis.target_display_name
    ?? formatTargetIdentifier(analysis.target_type, analysis.target_identifier);

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
    >
      <TopBar backTarget="/" />

      <main style={{ padding: "24px 24px 48px" }}>
        <header style={{ marginBottom: 28 }}>
          <p
            className="font-sans tabular-nums"
            style={{
              margin: 0,
              fontSize: 11,
              letterSpacing: "0.05em",
              color: "var(--color-mute-2)",
            }}
          >
            추구미 분석  ·  {analysis.target_type === "ig" ? "INSTAGRAM" : "PINTEREST"}
          </p>
          <h1
            className="font-serif"
            style={{
              margin: "10px 0 0",
              fontSize: 26,
              fontWeight: 400,
              lineHeight: 1.3,
              letterSpacing: "-0.01em",
            }}
          >
            {targetLabel}
          </h1>
        </header>

        {analysis.gap_narrative && (
          <GapNarrative text={analysis.gap_narrative} />
        )}

        {analysis.photo_pairs.length > 0 && (
          <section style={{ marginTop: 36 }}>
            <h2
              className="font-sans"
              style={{
                margin: "0 0 14px",
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: "0.08em",
                color: "var(--color-mute)",
              }}
            >
              본인  ·  추구미
            </h2>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 24,
              }}
            >
              {analysis.photo_pairs.map((pair, i) => (
                <PairCard key={i} pair={pair} />
              ))}
            </div>
          </section>
        )}

        {analysis.matched_trends && analysis.matched_trends.length > 0 && (
          <MatchedTrendsSection trends={analysis.matched_trends} />
        )}

        {analysis.sia_overall_message && (
          <OverallMessage text={analysis.sia_overall_message} />
        )}

        <section
          style={{
            marginTop: 40,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <Link href="/aspiration" style={{ textDecoration: "none" }}>
            <PrimaryButton type="button">다시 분석하기</PrimaryButton>
          </Link>
          <Link
            href="/"
            className="font-sans"
            style={{
              textAlign: "center",
              fontSize: 13,
              color: "var(--color-mute)",
              textDecoration: "underline",
              padding: "12px 0",
            }}
          >
            홈으로
          </Link>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="font-sans"
            style={{
              marginTop: 8,
              background: "transparent",
              border: "none",
              padding: "8px 0",
              fontSize: 12,
              color: "var(--color-mute-2)",
              textDecoration: "underline",
              cursor: deleting ? "default" : "pointer",
              opacity: deleting ? 0.55 : 1,
            }}
          >
            {deleting ? "삭제 중..." : "이 분석 삭제"}
          </button>
          {deleteError && (
            <p
              className="font-sans"
              role="alert"
              style={{
                margin: 0,
                fontSize: 11,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
                textAlign: "center",
              }}
            >
              {deleteError}
            </p>
          )}
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Sub-views
// ─────────────────────────────────────────────

function GapNarrative({ text }: { text: string }) {
  return (
    <section
      style={{
        padding: "24px 22px",
        background: "var(--color-bubble-ai)",
      }}
    >
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 18,
          lineHeight: 1.65,
          letterSpacing: "-0.01em",
          color: "var(--color-ink)",
        }}
      >
        {text}
      </p>
    </section>
  );
}

function PairCard({ pair }: { pair: PhotoPair }) {
  return (
    <article>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
        }}
      >
        <PairHalf
          label="본인"
          imageUrl={pair.user_photo_url}
          comment={pair.user_sia_comment}
        />
        <PairHalf
          label="추구미"
          imageUrl={pair.target_photo_url}
          comment={pair.target_sia_comment}
        />
      </div>
      {pair.pair_axis_hint && (
        <p
          className="font-sans"
          style={{
            margin: "10px 0 0",
            fontSize: 11,
            letterSpacing: "0.05em",
            color: "var(--color-mute-2)",
            textAlign: "center",
          }}
        >
          {pair.pair_axis_hint}
        </p>
      )}
    </article>
  );
}

function PairHalf({
  label,
  imageUrl,
  comment,
}: {
  label: string;
  imageUrl: string;
  comment: string;
}) {
  return (
    <div>
      <div
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "1 / 1",
          background: "rgba(0,0,0,0.06)",
          overflow: "hidden",
        }}
      >
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={label}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
          />
        ) : (
          <div
            className="font-sans"
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              color: "var(--color-mute-2)",
              letterSpacing: "0.05em",
            }}
          >
            이미지 없음
          </div>
        )}
      </div>
      {comment && (
        <p
          className="font-sans"
          style={{
            margin: "8px 0 0",
            fontSize: 12,
            lineHeight: 1.55,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          {comment}
        </p>
      )}
    </div>
  );
}

// STEP 11 — 추구미 방향 매칭 트렌드 카드 (KB hydrate)
function MatchedTrendsSection({ trends }: { trends: MatchedTrendView[] }) {
  return (
    <section style={{ marginTop: 36 }}>
      <h2
        className="font-sans"
        style={{
          margin: "0 0 4px",
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: "var(--color-mute)",
        }}
      >
        추구미 방향의 트렌드
      </h2>
      <p
        className="font-sans"
        style={{
          margin: "0 0 14px",
          fontSize: 11,
          letterSpacing: "0.02em",
          color: "var(--color-mute-2)",
        }}
      >
        2026 S/S 트렌드 중 추구미 방향과 가까운 항목
      </p>
      <div
        style={{
          display: "flex",
          gap: 10,
          overflowX: "auto",
          paddingBottom: 8,
          WebkitOverflowScrolling: "touch",
          scrollSnapType: "x mandatory",
        }}
      >
        {trends.slice(0, 5).map((t) => (
          <TrendCard key={t.trend_id} trend={t} />
        ))}
      </div>
    </section>
  );
}


function TrendCard({ trend }: { trend: MatchedTrendView }) {
  const [expanded, setExpanded] = useState(false);
  const guide = (trend.detailed_guide || "").trim();
  const truncated = guide.length > 110 ? guide.slice(0, 110).trimEnd() + "…" : guide;
  const displayGuide = expanded ? guide : truncated;

  return (
    <article
      style={{
        flex: "0 0 74%",
        minWidth: 260,
        maxWidth: 320,
        padding: "16px 16px 14px",
        background: "rgba(0, 0, 0, 0.04)",
        scrollSnapAlign: "start",
      }}
    >
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "0.08em",
          color: "var(--color-mute-2)",
          textTransform: "uppercase",
        }}
      >
        {renderCategoryLabel(trend.category)}
      </p>
      <h3
        className="font-serif"
        style={{
          margin: "6px 0 10px",
          fontSize: 15,
          fontWeight: 500,
          letterSpacing: "-0.005em",
          lineHeight: 1.35,
          color: "var(--color-ink)",
        }}
      >
        {trend.title}
      </h3>
      {guide && (
        <p
          className="font-sans"
          style={{
            margin: "0 0 8px",
            fontSize: 12,
            lineHeight: 1.55,
            color: "var(--color-ink)",
            letterSpacing: "-0.003em",
            whiteSpace: "pre-line",
          }}
        >
          {displayGuide}
        </p>
      )}
      {guide.length > 110 && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="font-sans"
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            fontSize: 11,
            color: "var(--color-mute)",
            textDecoration: "underline",
            cursor: "pointer",
            letterSpacing: "0.02em",
          }}
        >
          {expanded ? "접기" : "자세히"}
        </button>
      )}
    </article>
  );
}


function renderCategoryLabel(category: string): string {
  switch (category) {
    case "mood":
      return "무드";
    case "color_palette":
      return "컬러";
    case "silhouette":
      return "실루엣";
    case "styling_method":
      return "스타일링";
    case "makeup_method":
      return "메이크업";
    case "grooming_method":
      return "그루밍";
    default:
      return "트렌드";
  }
}


function OverallMessage({ text }: { text: string }) {
  return (
    <section
      style={{
        marginTop: 36,
        padding: "22px 22px",
        background: "rgba(0, 0, 0, 0.04)",
      }}
    >
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 16,
          lineHeight: 1.7,
          letterSpacing: "-0.005em",
          color: "var(--color-ink)",
        }}
      >
        {text}
      </p>
    </section>
  );
}

function formatTargetIdentifier(type: string, id: string): string {
  if (type === "ig") return `@${id.replace(/^@/, "")}`;
  // Pinterest URL — 짧게 표시
  try {
    const url = new URL(id.startsWith("http") ? id : `https://${id}`);
    const seg = url.pathname.split("/").filter(Boolean);
    return seg.slice(-2).join(" / ") || id;
  } catch {
    return id;
  }
}

function SimpleStatePage({
  title,
  message,
  primary,
  secondary,
}: {
  title: string;
  message: string;
  primary?: { label: string; href: string };
  secondary?: { label: string; href: string };
}) {
  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
    >
      <TopBar backTarget="/" />
      <main
        className="flex-1"
        style={{
          padding: "60px 28px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
        }}
      >
        <h1
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 24,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
          }}
        >
          {title}
        </h1>
        <p
          className="font-sans"
          style={{
            margin: "14px 0 28px",
            fontSize: 13,
            lineHeight: 1.7,
            color: "var(--color-mute)",
            letterSpacing: "-0.005em",
            maxWidth: 320,
          }}
        >
          {message}
        </p>
        {primary && (
          <Link
            href={primary.href}
            style={{ textDecoration: "none", width: "100%", maxWidth: 320 }}
          >
            <PrimaryButton type="button">{primary.label}</PrimaryButton>
          </Link>
        )}
        {secondary && (
          <Link
            href={secondary.href}
            className="font-sans"
            style={{
              marginTop: 14,
              fontSize: 13,
              color: "var(--color-mute)",
              textDecoration: "underline",
            }}
          >
            {secondary.label}
          </Link>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
