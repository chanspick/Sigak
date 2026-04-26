// 추구미 갭 분석 섹션 (standard 잠금)
// 프리미엄 컨설팅 리포트 스타일: 정량 좌표 기반 비주얼 방향 시각화
// 구조: 헤더 → 유형 카드 → 갭 오버뷰(산점도+미니바) → 요약 → 방향 카드

import Image from "next/image";
import { GapScatterPlot } from "@/components/report/charts/gap-scatter-plot";

interface Coordinates {
  shape: number;
  volume: number;
  age: number;
}

interface DirectionItem {
  axis: string;
  label: string;
  name_kr?: string;
  label_low?: string;
  label_high?: string;
  axis_description?: string;
  from_score: number;
  to_score: number;
  delta: number;
  from_label: string;
  to_label: string;
  difficulty: string;
  recommendation: string;
}

// Phase B-4 / B-5 (PI-REVIVE 2026-04-26): 누적 추구미 분석 카드
// gap_narrative 제거 (vault raw text 가 좌표 숫자 + 영문 axis 키 mix 로 UX 깨짐)
interface AspirationReference {
  target_handle: string;
  source: string; // "instagram" | "pinterest"
  created_at: string; // ISO datetime
  primary_axis?: string | null;
  primary_delta?: number | null;
}

interface GapAnalysisContent {
  current_type: string;
  current_type_id?: number;
  aspiration_type: string;
  aspiration_type_id?: number;
  aspiration_description?: string;
  aspiration_features?: string[];
  current_coordinates: Coordinates;
  aspiration_coordinates: Coordinates;
  aesthetic_map?: {
    current: { x: number; y: number; size: number };
    aspiration: { x: number; y: number; size: number };
    x_axis: { name_kr: string; low: string; high: string; low_en: string; high_en: string };
    y_axis: { name_kr: string; low: string; high: string; low_en: string; high_en: string };
    size_axis: { name_kr: string; low: string; high: string };
    quadrants: { top_left: string; top_right: string; bottom_left: string; bottom_right: string };
    description?: string;
  };
  gap_magnitude: number;
  gap_difficulty: string;
  gap_summary: string;
  direction_items: DirectionItem[];
  // Phase B-4: 누적 추구미 분석 (vault.aspiration_history). 빈 배열이면 미렌더.
  aspiration_references?: AspirationReference[];
}

interface GapAnalysisProps {
  content: GapAnalysisContent;
  locked: boolean;
}

// 난이도 배지 스타일 — 프리미엄 모노크롬
function getDifficultyStyle(difficulty: string): string {
  if (difficulty.includes("큰")) {
    return "bg-[var(--color-fg)] text-[var(--color-bg)]";
  }
  return "border border-[var(--color-border)] text-[var(--color-muted)]";
}

// -1~+1 범위를 0~100% 위치로 변환
function scoreToPercent(score: number): number {
  return ((Math.max(-1, Math.min(1, score ?? 0)) + 1) / 2) * 100;
}

// ─── 3축 미니 비교 바 (컴팩트) ───
function MiniAxisRow({
  axisKey,
  label,
  currentScore,
  aspirationScore,
  labelLow,
  labelHigh,
  description,
}: {
  axisKey: string;
  label: string;
  currentScore: number;
  aspirationScore: number;
  labelLow?: string;
  labelHigh?: string;
  description?: string;
}) {
  const currentPos = scoreToPercent(currentScore);
  const aspirationPos = scoreToPercent(aspirationScore);
  const delta = Math.abs(aspirationScore - currentScore);

  return (
    <div className="flex items-center gap-2">
      {/* 축 라벨 + 설명 — 고정 폭 */}
      <div className="w-[56px] shrink-0 text-right">
        <span className="text-[11px] text-[var(--color-muted)] tracking-[0.5px] block">
          {label}
        </span>
        {description && (
          <span className="text-[8px] text-[var(--color-muted)] opacity-40 block leading-tight">
            {description}
          </span>
        )}
      </div>

      {/* 좌 라벨 */}
      {labelLow && (
        <span className="text-[8px] text-[var(--color-muted)] w-[36px] shrink-0 text-right opacity-60">
          {labelLow}
        </span>
      )}

      {/* 바 */}
      <div className="flex-1 relative h-[2px] bg-[var(--color-border)] rounded-full">
        <div className="absolute left-1/2 top-1/2 -translate-x-px -translate-y-1/2 w-[1px] h-[6px] bg-[var(--color-border)] opacity-60" />
        {delta > 0.05 && (
          <div
            className="absolute h-[2px] bg-[var(--color-fg)] opacity-15 rounded-full"
            style={{
              left: `${Math.min(currentPos, aspirationPos)}%`,
              width: `${Math.abs(aspirationPos - currentPos)}%`,
            }}
          />
        )}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[7px] h-[7px] rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]"
          style={{ left: `${currentPos}%`, marginLeft: "-3.5px" }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[7px] h-[7px] rounded-full bg-[var(--color-fg)]"
          style={{ left: `${aspirationPos}%`, marginLeft: "-3.5px" }}
        />
      </div>

      {/* 우 라벨 */}
      {labelHigh && (
        <span className="text-[8px] text-[var(--color-muted)] w-[36px] shrink-0 text-left opacity-60">
          {labelHigh}
        </span>
      )}
    </div>
  );
}

// ─── 방향 아이템 카드 — from→to 레인지 바 + delta + 추천 ───
function DirectionCard({ item }: { item: DirectionItem }) {
  const fromPos = scoreToPercent(item.from_score);
  const toPos = scoreToPercent(item.to_score);
  const barLeft = Math.min(fromPos, toPos);
  const barWidth = Math.abs(toPos - fromPos);

  return (
    <div className="p-4 border border-[var(--color-border)] rounded-lg">
      {/* 상단: 축 라벨 + 난이도 배지 */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold tracking-[1.5px] uppercase text-[var(--color-muted)]">
            {item.name_kr ?? item.label}
          </span>
          <span
            className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${getDifficultyStyle(item.difficulty)}`}
          >
            {item.difficulty}
          </span>
        </div>
      </div>

      {/* 축 설명 — 어떤 특징으로 계산되는지 */}
      {item.axis_description && (
        <p className="text-[10px] text-[var(--color-muted)] mb-3 opacity-70 leading-snug">
          {item.axis_description}
        </p>
      )}

      {/* from → to 라벨 */}
      <div className="flex items-center justify-between text-[11px] mb-1.5">
        <span className="text-[var(--color-muted)]">{item.from_label}</span>
        <span className="text-[var(--color-muted)] mx-1">→</span>
        <span className="font-semibold text-[var(--color-fg)]">
          {item.to_label}
        </span>
      </div>

      {/* 레인지 바: from→to */}
      <div className="mb-3">
        <div className="relative h-[3px] bg-[var(--color-border)] rounded-full">
          <div
            className="absolute h-full bg-[var(--color-fg)] rounded-full opacity-20"
            style={{ left: `${barLeft}%`, width: `${barWidth}%` }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 w-[8px] h-[8px] rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]"
            style={{ left: `${fromPos}%`, marginLeft: "-4px" }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 w-[8px] h-[8px] rounded-full bg-[var(--color-fg)]"
            style={{ left: `${toPos}%`, marginLeft: "-4px" }}
          />
        </div>
        {/* 축 양 끝 라벨 */}
        <div className="flex items-center justify-between text-[9px] mt-1.5 text-[var(--color-muted)] opacity-60">
          <span>{item.label_low ?? ""}</span>
          <span>{item.label_high ?? ""}</span>
        </div>
      </div>

      {/* 추천 텍스트 */}
      <p className="text-[13px] leading-relaxed">{item.recommendation}</p>
    </div>
  );
}

// ─── 메인: 추구미 갭 분석 ───
export function GapAnalysis({ content, locked }: GapAnalysisProps) {
  // type_id → 이미지 경로 (남성 11~18 → type_1m~8m, 여성 1~8 → type_1~8)
  const typeIdToImg = (id?: number) => {
    if (!id) return null;
    if (id >= 11 && id <= 18) return `/images/types/type_${id - 10}m.jpg`;
    return `/images/types/type_${id}.jpg`;
  };
  const currentImg = typeIdToImg(content.current_type_id);
  const aspirationImg = typeIdToImg(content.aspiration_type_id);

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-[11px] font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-8">
        GAP ANALYSIS
      </h2>

      {/* ─── 현재 → 추구 비주얼 카드 ─── */}
      <div className="flex items-start gap-4 mb-8">
        {/* 현재 유형 */}
        <div className="flex flex-col items-center gap-2 flex-1">
          {currentImg && (
            <div className="w-16 h-20 md:w-20 md:h-24 relative rounded-lg overflow-hidden bg-[var(--color-border)]">
              <Image
                src={currentImg}
                alt={content.current_type}
                fill
                className="object-cover opacity-70"
                sizes="80px"
              />
            </div>
          )}
          <span className="text-[10px] tracking-[1px] uppercase text-[var(--color-muted)]">
            현재
          </span>
          <span className="text-[13px] font-medium text-center leading-tight">
            {content.current_type}
          </span>
        </div>

        {/* 화살표 + 갭 크기 — 미니멀 */}
        <div className="flex flex-col items-center gap-1 shrink-0 px-2">
          <div className="w-10 md:w-14 h-px bg-[var(--color-border)]" />
          <span className="text-[var(--color-muted)] text-sm">&rarr;</span>
          <div className="w-10 md:w-14 h-px bg-[var(--color-border)]" />
          <span className="text-[9px] text-[var(--color-muted)] mt-1 tracking-[0.5px]">
            {content.gap_difficulty}
          </span>
        </div>

        {/* 추구 유형 */}
        <div className="flex flex-col items-center gap-2 flex-1">
          {aspirationImg && (
            <div className="w-16 h-20 md:w-20 md:h-24 relative rounded-lg overflow-hidden bg-[var(--color-border)] ring-2 ring-[var(--color-fg)]">
              <Image
                src={aspirationImg}
                alt={content.aspiration_type}
                fill
                className="object-cover"
                sizes="80px"
              />
            </div>
          )}
          <span className="text-[10px] tracking-[1px] uppercase text-[var(--color-muted)]">
            추구
          </span>
          <span className="text-[13px] font-bold text-center leading-tight">
            {content.aspiration_type}
          </span>
          {/* 추구 유형 특징 포인트 (1-12) */}
          {content.aspiration_features && content.aspiration_features.length > 0 ? (
            <ul className="mt-1.5 space-y-0.5 text-left list-none p-0 m-0">
              {content.aspiration_features.slice(0, 4).map((feat, i) => (
                <li key={i} className="text-[10px] text-[var(--color-muted)] leading-snug">
                  · {feat}
                </li>
              ))}
            </ul>
          ) : content.aspiration_description ? (
            <p className="text-[10px] text-[var(--color-muted)] text-center mt-1 leading-relaxed max-w-[120px]">
              {content.aspiration_description}
            </p>
          ) : null}
        </div>
      </div>

      {/* ─── 갭 오버뷰 카드: 산점도 + 3축 미니 비교 ─── */}
      <div className="mb-8 p-5 border border-[var(--color-border)] rounded-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-[11px] font-semibold tracking-[2px] uppercase text-[var(--color-muted)]">
            GAP OVERVIEW
          </h3>
          <span
            className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${getDifficultyStyle(content.gap_difficulty)}`}
          >
            {content.gap_difficulty}
          </span>
        </div>

        {/* 차트 읽기 안내 (Fix #14) */}
        <p className="text-[12px] text-[var(--color-muted)] mb-3 leading-relaxed">
          ○가 지금 위치, ●이 가고 싶은 위치예요.
        </p>

        {/* 2단 레이아웃: 산점도(좌) + 미니 비교(우) — 모바일은 스택 */}
        <div className="flex flex-col md:flex-row gap-6 items-start">
          {/* 산점도 */}
          {content.aesthetic_map && (
            <div className="w-full md:w-auto md:shrink-0">
              <GapScatterPlot
                aestheticMap={content.aesthetic_map}
                gapMagnitude={content.gap_magnitude}
              />
            </div>
          )}

          {/* 3축 미니 비교 바 */}
          <div className="w-full md:flex-1 md:pt-4">
            {/* 범례 */}
            <div className="flex items-center gap-4 mb-3 text-[9px] tracking-[0.5px] text-[var(--color-muted)]">
              <div className="flex items-center gap-1">
                <span className="w-[7px] h-[7px] rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]" />
                <span>현재</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-[7px] h-[7px] rounded-full bg-[var(--color-fg)]" />
                <span className="text-[var(--color-fg)]">추구</span>
              </div>
            </div>
            {/* 축별 바 */}
            <div className="flex flex-col gap-1">
              {content.direction_items.map((item) => (
                <MiniAxisRow
                  key={item.axis}
                  axisKey={item.axis}
                  label={item.name_kr ?? item.label}
                  currentScore={content.current_coordinates[item.axis as keyof Coordinates] ?? 0}
                  aspirationScore={content.aspiration_coordinates[item.axis as keyof Coordinates] ?? 0}
                  labelLow={item.label_low}
                  labelHigh={item.label_high}
                  description={item.axis_description}
                />
              ))}
            </div>
          </div>
        </div>

        {/* 차트 아래 안내 */}
        <p className="text-[11px] text-[var(--color-muted)] mt-4 leading-relaxed">
          {content.aesthetic_map?.description ?? "위 차트에서 ○가 지금 위치, ●이 가고 싶은 위치예요."}
        </p>
      </div>

      {/* ─── 갭 요약 ─── */}
      <p className="text-[15px] leading-relaxed font-serif mb-8">
        {content.gap_summary}
      </p>

      {/* ─── 상세 방향 카드 — 잠금 시 블러 ─── */}
      <div className={locked ? "select-none" : ""}>
        <div className="relative">
          <div className="flex flex-col gap-4">
            {content.direction_items.map((item) => (
              <DirectionCard key={item.axis} item={item} />
            ))}
          </div>

          {/* 블러 오버레이 */}
          {locked && (
            <div className="absolute inset-0 blur-overlay blur-fade-out rounded-lg" />
          )}
        </div>
      </div>

      {/* ─── Phase B-4: 누적 추구미 분석 카드 ─── */}
      {content.aspiration_references && content.aspiration_references.length > 0 && (
        <div className="mt-10">
          <h3 className="text-[11px] font-semibold tracking-[2px] uppercase text-[var(--color-muted)] mb-3">
            누적 추구미 분석 ({content.aspiration_references.length})
          </h3>
          <p className="text-[12px] text-[var(--color-muted)] mb-4 leading-relaxed">
            지금까지 본인이 분석한 추구미 결과예요. 쌓일수록 좌표가 더 정교해져요.
          </p>
          <div className="flex flex-col gap-3">
            {content.aspiration_references.map((entry, i) => (
              <AspirationReferenceCard key={i} entry={entry} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// ─── Phase B-4: 누적 추구미 분석 카드 ───
function AspirationReferenceCard({ entry }: { entry: AspirationReference }) {
  // 날짜 포맷: "2026년 4월 26일"
  const dateLabel = (() => {
    if (!entry.created_at) return "";
    try {
      const d = new Date(entry.created_at);
      if (isNaN(d.getTime())) return "";
      return d.toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return "";
    }
  })();

  const sourceLabel = entry.source === "pinterest" ? "Pinterest" : "Instagram";
  const handleDisplay = entry.target_handle.startsWith("@")
    ? entry.target_handle
    : `@${entry.target_handle}`;

  // 좌표 메타 라벨 (있으면)
  const axisLabelMap: Record<string, string> = {
    shape: "골격",
    volume: "존재감",
    age: "무드",
  };
  const directionLabel = (() => {
    if (!entry.primary_axis || entry.primary_delta == null) return "";
    const axisKr = axisLabelMap[entry.primary_axis] ?? entry.primary_axis;
    const dir = entry.primary_delta > 0 ? "+" : "";
    return `${axisKr} ${dir}${entry.primary_delta}`;
  })();

  return (
    <div className="p-4 border border-[var(--color-border)] rounded-lg">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold tracking-[1px] uppercase text-[var(--color-muted)]">
            {sourceLabel}
          </span>
          <span className="text-[12px] font-medium text-[var(--color-fg)]">
            {handleDisplay}
          </span>
        </div>
        {dateLabel && (
          <span className="text-[10px] text-[var(--color-muted)]">{dateLabel}</span>
        )}
      </div>
      {directionLabel && (
        <div className="text-[11px] text-[var(--color-muted)] tracking-[0.5px]">
          주요 갭: {directionLabel}
        </div>
      )}
    </div>
  );
}
