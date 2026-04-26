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
  AspirationRecommendation,
  PhotoPair,
} from "@/lib/types/aspiration";
import { PrimaryButton, TopBar, SigakLoading } from "@/components/ui/sigak";
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
    // Phase B-8 (2026-04-27): 빈 div → SigakLoading (redesign/로딩_1815.html 통일)
    return <SigakLoading message="결과를 불러오는 중이에요." hint="잠시만 기다려 주세요" />;
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
          {analysis.hook_line && (
            <p
              className="font-sans"
              style={{
                margin: "12px 0 0",
                fontSize: 13,
                lineHeight: 1.55,
                letterSpacing: "-0.005em",
                color: "var(--color-mute)",
              }}
            >
              {analysis.hook_line}
            </p>
          )}
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
                <PairCard
                  key={i}
                  pair={pair}
                  highlighted={analysis.best_fit_pair_index === i}
                />
              ))}
            </div>
          </section>
        )}

        {analysis.recommendation && (
          <RecommendationSection rec={analysis.recommendation} />
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

function PairCard({
  pair,
  highlighted,
}: {
  pair: PhotoPair;
  highlighted?: boolean;
}) {
  // v2 — pair_comment (Sonnet cross-analysis 페어 단위 비교 한 줄) 만 노출.
  // 기존 user_sia_comment / target_sia_comment 는 v1.5 호환 default "" 라
  // UI 사용 X. v2 응답에서 pair_comment 가 채워짐.
  const pairText = pair.pair_comment ?? "";
  return (
    <article
      style={
        highlighted
          ? {
              padding: 8,
              background: "var(--color-bubble-ai)",
            }
          : undefined
      }
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
        }}
      >
        <PairHalf label="본인" imageUrl={pair.user_photo_url} />
        <PairHalf label="추구미" imageUrl={pair.target_photo_url} />
      </div>
      {pairText && (
        <p
          className="font-sans"
          style={{
            margin: "12px 0 0",
            fontSize: 13,
            lineHeight: 1.6,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          {pairText}
        </p>
      )}
    </article>
  );
}

function PairHalf({
  label,
  imageUrl,
}: {
  label: string;
  imageUrl: string;
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
    </div>
  );
}

// v2 — 추구미 이동 권장 (트렌드 spirit narrative 안에 흡수). Verdict v2
// recommendation 패턴 차용. 트렌드 카드 별도 노출 없음.
function RecommendationSection({ rec }: { rec: AspirationRecommendation }) {
  return (
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
        이동 방향
      </h2>
      <div
        style={{
          padding: "20px 22px",
          background: "rgba(0, 0, 0, 0.04)",
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {rec.style_direction && (
          <p
            className="font-serif"
            style={{
              margin: 0,
              fontSize: 15,
              lineHeight: 1.7,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
            }}
          >
            {rec.style_direction}
          </p>
        )}
        {rec.next_action && (
          <p
            className="font-sans"
            style={{
              margin: 0,
              fontSize: 13,
              lineHeight: 1.65,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
            }}
          >
            {rec.next_action}
          </p>
        )}
        {rec.why && (
          <p
            className="font-sans"
            style={{
              margin: 0,
              fontSize: 12,
              lineHeight: 1.6,
              letterSpacing: "0",
              color: "var(--color-mute)",
            }}
          >
            {rec.why}
          </p>
        )}
      </div>
    </section>
  );
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
