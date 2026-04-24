// SIGAK — VerdictV2Screen (2026-04-24)
//
// Sonnet 4.6 cross-analysis 결과 렌더.
// preview: 무료 공개 (hook_line + reason_summary)
// full_content: 10 토큰 unlock 후 공개 (verdict + photo_insights + recommendation)
//
// 페르소나: 정중체 "~습니다" (Sia 친밀체와 분리). 평론 톤 유지.
//
// photo_insights "가장 가까운 결" 뱃지:
//   Sonnet 응답 본문에 "가장 가까운" / "가장 잘 맞는" / "가장 부합" 키워드가
//   포함된 사진에 라벨. v1 GOLD 감각의 프론트 복원 (백엔드 무변경).
//   매치 없으면 라벨 생략.
//
// v2 는 사진 이미지 URL 미저장 (backend 합성 id 만 기록). 텍스트 중심 UI.

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { unlockVerdictV2 } from "@/lib/api/verdicts";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { SiteFooter } from "@/components/sigak/site-footer";
import { FeedTopBar } from "@/components/ui/sigak";
import type {
  FullContent,
  PhotoInsight,
  PhotoUrl,
  PreviewContent,
  Recommendation,
  VerdictNumbers,
  VerdictV2GetResponse,
} from "@/lib/types/verdict_v2";

const UNLOCK_COST = 10;

const BEST_FIT_PATTERNS = [
  /가장\s*가까운/,
  /가장\s*잘\s*맞는/,
  /가장\s*부합/,
  /가장\s*유사/,
];

function detectBestFitIndex(photoInsights: PhotoInsight[]): number | null {
  for (const pi of photoInsights) {
    const blob = `${pi.insight} ${pi.improvement}`;
    if (BEST_FIT_PATTERNS.some((p) => p.test(blob))) {
      return pi.photo_index;
    }
  }
  return null;
}

interface VerdictV2ScreenProps {
  initial: VerdictV2GetResponse;
}

export function VerdictV2Screen({ initial }: VerdictV2ScreenProps) {
  const router = useRouter();
  const { balance, refetch: refetchBalance } = useTokenBalance();

  const [data, setData] = useState<VerdictV2GetResponse>(initial);
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  const unlocked = data.full_unlocked && data.full_content !== null;

  async function handleUnlock() {
    if (unlocking) return;
    if (balance != null && balance < UNLOCK_COST) {
      router.push(
        `/tokens/purchase?intent=unlock_verdict_v2&verdict_id=${encodeURIComponent(data.verdict_id)}`,
      );
      return;
    }
    setUnlocking(true);
    setUnlockError(null);
    try {
      const res = await unlockVerdictV2(data.verdict_id);
      setData({
        ...data,
        full_unlocked: true,
        full_content: res.full_content,
        photo_urls: res.photo_urls ?? data.photo_urls,
      });
      await refetchBalance();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push(
          `/tokens/purchase?intent=unlock_verdict_v2&verdict_id=${encodeURIComponent(data.verdict_id)}`,
        );
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setUnlockError(
        e instanceof Error ? e.message : "해제에 실패했습니다. 다시 시도해주세요.",
      );
    } finally {
      setUnlocking(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <FeedTopBar backTarget="/" />

      {/* 날짜 + 헤드라인 */}
      <section style={{ padding: "40px 28px 24px" }}>
        <DateLabel />
        <h1
          className="font-serif"
          style={{
            fontSize: 36,
            fontWeight: 400,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            margin: "14px 0 0",
            color: "var(--color-ink)",
          }}
        >
          피드 분석.
        </h1>
      </section>

      {/* Preview (항상 공개) */}
      <PreviewSection preview={data.preview} />

      {/* 업로드 사진 썸네일 — 본인 사진이므로 unlock 무관 항상 공개 */}
      {data.photo_urls.length > 0 && (
        <PhotosGrid urls={data.photo_urls} />
      )}

      <Rule />

      {/* Full content (unlock 후) 또는 unlock CTA */}
      {unlocked && data.full_content ? (
        <FullSection
          content={data.full_content}
          photoUrls={data.photo_urls}
        />
      ) : (
        <UnlockSection
          balance={balance}
          busy={unlocking}
          error={unlockError}
          onClick={handleUnlock}
        />
      )}

      <div style={{ height: 40 }} />
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Preview (무료)
// ─────────────────────────────────────────────

function PreviewSection({ preview }: { preview: PreviewContent }) {
  return (
    <section style={{ padding: "4px 28px 32px" }}>
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 22,
          lineHeight: 1.35,
          letterSpacing: "-0.01em",
          color: "var(--color-ink)",
          fontWeight: 400,
        }}
      >
        {preview.hook_line}
      </p>
      <p
        className="font-sans"
        style={{
          marginTop: 20,
          fontSize: 14,
          lineHeight: 1.75,
          letterSpacing: "-0.005em",
          color: "var(--color-ink)",
          opacity: 0.75,
          whiteSpace: "pre-wrap",
        }}
      >
        {preview.reason_summary}
      </p>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Unlock CTA
// ─────────────────────────────────────────────

function UnlockSection({
  balance,
  busy,
  error,
  onClick,
}: {
  balance: number | null;
  busy: boolean;
  error: string | null;
  onClick: () => void;
}) {
  const insufficient = balance != null && balance < UNLOCK_COST;
  return (
    <section style={{ padding: "32px 28px 0" }}>
      <div
        style={{
          border: "1px solid var(--color-line-strong)",
          padding: "26px 22px",
          background: "transparent",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "2px",
            opacity: 0.4,
            color: "var(--color-ink)",
          }}
        >
          FULL
        </div>
        <div
          className="font-serif"
          style={{
            marginTop: 14,
            fontSize: 22,
            fontWeight: 400,
            lineHeight: 1.35,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
          }}
        >
          이 업로드에 대한 전체 분석과 사진별 해석을 엽니다.
        </div>
        <p
          className="font-sans"
          style={{
            marginTop: 10,
            fontSize: 12,
            lineHeight: 1.6,
            opacity: 0.55,
            color: "var(--color-ink)",
          }}
        >
          각 사진 해석 · 방향 · 다음 행동 · 이유.
        </p>

        <button
          type="button"
          onClick={onClick}
          disabled={busy}
          className="font-sans"
          style={{
            marginTop: 22,
            width: "100%",
            height: 52,
            background: "var(--color-ink)",
            color: "var(--color-paper)",
            border: "none",
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.3px",
            cursor: busy ? "default" : "pointer",
            opacity: busy ? 0.6 : 1,
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
          }}
        >
          {busy ? (
            <span>처리 중...</span>
          ) : (
            <>
              <span>전체 분석 열기</span>
              <span
                aria-hidden
                style={{ opacity: 0.6, fontSize: 12, letterSpacing: "0.02em" }}
              >
                ·
              </span>
              <span className="tabular-nums">{UNLOCK_COST} 토큰</span>
            </>
          )}
        </button>
        {insufficient && !busy && (
          <p
            className="font-sans"
            style={{
              marginTop: 10,
              fontSize: 11,
              textAlign: "right",
              opacity: 0.5,
              color: "var(--color-ink)",
            }}
          >
            현재 잔액 {balance}토큰 — 충전 페이지로 안내
          </p>
        )}
        {error && (
          <p
            role="alert"
            className="font-sans"
            style={{
              marginTop: 10,
              fontSize: 11,
              textAlign: "right",
              color: "var(--color-danger)",
            }}
          >
            {error}
          </p>
        )}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Photos grid (업로드 사진 썸네일 — preview 영역 아래)
// ─────────────────────────────────────────────

function PhotosGrid({ urls }: { urls: PhotoUrl[] }) {
  // 모든 URL 이 null 이면 렌더 생략 (저장 실패 케이스).
  if (urls.every((u) => !u)) return null;
  return (
    <section style={{ padding: "0 28px 32px" }}>
      <Label>업로드 사진</Label>
      <div
        style={{
          marginTop: 12,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 4,
        }}
      >
        {urls.map((url, idx) => (
          <ThumbnailTile key={idx} url={url} index={idx} />
        ))}
      </div>
    </section>
  );
}

function ThumbnailTile({ url, index }: { url: PhotoUrl; index: number }) {
  return (
    <div
      style={{
        aspectRatio: "1 / 1",
        overflow: "hidden",
        background: "rgba(0, 0, 0, 0.06)",
        position: "relative",
      }}
    >
      {url ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={url}
          alt={`업로드 사진 ${index + 1}`}
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
            fontSize: 10,
            letterSpacing: "0.05em",
            color: "var(--color-ink)",
            opacity: 0.4,
          }}
        >
          #{index + 1}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Full content (10토큰 해제 후)
// ─────────────────────────────────────────────

function FullSection({
  content,
  photoUrls,
}: {
  content: FullContent;
  photoUrls: PhotoUrl[];
}) {
  const bestFit = detectBestFitIndex(content.photo_insights);

  return (
    <>
      {/* 전체 판정 서사 */}
      <section style={{ padding: "32px 28px 28px" }}>
        <Label>판정</Label>
        <p
          className="font-serif"
          style={{
            marginTop: 14,
            fontSize: 17,
            lineHeight: 1.8,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
            margin: "14px 0 0",
            whiteSpace: "pre-wrap",
          }}
        >
          {content.verdict}
        </p>
      </section>

      <Rule />

      {/* 사진별 해석 */}
      <section style={{ padding: "28px 28px 8px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 16,
          }}
        >
          <Label>사진별 해석</Label>
          <span
            className="font-sans tabular-nums"
            style={{
              fontSize: 11,
              opacity: 0.4,
              letterSpacing: "0.05em",
              color: "var(--color-ink)",
            }}
          >
            {content.photo_insights.length}장
          </span>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 18,
          }}
        >
          {content.photo_insights.map((pi) => (
            <PhotoInsightCard
              key={pi.photo_index}
              insight={pi}
              isBestFit={pi.photo_index === bestFit}
              photoUrl={photoUrls[pi.photo_index] ?? null}
            />
          ))}
        </div>
      </section>

      <Rule />

      {/* Recommendation */}
      <section style={{ padding: "28px 28px 8px" }}>
        <Label>방향</Label>
        <RecommendationBlock rec={content.recommendation} />
      </section>

      <Rule />

      {/* Numbers */}
      <NumbersBlock numbers={content.numbers} />
    </>
  );
}

function PhotoInsightCard({
  insight,
  isBestFit,
  photoUrl,
}: {
  insight: PhotoInsight;
  isBestFit: boolean;
  photoUrl: PhotoUrl;
}) {
  return (
    <div
      style={{
        border: "1px solid rgba(0, 0, 0, 0.1)",
        padding: 0,
        background: isBestFit ? "rgba(0, 0, 0, 0.03)" : "transparent",
        overflow: "hidden",
      }}
    >
      {photoUrl && (
        <div
          style={{
            width: "100%",
            aspectRatio: "4 / 5",
            overflow: "hidden",
            background: "rgba(0, 0, 0, 0.06)",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={photoUrl}
            alt={`업로드 사진 ${insight.photo_index + 1}`}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
          />
        </div>
      )}
      <div style={{ padding: "18px 18px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
            marginBottom: 12,
          }}
        >
          <span
            className="font-sans tabular-nums uppercase"
            style={{
              fontSize: 10,
              letterSpacing: "1.5px",
              opacity: 0.45,
              color: "var(--color-ink)",
            }}
          >
            #{String(insight.photo_index + 1).padStart(2, "0")}
          </span>
          {isBestFit && (
            <span
              className="font-sans"
              style={{
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "0.08em",
                padding: "3px 10px",
                background: "var(--color-ink)",
                color: "var(--color-paper)",
              }}
            >
              추구미와 가장 가까운 결
            </span>
          )}
        </div>
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
          {insight.insight}
        </p>
        <div
          style={{
            marginTop: 12,
            paddingTop: 12,
            borderTop: "1px dashed rgba(0, 0, 0, 0.12)",
          }}
        >
          <span
            className="font-sans uppercase"
            style={{
              fontSize: 10,
              letterSpacing: "1.5px",
              opacity: 0.45,
              color: "var(--color-ink)",
            }}
          >
            개선
          </span>
          <p
            className="font-sans"
            style={{
              margin: "6px 0 0",
              fontSize: 13,
              lineHeight: 1.7,
              letterSpacing: "-0.005em",
              opacity: 0.75,
              color: "var(--color-ink)",
            }}
          >
            {insight.improvement}
          </p>
        </div>
      </div>
    </div>
  );
}

function RecommendationBlock({ rec }: { rec: Recommendation }) {
  const rows = [
    { label: "방향", value: rec.style_direction },
    { label: "다음 행동", value: rec.next_action },
    { label: "이유", value: rec.why },
  ];
  return (
    <div
      style={{
        marginTop: 14,
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      {rows.map((r) => (
        <div key={r.label}>
          <span
            className="font-sans uppercase"
            style={{
              fontSize: 10,
              letterSpacing: "1.5px",
              opacity: 0.45,
              color: "var(--color-ink)",
            }}
          >
            {r.label}
          </span>
          <p
            className="font-serif"
            style={{
              margin: "6px 0 0",
              fontSize: 15,
              lineHeight: 1.75,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
              whiteSpace: "pre-wrap",
            }}
          >
            {r.value}
          </p>
        </div>
      ))}
    </div>
  );
}

function NumbersBlock({ numbers }: { numbers: VerdictNumbers }) {
  const items: { label: string; value: string }[] = [];
  if (numbers.alignment_with_profile) {
    items.push({ label: "추구미와의 정합", value: numbers.alignment_with_profile });
  }
  if (numbers.dominant_tone && numbers.dominant_tone_pct != null) {
    items.push({
      label: "지배 톤",
      value: `${numbers.dominant_tone} · ${numbers.dominant_tone_pct}%`,
    });
  } else if (numbers.dominant_tone) {
    items.push({ label: "지배 톤", value: numbers.dominant_tone });
  }
  if (numbers.chroma_multiplier != null) {
    items.push({
      label: "채도 배수",
      value: `×${numbers.chroma_multiplier.toFixed(1)}`,
    });
  }
  if (items.length === 0) return null;

  return (
    <section style={{ padding: "28px 28px 36px" }}>
      <Label>수치</Label>
      <dl
        style={{
          marginTop: 14,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "14px 12px",
          marginBlockStart: 14,
          marginBlockEnd: 0,
        }}
      >
        {items.map((it) => (
          <div key={it.label}>
            <dt
              className="font-sans"
              style={{
                fontSize: 10,
                letterSpacing: "1.2px",
                textTransform: "uppercase",
                opacity: 0.45,
                color: "var(--color-ink)",
              }}
            >
              {it.label}
            </dt>
            <dd
              className="font-serif tabular-nums"
              style={{
                margin: "4px 0 0",
                fontSize: 16,
                fontWeight: 400,
                letterSpacing: "-0.005em",
                color: "var(--color-ink)",
              }}
            >
              {it.value}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Primitives
// ─────────────────────────────────────────────

function Rule() {
  return (
    <div
      style={{
        height: 1,
        background: "var(--color-ink)",
        margin: "0 28px",
        opacity: 0.1,
      }}
    />
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-sans uppercase"
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "1.5px",
        opacity: 0.4,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}

function DateLabel() {
  const [label, setLabel] = useState("");
  useEffect(() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    setLabel(`${y} · ${m} · ${day}`);
  }, []);
  return (
    <p
      className="font-sans uppercase"
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "2px",
        opacity: 0.4,
        margin: 0,
        color: "var(--color-ink)",
      }}
    >
      {label}
    </p>
  );
}
