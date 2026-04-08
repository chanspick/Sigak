// 추구미 갭 분석 섹션 (standard 잠금)
// 프리미엄 컨설팅 리포트 스타일: 정량 좌표 기반 비주얼 방향 시각화
// 구조: 헤더 → 유형 카드 → 갭 오버뷰(산점도+미니바) → 요약 → 방향 카드

import Image from "next/image";
import { GapScatterPlot } from "@/components/report/charts/gap-scatter-plot";

// 4축 좌표 타입
interface Coordinates {
  structure: number;
  impression: number;
  maturity: number;
  intensity: number;
}

interface DirectionItem {
  axis: string;
  label: string;
  from_score: number;
  to_score: number;
  delta: number;
  from_label: string;
  to_label: string;
  difficulty: string;
  recommendation: string;
}

interface GapAnalysisContent {
  current_type: string;
  current_type_id?: number;
  aspiration_type: string;
  aspiration_type_id?: number;
  current_coordinates: Coordinates;
  aspiration_coordinates: Coordinates;
  gap_magnitude: number;
  gap_difficulty: string;
  gap_summary: string;
  direction_items: DirectionItem[];
}

interface GapAnalysisProps {
  content: GapAnalysisContent;
  locked: boolean;
}

// 축 라벨 매핑 (영문 키 → 한글)
const AXIS_LABELS: Record<string, string> = {
  structure: "Structure",
  impression: "Impression",
  maturity: "Maturity",
  intensity: "Presence",
};

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

// ─── 4축 미니 비교 바 (컴팩트 24px 높이) ───
function MiniAxisRow({
  label,
  currentScore,
  aspirationScore,
}: {
  label: string;
  currentScore: number;
  aspirationScore: number;
}) {
  const currentPos = scoreToPercent(currentScore);
  const aspirationPos = scoreToPercent(aspirationScore);
  const delta = Math.abs(aspirationScore - currentScore);

  return (
    <div className="flex items-center gap-2 h-[24px]">
      {/* 축 라벨 — 고정 폭 */}
      <span className="text-[11px] text-[var(--color-muted)] w-[42px] shrink-0 text-right tracking-[0.5px]">
        {label}
      </span>

      {/* 바 — 얇고 정밀한 느낌 */}
      <div className="flex-1 relative h-[2px] bg-[var(--color-border)] rounded-full">
        {/* 중심선 (0 위치) */}
        <div className="absolute left-1/2 top-1/2 -translate-x-px -translate-y-1/2 w-[1px] h-[6px] bg-[var(--color-border)] opacity-60" />
        {/* 이동 범위 강조 (현재→추구 사이 얇은 바) */}
        {delta > 0.05 && (
          <div
            className="absolute h-[2px] bg-[var(--color-fg)] opacity-15 rounded-full"
            style={{
              left: `${Math.min(currentPos, aspirationPos)}%`,
              width: `${Math.abs(aspirationPos - currentPos)}%`,
            }}
          />
        )}
        {/* 현재 마커 — 빈 원 */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[7px] h-[7px] rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]"
          style={{ left: `${currentPos}%`, marginLeft: "-3.5px" }}
        />
        {/* 추구 마커 — 채운 원 */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[7px] h-[7px] rounded-full bg-[var(--color-fg)]"
          style={{ left: `${aspirationPos}%`, marginLeft: "-3.5px" }}
        />
      </div>

      {/* 변화 표시 */}
      <span className="text-[10px] text-[var(--color-muted)] w-[20px] shrink-0 text-right">
        {delta > 0.05 ? "→" : "·"}
      </span>
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
      {/* 상단: 축 라벨 + 난이도 배지 + delta */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold tracking-[1.5px] uppercase text-[var(--color-muted)]">
            {item.label}
          </span>
          <span
            className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${getDifficultyStyle(item.difficulty)}`}
          >
            {item.difficulty}
          </span>
        </div>
        <span className="text-[11px] font-semibold text-[var(--color-fg)]">
          {item.difficulty}
        </span>
      </div>

      {/* from → to 라벨 */}
      <div className="flex items-center justify-between text-[11px] mb-1.5">
        <span className="text-[var(--color-muted)]">{item.from_label}</span>
        <span className="font-semibold text-[var(--color-fg)]">
          {item.to_label}
        </span>
      </div>

      {/* 레인지 바: from→to */}
      <div className="mb-3">
        <div className="relative h-[3px] bg-[var(--color-border)] rounded-full">
          {/* 이동 범위 강조 */}
          <div
            className="absolute h-full bg-[var(--color-fg)] rounded-full opacity-20"
            style={{ left: `${barLeft}%`, width: `${barWidth}%` }}
          />
          {/* 현재 마커 — 빈 원 */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-[8px] h-[8px] rounded-full border-[1.5px] border-[var(--color-muted)] bg-[var(--color-bg)]"
            style={{ left: `${fromPos}%`, marginLeft: "-4px" }}
          />
          {/* 목표 마커 — 채운 원 */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-[8px] h-[8px] rounded-full bg-[var(--color-fg)]"
            style={{ left: `${toPos}%`, marginLeft: "-4px" }}
          />
        </div>
        {/* 라벨 텍스트 */}
        <div className="flex items-center justify-between text-[10px] mt-1.5">
          <span className="text-[var(--color-muted)]">
            {item.from_label}
          </span>
          <span className="font-semibold text-[var(--color-fg)]">
            {item.to_label}
          </span>
        </div>
      </div>

      {/* 추천 텍스트 */}
      <p className="text-[13px] leading-relaxed">{item.recommendation}</p>
    </div>
  );
}

// ─── 메인: 추구미 갭 분석 ───
export function GapAnalysis({ content, locked }: GapAnalysisProps) {
  const currentImg = content.current_type_id
    ? `/images/types/type_${content.current_type_id}.jpg`
    : null;
  const aspirationImg = content.aspiration_type_id
    ? `/images/types/type_${content.aspiration_type_id}.jpg`
    : null;

  const axisKeys = Object.keys(AXIS_LABELS) as (keyof Coordinates)[];

  return (
    <section className="py-10 border-b border-[var(--color-border)]">
      {/* 섹션 헤더 */}
      <h2 className="text-[11px] font-semibold tracking-[3px] uppercase text-[var(--color-muted)] mb-8">
        GAP ANALYSIS
      </h2>

      {/* ─── 현재 → 추구 비주얼 카드 ─── */}
      <div className="flex items-center gap-4 mb-8">
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
        </div>
      </div>

      {/* ─── 갭 오버뷰 카드: 산점도 + 4축 미니 비교 ─── */}
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

        {/* 2단 레이아웃: 산점도(좌) + 미니 비교(우) — 모바일은 스택 */}
        <div className="flex flex-col md:flex-row gap-6 items-start">
          {/* 산점도 */}
          <div className="w-full md:w-auto md:shrink-0">
            <GapScatterPlot
              current={content.current_coordinates}
              aspiration={content.aspiration_coordinates}
              gapMagnitude={content.gap_magnitude}
            />
          </div>

          {/* 4축 미니 비교 바 */}
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
              {axisKeys.map((key) => (
                <MiniAxisRow
                  key={key}
                  label={AXIS_LABELS[key]}
                  currentScore={content.current_coordinates[key]}
                  aspirationScore={content.aspiration_coordinates[key]}
                />
              ))}
            </div>
          </div>
        </div>
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
    </section>
  );
}
