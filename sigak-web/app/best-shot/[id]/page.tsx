/**
 * /best-shot/[id] — 선별 결과 (Phase K6 프론트).
 *
 * 진입 경로:
 *   1. /best-shot 에서 run 완료 후 자동 redirect
 *   2. 유저가 직접 URL 진입 (새로고침, 북마크, 공유)
 *
 * status 분기:
 *   - "ready"            → 결과 렌더 (rank 1 hero + 그리드)
 *   - "running"          → 3초 간격 폴링
 *   - "failed"           → 실패 안내 + 새로 시작 CTA (토큰 환불됨)
 *   - "aborted"          → 취소된 세션 안내
 *   - "uploading" / "ready_to_run" → /best-shot 으로 안내
 *
 * 백엔드: GET /api/v2/best-shot/{session_id} → { session: BestShotSession }
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

import { ApiError } from "@/lib/api/fetch";
import { getBestShotSession } from "@/lib/api/best_shot";
import type {
  BestShotSession,
  SelectedPhoto,
} from "@/lib/types/best_shot";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

const POLL_INTERVAL_MS = 3000;

export default function BestShotResultPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [session, setSession] = useState<BestShotSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    async function tick(): Promise<void> {
      try {
        const res = await getBestShotSession(sessionId);
        if (cancelled) return;
        setSession(res.session);
        if (res.session.status === "running") {
          pollTimer.current = setTimeout(tick, POLL_INTERVAL_MS);
        }
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError) {
          if (e.status === 401) {
            router.replace("/auth/login");
            return;
          }
          if (e.status === 404) {
            setError("세션을 찾을 수 없어요.");
            return;
          }
          if (e.status === 403) {
            setError("본인 세션만 열람할 수 있어요.");
            return;
          }
          setError(e.message || "조회에 실패했어요.");
          return;
        }
        setError("연결이 잠깐 끊겼어요. 다시 시도해주세요.");
      }
    }

    void tick();
    return () => {
      cancelled = true;
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [sessionId, router]);

  if (error) {
    return <SimpleStatePage title="안내" message={error} primary={{ label: "홈으로", href: "/" }} />;
  }

  if (!session) {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-busy
        aria-label="결과를 불러오는 중"
      />
    );
  }

  if (session.status === "running") {
    return (
      <SimpleStatePage
        title="고르는 중이에요"
        message="잠시만 기다려주세요. 분석이 끝나면 자동으로 넘어가요."
        busy
      />
    );
  }

  if (session.status === "uploading" || session.status === "ready_to_run") {
    return (
      <SimpleStatePage
        title="업로드가 마무리되지 않은 세션이에요"
        message="처음부터 다시 시작해 주세요."
        primary={{ label: "Best Shot 새로 시작", href: "/best-shot" }}
      />
    );
  }

  if (session.status === "aborted") {
    return (
      <SimpleStatePage
        title="취소된 세션이에요"
        message="새로 시작하시면 다른 사진들로 다시 골라요."
        primary={{ label: "Best Shot 새로 시작", href: "/best-shot" }}
      />
    );
  }

  if (session.status === "failed") {
    return (
      <SimpleStatePage
        title="선별을 끝내지 못했어요"
        message={
          session.failure_reason
          ?? "처리 중 오류가 있었어요. 토큰은 환불됐어요."
        }
        primary={{ label: "다시 시도하기", href: "/best-shot" }}
        secondary={{ label: "홈으로", href: "/" }}
      />
    );
  }

  // status === "ready"
  return <ReadyView session={session} />;
}

// ─────────────────────────────────────────────
//  Ready (selected_photos 렌더)
// ─────────────────────────────────────────────

function ReadyView({ session }: { session: BestShotSession }) {
  const result = session.result;
  const selected: SelectedPhoto[] = result?.selected_photos ?? [];
  const sorted = [...selected].sort((a, b) => a.rank - b.rank);
  const hero = sorted[0];
  const rest = sorted.slice(1);

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
    >
      <TopBar backTarget="/" />

      <main style={{ padding: "24px 24px 48px" }}>
        <header style={{ marginBottom: 24 }}>
          <p
            className="font-sans tabular-nums"
            style={{
              margin: 0,
              fontSize: 11,
              letterSpacing: "0.05em",
              color: "var(--color-mute-2)",
            }}
          >
            BEST SHOT  ·  {sorted.length}장 선별
          </p>
          <h1
            className="font-serif"
            style={{
              margin: "10px 0 0",
              fontSize: 24,
              fontWeight: 700,
              lineHeight: 1.42,
              letterSpacing: "-0.022em",
              color: "var(--color-ink)",
              wordBreak: "keep-all",
            }}
          >
            한 장만 고르라면, 이거예요
            <span style={{ color: "var(--color-danger)" }}>.</span>
          </h1>
        </header>

        {hero && <HeroPhoto photo={hero} />}

        {result?.sia_overall_message && (
          <OverallMessage text={result.sia_overall_message} />
        )}

        {rest.length > 0 && (
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
              그 다음으로 좋은 컷
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: 10,
              }}
            >
              {rest.map((p) => (
                <PhotoCard key={p.photo_id} photo={p} />
              ))}
            </div>
          </section>
        )}

        <section
          style={{
            marginTop: 40,
            display: "flex",
            flexDirection: "column",
            gap: 10,
          }}
        >
          <Link href="/best-shot" style={{ textDecoration: "none" }}>
            <PrimaryButton type="button">다른 사진들로 다시</PrimaryButton>
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
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function HeroPhoto({ photo }: { photo: SelectedPhoto }) {
  return (
    <figure style={{ margin: 0 }}>
      <div
        style={{
          width: "100%",
          aspectRatio: "4 / 5",
          background: "rgba(0,0,0,0.06)",
          overflow: "hidden",
          marginBottom: 14,
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={photo.stored_url}
          alt={`Best shot rank ${photo.rank}`}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      </div>
      <figcaption>
        <p
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 17,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
          }}
        >
          {photo.sia_comment}
        </p>
        <ScoreRow photo={photo} />
      </figcaption>
    </figure>
  );
}

function PhotoCard({ photo }: { photo: SelectedPhoto }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          padding: 0,
          background: "transparent",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
        aria-expanded={expanded}
      >
        <div
          style={{
            position: "relative",
            width: "100%",
            aspectRatio: "1 / 1",
            background: "rgba(0,0,0,0.06)",
            overflow: "hidden",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photo.stored_url}
            alt={`Rank ${photo.rank}`}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
          />
          <span
            className="font-sans tabular-nums"
            style={{
              position: "absolute",
              top: 6,
              left: 6,
              padding: "2px 6px",
              background: "rgba(0,0,0,0.6)",
              color: "#fff",
              fontSize: 10,
              letterSpacing: "0.05em",
            }}
          >
            #{photo.rank}
          </span>
        </div>
      </button>
      {expanded && photo.sia_comment && (
        <p
          className="font-sans"
          style={{
            margin: "8px 0 0",
            fontSize: 12,
            lineHeight: 1.6,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          {photo.sia_comment}
        </p>
      )}
    </div>
  );
}

function ScoreRow({ photo }: { photo: SelectedPhoto }) {
  return (
    <div
      className="font-sans tabular-nums"
      style={{
        marginTop: 10,
        display: "flex",
        gap: 14,
        fontSize: 11,
        color: "var(--color-mute-2)",
        letterSpacing: "0.03em",
      }}
    >
      <span>품질 {(photo.quality_score * 100).toFixed(0)}</span>
      <span>적합도 {(photo.profile_match_score * 100).toFixed(0)}</span>
      <span>흐름 {(photo.trend_match_score * 100).toFixed(0)}</span>
    </div>
  );
}

function OverallMessage({ text }: { text: string }) {
  return (
    <section
      style={{
        marginTop: 28,
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

function SimpleStatePage({
  title,
  message,
  primary,
  secondary,
  busy,
}: {
  title: string;
  message: string;
  primary?: { label: string; href: string };
  secondary?: { label: string; href: string };
  busy?: boolean;
}) {
  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
      aria-busy={busy ? true : undefined}
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
