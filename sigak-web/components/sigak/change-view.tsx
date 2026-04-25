// SIGAK MVP v2 BM — ChangeView
//
// /change 탭. 유저 전체 verdict 시계열 궤적.
// 3건 미만이면 empty state, 3건+ 이면 SVG 라인 차트(3축 오버레이).
//
// 무료 엔드포인트. 차트 디자인은 placeholder 수준 — 추후 리파인.
"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getChange } from "@/lib/api/change";
import type { ChangeEntry, ChangeResponse } from "@/lib/types/mvp";

const MIN_ENTRIES_FOR_CHART = 3;

type AxisKey = "shape" | "volume" | "age";

const AXES: { key: AxisKey; label: string; kr: string }[] = [
  { key: "shape", label: "SHAPE", kr: "형태" },
  { key: "volume", label: "VOLUME", kr: "부피" },
  { key: "age", label: "AGE", kr: "나이감" },
];

export function ChangeView() {
  const router = useRouter();
  const [state, setState] = useState<{
    loading: boolean;
    data: ChangeResponse | null;
    error: string | null;
  }>({ loading: true, data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getChange();
        if (!cancelled) setState({ loading: false, data, error: null });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        setState({
          loading: false,
          data: null,
          error: e instanceof Error ? e.message : "변화 로드 실패",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state.loading) {
    return (
      <div
        style={{
          minHeight: "40vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: 0.3,
          fontSize: 12,
          fontFamily: "var(--font-sans)",
          color: "var(--color-ink)",
        }}
      >
        불러오는 중...
      </div>
    );
  }

  if (state.error || !state.data) {
    return (
      <div style={{ padding: "40px 28px", textAlign: "center" }}>
        <p
          className="font-sans"
          role="alert"
          style={{
            fontSize: 13,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
          }}
        >
          {state.error ?? "알 수 없는 오류"}
        </p>
      </div>
    );
  }

  const entries = state.data.entries;

  // 임시 (2026-04-26) — 변화 그래프 v1.5 후속. 현재는 monthly 메시지만 노출.
  // entries 갯수 무관 ChangeEmpty 강제. 재개 시 if 조건 + ChangeChart 복원.
  return <ChangeEmpty count={entries.length} />;
}

// ─────────────────────────────────────────────
//  Empty state
// ─────────────────────────────────────────────

function ChangeEmpty({ count }: { count: number }) {
  return (
    <section
      style={{
        minHeight: "60vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 28px",
        gap: 18,
        maxWidth: 420,
        margin: "0 auto",
      }}
    >
      <span
        className="font-sans uppercase"
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "1.6px",
          opacity: 0.4,
          color: "var(--color-ink)",
        }}
      >
        MONTHLY
      </span>
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 22,
          lineHeight: 1.5,
          letterSpacing: "-0.01em",
          color: "var(--color-ink)",
          opacity: 0.85,
          textAlign: "center",
        }}
      >
        매달 15일,
        <br />
        당신의 결을 정리해드려요
      </p>
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 13,
          lineHeight: 1.75,
          opacity: 0.6,
          letterSpacing: "-0.005em",
          color: "var(--color-ink)",
          textAlign: "center",
          maxWidth: 360,
        }}
      >
        변화는 각 월 15일에 여러분의 SIGAK 서비스 경험과 트렌드 변화를
        기반으로 만들어집니다.
      </p>
      {count > 0 && (
        <p
          className="font-sans tabular-nums"
          style={{
            margin: 0,
            fontSize: 11,
            opacity: 0.35,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
          }}
        >
          지금까지 쌓인 기록 · {count}건
        </p>
      )}
    </section>
  );
}

// ─────────────────────────────────────────────
//  Chart (SVG line, 3축 오버레이)
// ─────────────────────────────────────────────

function ChangeChart({ entries }: { entries: ChangeEntry[] }) {
  const [active, setActive] = useState<AxisKey | "all">("all");
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  // 좌표 series 추출 (winner_coords 기준). null이면 0 처리.
  const series: Record<AxisKey, number[]> = useMemo(() => {
    const s: Record<AxisKey, number[]> = { shape: [], volume: [], age: [] };
    for (const e of entries) {
      s.shape.push(e.winner_coords?.shape ?? 0);
      s.volume.push(e.winner_coords?.volume ?? 0);
      s.age.push(e.winner_coords?.age ?? 0);
    }
    return s;
  }, [entries]);

  // 추구미 타겟 (마지막 것 기준 — 최신 추구미가 현재 목표)
  const latestTarget = entries[entries.length - 1]?.target_coords ?? null;

  const W = 340;
  const H = 160;
  const padX = 14;
  const padY = 18;
  const n = entries.length;
  const innerW = W - padX * 2;
  const innerH = H - padY * 2;

  const xFor = (i: number) =>
    n <= 1 ? padX + innerW / 2 : padX + innerW * (i / (n - 1));
  // y: -1..1 범위 (series 값 범위 동일 가정)
  const yFor = (v: number) => padY + innerH * (1 - (v + 1) / 2);

  const pathFor = (values: number[]) =>
    values
      .map((v, i) => `${i === 0 ? "M" : "L"}${xFor(i).toFixed(1)},${yFor(v).toFixed(1)}`)
      .join(" ");

  const colors: Record<AxisKey, string> = {
    shape: "var(--color-ink)",
    volume: "#8B9D7D", // sage legacy tone — axis 구분용만
    age: "rgba(0, 0, 0, 0.35)",
  };

  const visibleAxes: AxisKey[] =
    active === "all" ? ["shape", "volume", "age"] : [active];

  const hoverEntry = hoverIdx != null ? entries[hoverIdx] : null;

  return (
    <section style={{ padding: "28px 28px 60px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 14,
        }}
      >
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
          궤적
        </span>
        <span
          className="font-serif tabular-nums"
          style={{ fontSize: 14, color: "var(--color-ink)" }}
        >
          {entries.length}건
        </span>
      </div>

      {/* Axis toggles */}
      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          marginBottom: 14,
        }}
      >
        {[{ key: "all" as const, label: "ALL", kr: "전체" }, ...AXES].map((a) => {
          const isActive = active === a.key;
          const color = a.key === "all" ? "var(--color-ink)" : colors[a.key as AxisKey];
          return (
            <button
              key={a.key}
              type="button"
              onClick={() => setActive(a.key)}
              className="font-sans"
              style={{
                padding: "6px 10px",
                background: isActive ? "var(--color-ink)" : "transparent",
                color: isActive ? "var(--color-paper)" : color,
                border: isActive
                  ? "1px solid var(--color-ink)"
                  : "1px solid rgba(0, 0, 0, 0.15)",
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "1.5px",
                cursor: "pointer",
                borderRadius: 0,
              }}
            >
              {a.label}
            </button>
          );
        })}
      </div>

      {/* Chart */}
      <div
        style={{
          position: "relative",
          border: "1px solid rgba(0, 0, 0, 0.1)",
          background: "transparent",
        }}
      >
        <svg
          width="100%"
          viewBox={`0 0 ${W} ${H}`}
          style={{ display: "block" }}
          onMouseLeave={() => setHoverIdx(null)}
        >
          {/* Midline (y=0) */}
          <line
            x1={padX}
            y1={yFor(0)}
            x2={W - padX}
            y2={yFor(0)}
            stroke="rgba(0, 0, 0, 0.1)"
            strokeWidth={1}
            strokeDasharray="2 3"
          />

          {/* Target 추구미 좌표 라인 (optional, all일 때만) */}
          {active === "all" && latestTarget && (
            <>
              <line
                x1={padX}
                y1={yFor(latestTarget.shape)}
                x2={W - padX}
                y2={yFor(latestTarget.shape)}
                stroke={colors.shape}
                strokeWidth={0.5}
                strokeDasharray="1 4"
                opacity={0.35}
              />
            </>
          )}

          {/* Lines for visible axes */}
          {visibleAxes.map((a) => (
            <g key={a}>
              <path
                d={pathFor(series[a])}
                fill="none"
                stroke={colors[a]}
                strokeWidth={1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {series[a].map((v, i) => (
                <circle
                  key={i}
                  cx={xFor(i)}
                  cy={yFor(v)}
                  r={hoverIdx === i ? 3 : 2}
                  fill={colors[a]}
                />
              ))}
            </g>
          ))}

          {/* Hover hit-zones (invisible wide rects) */}
          {entries.map((_, i) => (
            <rect
              key={`hit-${i}`}
              x={xFor(i) - (innerW / Math.max(1, n - 1)) / 2}
              y={0}
              width={innerW / Math.max(1, n - 1)}
              height={H}
              fill="transparent"
              onMouseEnter={() => setHoverIdx(i)}
              style={{ cursor: "pointer" }}
            />
          ))}
        </svg>

        {/* Axis labels */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "6px 14px 10px",
            fontSize: 10,
            fontFamily: "var(--font-mono)",
            opacity: 0.3,
            letterSpacing: "0.04em",
            color: "var(--color-ink)",
          }}
          className="tabular-nums"
        >
          <span>{formatDate(entries[0]?.created_at)}</span>
          <span>{formatDate(entries[entries.length - 1]?.created_at)}</span>
        </div>
      </div>

      {/* Hover info */}
      {hoverEntry && (
        <div
          style={{
            marginTop: 14,
            padding: "10px 14px",
            background: "rgba(0, 0, 0, 0.03)",
            fontFamily: "var(--font-sans)",
            fontSize: 11,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          <div style={{ opacity: 0.5, marginBottom: 4 }}>
            {formatDate(hoverEntry.created_at)}
          </div>
          <div className="tabular-nums" style={{ opacity: 0.75 }}>
            Shape {fmt(hoverEntry.winner_coords?.shape)}
            {" · "}Volume {fmt(hoverEntry.winner_coords?.volume)}
            {" · "}Age {fmt(hoverEntry.winner_coords?.age)}
          </div>
        </div>
      )}

      {/* Legend */}
      {active === "all" && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: 20,
            marginTop: 18,
            fontSize: 10,
            fontFamily: "var(--font-sans)",
            letterSpacing: "1.5px",
            color: "var(--color-ink)",
            opacity: 0.65,
          }}
        >
          {AXES.map((a) => (
            <span key={a.key} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                style={{
                  width: 10,
                  height: 2,
                  background: colors[a.key],
                  display: "inline-block",
                }}
              />
              {a.label}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function formatDate(iso: string | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${String(d.getMonth() + 1).padStart(2, "0")}·${String(d.getDate()).padStart(2, "0")}`;
}

function fmt(n: number | null | undefined): string {
  if (n == null) return "—";
  const r = Math.round(n * 100) / 100;
  const sign = r === 0 ? "" : r > 0 ? "+" : "−";
  return `${sign}${Math.abs(r).toFixed(2)}`;
}
