// SIGAK MVP v1.2 (D-6 revised) — VerdictGrid
//
// Instagram 3-col gap 2px. 본인 사진이므로 블러/자물쇠 없음, 항상 클리어.
// 첫 셀은 항상 "+" 업로드 버튼 — 피드가 비어있어도 상시 노출.
// 무한 스크롤 (IntersectionObserver).
//
// onTotalChange 콜백으로 상위(FeedView)에 총 개수 전달 — 프로필 섹션의
// "피드 N"에 쓰임.
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { listVerdicts, resolvePhotoUrl } from "@/lib/api/verdicts";
import type { VerdictListItem } from "@/lib/types/mvp";

const PAGE_SIZE = 30;

interface VerdictGridProps {
  /** 총 개수 상위로 전달 (프로필 섹션 "피드 N"용). */
  onTotalChange?: (total: number) => void;
}

export function VerdictGrid({ onTotalChange }: VerdictGridProps = {}) {
  const router = useRouter();
  const [items, setItems] = useState<VerdictListItem[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const offsetRef = useRef(0);
  const totalRef = useRef<number>(0);

  const loadMore = useCallback(async () => {
    if (!hasMore) return;
    try {
      const res = await listVerdicts(PAGE_SIZE, offsetRef.current);
      setItems((prev) => [...prev, ...res.verdicts]);
      offsetRef.current += res.verdicts.length;
      setHasMore(res.has_more);
      if (res.total !== totalRef.current) {
        totalRef.current = res.total;
        onTotalChange?.(res.total);
      }
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
        return;
      }
      setError(e instanceof Error ? e.message : "피드 로드 실패");
    } finally {
      setLoading(false);
    }
  }, [hasMore, router, onTotalChange]);

  // 초기 로드
  useEffect(() => {
    void loadMore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 무한 스크롤
  useEffect(() => {
    if (!sentinelRef.current || !hasMore || loading) return;
    const el = sentinelRef.current;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          void loadMore();
        }
      },
      { rootMargin: "200px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [hasMore, loading, loadMore]);

  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 2,
          background: "var(--color-paper)",
        }}
      >
        {/* 첫 셀: + 업로드 진입점 (항상 노출) */}
        <AddCell onClick={() => router.push("/verdict/new")} />

        {/* Verdict 썸네일 — 블러 없음, 항상 클리어 */}
        {items.map((v) => (
          <ThumbCell
            key={v.verdict_id}
            url={resolvePhotoUrl(v.gold_photo_url)}
            onClick={() => router.push(`/verdict/${v.verdict_id}`)}
          />
        ))}
      </div>

      {/* 무한 스크롤 sentinel */}
      {hasMore && (
        <div
          ref={sentinelRef}
          style={{
            height: 48,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            className="font-sans"
            style={{ fontSize: 11, opacity: 0.3, letterSpacing: "1px" }}
          >
            {loading ? "로딩…" : ""}
          </span>
        </div>
      )}

      {error && (
        <p
          className="font-sans"
          role="alert"
          style={{
            padding: "20px 28px",
            fontSize: 12,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
            textAlign: "center",
          }}
        >
          {error}
        </p>
      )}

      <div style={{ height: 60 }} />
    </>
  );
}

// ─────────────────────────────────────────────
//  + 업로드 셀 (첫 셀)
// ─────────────────────────────────────────────

function AddCell({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="새 판정"
      style={{
        aspectRatio: "1/1",
        background: "rgba(0, 0, 0, 0.04)",
        border: "none",
        padding: 0,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
      }}
    >
      <span style={{ position: "relative", width: 28, height: 28 }}>
        <span
          style={{
            position: "absolute",
            top: 13.5,
            left: 0,
            width: 28,
            height: 1,
            background: "var(--color-ink)",
          }}
        />
        <span
          style={{
            position: "absolute",
            left: 13.5,
            top: 0,
            width: 1,
            height: 28,
            background: "var(--color-ink)",
          }}
        />
      </span>
    </button>
  );
}

// ─────────────────────────────────────────────
//  Verdict 썸네일 — 클리어, 블러/락 없음
// ─────────────────────────────────────────────

function ThumbCell({
  url,
  onClick,
}: {
  url: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="판정 보기"
      style={{
        aspectRatio: "1/1",
        background: "rgba(0, 0, 0, 0.04)",
        border: "none",
        padding: 0,
        cursor: "pointer",
        overflow: "hidden",
      }}
    >
      {url && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={url}
          alt=""
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
          }}
        />
      )}
    </button>
  );
}
