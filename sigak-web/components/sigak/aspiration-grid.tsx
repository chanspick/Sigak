// AspirationGrid — 추구미 분석 이력 그리드 (Phase J 후속 노출 UI).
//
// 피드 탭(/) 하단에 노출. VerdictGrid 와 시각적 패턴 동일 (3-col / gap 2px).
// 첫 셀 "+" = 새 추구미 분석 시작 (/aspiration). 썸네일 = 추구미 대상 사진.
//
// MVP 스코프:
//   - 한 번에 50건 로드 (aspiration 은 verdict 대비 누적량 적음 — 무한스크롤 불필요)
//   - long-press 삭제 미적용 (백엔드 DELETE 엔드포인트 미구현)
//   - 썸네일 우상단에 source 라벨 ("@핸들" 또는 "Pinterest")
//   - 0건이어도 "+" 셀 노출 → 신규 분석 진입점 유지
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import {
  listAspirations,
  resolveAspirationCoverUrl,
} from "@/lib/api/aspirations";
import type { AspirationListItem } from "@/lib/types/aspiration";

const PAGE_SIZE = 50;

export function AspirationGrid() {
  const router = useRouter();
  const [items, setItems] = useState<AspirationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await listAspirations(PAGE_SIZE, 0);
        if (cancelled) return;
        setItems(res.analyses);
        setError(null);
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        setError(e instanceof Error ? e.message : "추구미 이력 로드 실패");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return (
    <>
      <SectionHeader count={items.length} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 2,
          background: "var(--color-paper)",
        }}
      >
        <AddCell onClick={() => router.push("/aspiration")} />

        {items.map((a) => (
          <ThumbCell
            key={a.analysis_id}
            url={resolveAspirationCoverUrl(a.cover_photo_url)}
            label={makeLabel(a)}
            onClick={() => router.push(`/aspiration/${a.analysis_id}`)}
          />
        ))}
      </div>

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

      {loading && items.length === 0 && (
        <div
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
            로딩…
          </span>
        </div>
      )}

      <div style={{ height: 60 }} />
    </>
  );
}

// ─────────────────────────────────────────────
//  헤더 — "추구미 이력" + 카운트
// ─────────────────────────────────────────────

function SectionHeader({ count }: { count: number }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "baseline",
        justifyContent: "space-between",
        padding: "32px 24px 14px",
        borderTop: "1px solid rgba(0, 0, 0, 0.08)",
      }}
    >
      <span
        className="font-sans uppercase"
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "1.5px",
          opacity: 0.55,
          color: "var(--color-ink)",
        }}
      >
        추구미 이력
      </span>
      <span
        className="font-serif tabular-nums"
        style={{
          fontSize: 14,
          fontWeight: 400,
          opacity: 0.55,
          color: "var(--color-ink)",
        }}
      >
        {count}
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────
//  + 진입 셀 (verdict-grid 와 동일 스타일)
// ─────────────────────────────────────────────

function AddCell({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="새 추구미 분석"
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
//  썸네일 셀 — source 라벨 우상단 음각
// ─────────────────────────────────────────────

function ThumbCell({
  url,
  label,
  onClick,
}: {
  url: string;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`추구미 분석 — ${label}`}
      style={{
        position: "relative",
        aspectRatio: "1/1",
        background: "rgba(0, 0, 0, 0.04)",
        border: "none",
        padding: 0,
        cursor: "pointer",
        overflow: "hidden",
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
            pointerEvents: "none",
          }}
        />
      )}

      <span
        className="font-sans"
        style={{
          position: "absolute",
          top: 6,
          right: 6,
          maxWidth: "calc(100% - 12px)",
          padding: "2px 6px",
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "-0.005em",
          color: "var(--color-paper)",
          background: "rgba(0, 0, 0, 0.45)",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </span>
    </button>
  );
}

// ─────────────────────────────────────────────
//  source 라벨 빌더
//  IG: "@핸들" (12자 cap), Pinterest: "Pinterest"
// ─────────────────────────────────────────────

function makeLabel(item: AspirationListItem): string {
  if (item.target_type === "pinterest") return "Pinterest";
  const handle = item.target_identifier.replace(/^@/, "");
  return handle.length > 12 ? `@${handle.slice(0, 12)}…` : `@${handle}`;
}
