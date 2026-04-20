// SIGAK MVP v1.2 — VerdictGrid (Instagram 스타일 피드)
//
// 3-col grid gap 2px. blur_released=false면 blur(14px) + 자물쇠.
// 무한 스크롤 (IntersectionObserver). 빈 상태 중앙 안내.
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { listVerdicts, resolvePhotoUrl } from "@/lib/api/verdicts";
import type { VerdictListItem } from "@/lib/types/mvp";

const PAGE_SIZE = 30;

export function VerdictGrid() {
  const router = useRouter();
  const [items, setItems] = useState<VerdictListItem[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const offsetRef = useRef(0);

  const loadMore = useCallback(async () => {
    if (loading === false && !hasMore) return;
    try {
      const res = await listVerdicts(PAGE_SIZE, offsetRef.current);
      setItems((prev) => [...prev, ...res.verdicts]);
      offsetRef.current += res.verdicts.length;
      setHasMore(res.has_more);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setError(e instanceof Error ? e.message : "피드 로드 실패");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

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

  // 초기 로딩
  if (loading && items.length === 0) {
    return (
      <div
        style={{
          minHeight: "60vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--color-ink)",
          opacity: 0.3,
          fontFamily: "var(--font-sans)",
          fontSize: 12,
        }}
        aria-busy
      >
        불러오는 중...
      </div>
    );
  }

  // 빈 상태
  if (!loading && items.length === 0) {
    return (
      <div
        style={{
          minHeight: "60vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 28px",
        }}
      >
        <p
          className="font-sans"
          style={{
            textAlign: "center",
            fontSize: 13,
            opacity: 0.4,
            lineHeight: 1.6,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
          }}
        >
          아직 판정이 없어요.
          <br />
          우상단 + 버튼을 눌러 시작하세요.
        </p>
      </div>
    );
  }

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
        {items.map((v) => (
          <GridCell
            key={v.verdict_id}
            item={v}
            onClick={() => router.push(`/verdict/${v.verdict_id}`)}
          />
        ))}
      </div>

      {/* Sentinel for infinite scroll */}
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

      {/* 하단 여백 */}
      <div style={{ height: 60 }} />
    </>
  );
}

// ─────────────────────────────────────────────
//  GridCell
// ─────────────────────────────────────────────

function GridCell({
  item,
  onClick,
}: {
  item: VerdictListItem;
  onClick: () => void;
}) {
  const src = resolvePhotoUrl(item.gold_photo_url);
  const locked = !item.blur_released;

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={locked ? "가려진 판정" : "판정 보기"}
      style={{
        position: "relative",
        aspectRatio: "1/1",
        background: "rgba(0, 0, 0, 0.04)",
        border: "none",
        padding: 0,
        cursor: "pointer",
        overflow: "hidden",
      }}
    >
      {/* Image */}
      {src && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={src}
          alt=""
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
            filter: locked ? "blur(14px)" : "none",
            transform: locked ? "scale(1.1)" : "none",
            transformOrigin: "center",
          }}
        />
      )}

      {/* Locked overlay (어둡게) */}
      {locked && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(0, 0, 0, 0.10)",
            pointerEvents: "none",
          }}
        />
      )}

      {/* Top-right icon — 자물쇠 or 체크 */}
      <div
        style={{
          position: "absolute",
          top: 6,
          right: 6,
          width: 16,
          height: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          filter: "drop-shadow(0 1px 2px rgba(0, 0, 0, 0.4))",
        }}
      >
        {locked ? (
          <svg width="12" height="13" viewBox="0 0 12 13" aria-hidden>
            <rect
              x="2"
              y="6"
              width="8"
              height="6"
              rx="0.8"
              stroke="#FFFFFF"
              strokeWidth="1"
              fill="none"
            />
            <path
              d="M4 6V4a2 2 0 014 0v2"
              stroke="#FFFFFF"
              strokeWidth="1"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        ) : (
          <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
            <path
              d="M2 6l3 3 5-6"
              stroke="#FFFFFF"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
        )}
      </div>
    </button>
  );
}
