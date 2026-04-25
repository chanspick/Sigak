// SIGAK — VerdictV2Screen (2026-04-25, WTP 가설 적용)
//
// Sonnet 4.6 cross-analysis 결과 렌더.
// preview: 무료 공개 (hook_line + reason_summary + best_fit 1장 풀 노출)
// full_content: 10 토큰 unlock 후 공개 (verdict + photo_insights + recommendation)
//
// 페르소나: 정중체 "~습니다" (Sia 친밀체와 분리). 평론 톤 유지.
//
// WTP 가설 (2026-04-25):
//   best_fit 1장 풀 노출 (insight + improvement) → "AI 가 진짜 보네" 신뢰 형성
//   → 나머지 N-1장 궁금증 → 결제 트리거. 결제 전 BestFitCard + BlurredPhotosGrid
//   구성으로 노출. 결제 후 photo_insights 첫 자리에 best_fit 정렬.
//
// best_fit 식별 우선순위:
//   1. preview.best_fit_photo_index / full_content.best_fit_photo_index 명시 필드
//      (백엔드 build_verdict_v2 후처리 sync 보장).
//   2. 정규식 fallback (BEST_FIT_PATTERNS) — backward compat 안전망.

"use client";

import { useEffect, useMemo, useState } from "react";
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

/** photo_insights 텍스트에서 best_fit 정규식 매칭 (legacy fallback).
 *  명시 필드 (best_fit_photo_index) 가 우선이며, 부재 시에만 호출. */
function detectBestFitIndex(photoInsights: PhotoInsight[]): number | null {
  for (const pi of photoInsights) {
    const blob = `${pi.insight} ${pi.improvement}`;
    if (BEST_FIT_PATTERNS.some((p) => p.test(blob))) {
      return pi.photo_index;
    }
  }
  return null;
}

/** preview / full_content 의 best_fit_photo_index 결정.
 *  우선순위: full_content 명시 → preview 명시 → 정규식 fallback (full_content 만).
 *  unlock 전엔 full_content 가 null 이라 preview 명시 필드만 사용. */
function resolveBestFitIndex(
  preview: PreviewContent,
  full: FullContent | null,
): number | null {
  // 1순위: 명시 필드 (full → preview)
  const fullExplicit = full?.best_fit_photo_index;
  if (fullExplicit !== null && fullExplicit !== undefined) return fullExplicit;
  const previewExplicit = preview.best_fit_photo_index;
  if (previewExplicit !== null && previewExplicit !== undefined) {
    return previewExplicit;
  }
  // 2순위: 정규식 fallback (unlock 후 full_content 가 있을 때만)
  if (full) {
    return detectBestFitIndex(full.photo_insights);
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

  // WTP 가설 — best_fit 인덱스 / URL 결정 (memo 화로 매 렌더 재계산 방지).
  const bestFitIndex = useMemo(
    () => resolveBestFitIndex(data.preview, data.full_content),
    [data.preview, data.full_content],
  );
  const bestFitUrl: PhotoUrl =
    data.best_fit_photo_url ??
    (bestFitIndex !== null && bestFitIndex < data.photo_urls.length
      ? data.photo_urls[bestFitIndex]
      : null);

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
        best_fit_photo_url: res.best_fit_photo_url ?? data.best_fit_photo_url,
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

      {/* Full content (unlock 후) 또는 BestFit 풀 노출 + 잠금 N-1장 + Unlock CTA */}
      {unlocked && data.full_content ? (
        <FullSection
          content={data.full_content}
          photoUrls={data.photo_urls}
          bestFitIndex={bestFitIndex}
        />
      ) : (
        <PreviewBestFitGate
          preview={data.preview}
          photoUrls={data.photo_urls}
          bestFitIndex={bestFitIndex}
          bestFitUrl={bestFitUrl}
          balance={balance}
          busy={unlocking}
          error={unlockError}
          onUnlock={handleUnlock}
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
//  WTP 가설 — Preview BestFit Gate
//
//  best_fit 1 장 풀 노출 + 나머지 N-1 장 블러 + Unlock CTA 통합 영역.
//  best_fit_index 가 null 이면 BestFitCard 스킵하고 기존 UnlockSection 만 노출
//  (backward compat — 기존 동작 보존).
// ─────────────────────────────────────────────

function PreviewBestFitGate({
  preview,
  photoUrls,
  bestFitIndex,
  bestFitUrl,
  balance,
  busy,
  error,
  onUnlock,
}: {
  preview: PreviewContent;
  photoUrls: PhotoUrl[];
  bestFitIndex: number | null;
  bestFitUrl: PhotoUrl;
  balance: number | null;
  busy: boolean;
  error: string | null;
  onUnlock: () => void;
}) {
  const hasBestFit =
    bestFitIndex !== null &&
    preview.best_fit_insight !== null &&
    preview.best_fit_insight !== undefined &&
    preview.best_fit_improvement !== null &&
    preview.best_fit_improvement !== undefined;

  // best_fit 부재 시 기존 동작 — UnlockSection 만 노출.
  if (!hasBestFit) {
    return (
      <UnlockSection
        balance={balance}
        busy={busy}
        error={error}
        onClick={onUnlock}
      />
    );
  }

  // best_fit 명시 + photo_urls 길이 > 1 → 잠금 N-1 카드 영역도 함께 렌더.
  const remainingCount = Math.max(photoUrls.length - 1, 0);

  return (
    <>
      <section style={{ padding: "32px 28px 8px" }}>
        <SectionTitle>이번 업로드의 베스트 1장</SectionTitle>
      </section>
      <BestFitCard
        photoIndex={bestFitIndex!}
        photoUrl={bestFitUrl}
        insight={preview.best_fit_insight!}
        improvement={preview.best_fit_improvement!}
      />

      {remainingCount > 0 && (
        <>
          <section style={{ padding: "32px 28px 8px" }}>
            <SectionTitle>{`나머지 ${remainingCount}장`}</SectionTitle>
          </section>
          <BlurredPhotosGrid
            photoUrls={photoUrls}
            excludeIndex={bestFitIndex!}
          />
        </>
      )}

      <UnlockSection
        balance={balance}
        busy={busy}
        error={error}
        onClick={onUnlock}
      />
    </>
  );
}

// ─────────────────────────────────────────────
//  BestFit Card — preview / unlock 양쪽에서 재사용 가능한 카드 본체.
//  PhotoInsightCard 와 동일 디자인 토큰 (4:5 이미지 + serif 본문 + dashed
//  divider + sans 개선) 으로 시각 연속성 확보.
// ─────────────────────────────────────────────

function BestFitCard({
  photoIndex,
  photoUrl,
  insight,
  improvement,
}: {
  photoIndex: number;
  photoUrl: PhotoUrl;
  insight: string;
  improvement: string;
}) {
  return (
    <section style={{ padding: "0 28px 8px" }}>
      <div
        style={{
          border: "1px solid rgba(0, 0, 0, 0.1)",
          padding: 0,
          background: "rgba(0, 0, 0, 0.03)",
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
              alt={`베스트 사진 ${photoIndex + 1}`}
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
              #{String(photoIndex + 1).padStart(2, "0")}
            </span>
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
          </div>
          <p
            className="font-serif"
            style={{
              margin: 0,
              fontSize: 15,
              lineHeight: 1.7,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
              whiteSpace: "pre-wrap",
            }}
          >
            {insight}
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
                whiteSpace: "pre-wrap",
              }}
            >
              {improvement}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  BlurredPhotosGrid — best_fit 제외 N-1 장의 잠금 미리보기.
//  4:5 카드 + 이미지 blur + 텍스트 슬롯 (스켈레톤 라인) 으로 unlock 후 카드와
//  시각적 연속성 유지. 결제 트리거 강화.
// ─────────────────────────────────────────────

function BlurredPhotosGrid({
  photoUrls,
  excludeIndex,
}: {
  photoUrls: PhotoUrl[];
  excludeIndex: number;
}) {
  const blurred = photoUrls
    .map((url, idx) => ({ url, idx }))
    .filter((item) => item.idx !== excludeIndex);
  if (blurred.length === 0) return null;
  return (
    <section
      style={{
        padding: "0 28px 8px",
        display: "flex",
        flexDirection: "column",
        gap: 18,
      }}
    >
      {blurred.map(({ url, idx }) => (
        <BlurredCard key={idx} photoIndex={idx} photoUrl={url} />
      ))}
    </section>
  );
}

function BlurredCard({
  photoIndex,
  photoUrl,
}: {
  photoIndex: number;
  photoUrl: PhotoUrl;
}) {
  return (
    <div
      style={{
        border: "1px solid rgba(0, 0, 0, 0.1)",
        padding: 0,
        background: "transparent",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          width: "100%",
          aspectRatio: "4 / 5",
          overflow: "hidden",
          background: "rgba(0, 0, 0, 0.06)",
          position: "relative",
        }}
      >
        {photoUrl ? (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={photoUrl}
            alt={`잠금 사진 ${photoIndex + 1}`}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
              filter: "blur(14px)",
              transform: "scale(1.06)",
            }}
          />
        ) : (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 12,
              color: "var(--color-ink)",
              opacity: 0.3,
            }}
          >
            잠금
          </div>
        )}
      </div>
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
              opacity: 0.35,
              color: "var(--color-ink)",
            }}
          >
            #{String(photoIndex + 1).padStart(2, "0")}
          </span>
          <span
            className="font-sans uppercase"
            style={{
              fontSize: 10,
              letterSpacing: "1.5px",
              opacity: 0.35,
              color: "var(--color-ink)",
            }}
          >
            잠금
          </span>
        </div>
        {/* 텍스트 스켈레톤 (3 라인) */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <SkeletonLine widthPct={92} />
          <SkeletonLine widthPct={78} />
          <SkeletonLine widthPct={48} />
        </div>
      </div>
    </div>
  );
}

function SkeletonLine({ widthPct }: { widthPct: number }) {
  return (
    <div
      aria-hidden
      style={{
        height: 10,
        width: `${widthPct}%`,
        background: "rgba(0, 0, 0, 0.08)",
        borderRadius: 0,
      }}
    />
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2
      className="font-serif"
      style={{
        margin: 0,
        fontSize: 16,
        fontWeight: 400,
        lineHeight: 1.4,
        letterSpacing: "-0.005em",
        opacity: 0.6,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </h2>
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
  bestFitIndex,
}: {
  content: FullContent;
  photoUrls: PhotoUrl[];
  /** preview / full 명시 필드에서 결정된 best_fit 인덱스. null = 미선정.
   *  null 이면 정규식 fallback 시도. */
  bestFitIndex: number | null;
}) {
  // 명시 필드 우선, 없으면 정규식 fallback (안전망 보존)
  const bestFit =
    bestFitIndex !== null
      ? bestFitIndex
      : detectBestFitIndex(content.photo_insights);

  // 정렬: best_fit 첫 번째, 나머지는 photo_index 순 유지.
  // 새 배열 생성으로 원본 photo_insights 불변 보존.
  const orderedInsights = [...content.photo_insights].sort((a, b) => {
    if (bestFit !== null) {
      if (a.photo_index === bestFit) return -1;
      if (b.photo_index === bestFit) return 1;
    }
    return a.photo_index - b.photo_index;
  });

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

      {/* 사진별 해석 — best_fit 첫 번째 정렬 */}
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
          {orderedInsights.map((pi) => (
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
