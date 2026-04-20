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
import { deleteVerdict, listVerdicts, resolvePhotoUrl } from "@/lib/api/verdicts";
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
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const offsetRef = useRef(0);
  const totalRef = useRef<number>(0);

  async function handleDelete(verdictId: string) {
    if (deletingId) return;
    if (typeof window !== "undefined") {
      const ok = window.confirm(
        "이 판정을 삭제하시겠어요?\n삭제 후 복구할 수 없어요.",
      );
      if (!ok) return;
    }
    setDeletingId(verdictId);
    try {
      await deleteVerdict(verdictId);
      setItems((prev) => prev.filter((v) => v.verdict_id !== verdictId));
      totalRef.current = Math.max(0, totalRef.current - 1);
      onTotalChange?.(totalRef.current);
      offsetRef.current = Math.max(0, offsetRef.current - 1);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
        return;
      }
      setError(e instanceof Error ? e.message : "삭제 실패");
    } finally {
      setDeletingId(null);
    }
  }

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

        {/* Verdict 썸네일 — 블러 없음, 항상 클리어. long-press 삭제. */}
        {items.map((v) => (
          <ThumbCell
            key={v.verdict_id}
            url={resolvePhotoUrl(v.gold_photo_url)}
            onClick={() => router.push(`/verdict/${v.verdict_id}`)}
            onLongPress={() => handleDelete(v.verdict_id)}
            deleting={deletingId === v.verdict_id}
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
//  Verdict 썸네일 — 클리어 + long-press(700ms) / right-click 삭제
// ─────────────────────────────────────────────

const LONG_PRESS_MS = 700;

function ThumbCell({
  url,
  onClick,
  onLongPress,
  deleting,
}: {
  url: string;
  onClick: () => void;
  onLongPress: () => void;
  deleting: boolean;
}) {
  const pressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressedRef = useRef(false);

  function clearPress() {
    if (pressTimerRef.current) {
      clearTimeout(pressTimerRef.current);
      pressTimerRef.current = null;
    }
  }

  function onPointerDown() {
    longPressedRef.current = false;
    clearPress();
    pressTimerRef.current = setTimeout(() => {
      longPressedRef.current = true;
      // 가벼운 햅틱 피드백 (지원 기기만)
      try {
        (navigator as Navigator & { vibrate?: (p: number | number[]) => boolean }).vibrate?.(25);
      } catch {
        // ignore
      }
      onLongPress();
    }, LONG_PRESS_MS);
  }

  function onClickGuarded() {
    // long-press가 발동된 클릭이면 navigate 차단
    if (longPressedRef.current) {
      longPressedRef.current = false;
      return;
    }
    onClick();
  }

  return (
    <button
      type="button"
      onClick={onClickGuarded}
      onPointerDown={onPointerDown}
      onPointerUp={clearPress}
      onPointerLeave={clearPress}
      onPointerMove={clearPress}
      onPointerCancel={clearPress}
      onContextMenu={(e) => {
        // 데스크톱 우클릭 — 컨텍스트 메뉴 대신 삭제 프롬프트
        e.preventDefault();
        onLongPress();
      }}
      aria-label="판정 — 탭: 보기 · 길게 누르기: 삭제"
      style={{
        position: "relative",
        aspectRatio: "1/1",
        background: "rgba(0, 0, 0, 0.04)",
        border: "none",
        padding: 0,
        cursor: "pointer",
        overflow: "hidden",
        opacity: deleting ? 0.4 : 1,
        transition: "opacity 150ms ease",
        // long-press 시 drag/select 방지
        userSelect: "none",
        WebkitUserSelect: "none",
        touchAction: "manipulation",
      }}
    >
      {url && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={url}
          alt=""
          draggable={false}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            display: "block",
            pointerEvents: "none", // 이미지가 이벤트 먹지 않도록
          }}
        />
      )}
      {deleting && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 10,
            color: "var(--color-paper)",
            background: "rgba(0, 0, 0, 0.5)",
            fontFamily: "var(--font-sans)",
            fontWeight: 600,
            letterSpacing: "1px",
          }}
        >
          삭제 중
        </div>
      )}
    </button>
  );
}
