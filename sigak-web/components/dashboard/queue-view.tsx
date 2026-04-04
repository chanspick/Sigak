"use client";

import type { QueueUser, BookingStatus } from "@/lib/types/dashboard";
import { TIER_MAP, STATUS_MAP } from "@/lib/constants/mock-data";

interface QueueViewProps {
  queue: QueueUser[];
  onSelect: (user: QueueUser) => void;
}

// 상태별 뱃지 스타일 반환
function getBadgeClasses(status: BookingStatus): string {
  switch (status) {
    case "booked":
      // 연한 배경
      return "bg-black/[0.06] text-[var(--color-fg)]";
    case "reported":
    case "feedback_done":
      // 검은 배경 + 밝은 글자
      return "bg-black/[0.85] text-[var(--color-bg)]";
    default:
      // 인터뷰 완료, 분석 중 등 — 중간 톤 배경
      return "bg-black/[0.12] text-[var(--color-fg)]";
  }
}

// 진행 도트 컴포넌트 (인터뷰/사진/리포트)
function ProgressDot({ filled, title }: { filled: boolean; title: string }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full transition-colors duration-200 ${
        filled ? "bg-[var(--color-fg)]" : "bg-black/10"
      }`}
      title={title}
      aria-label={`${title}: ${filled ? "완료" : "미완료"}`}
    />
  );
}

// 대기열 뷰 — 날짜별 유저 그룹핑
export function QueueView({ queue, onSelect }: QueueViewProps) {
  // 날짜별로 유저를 그룹핑
  const groups: Record<string, QueueUser[]> = {};
  queue.forEach((u) => {
    const d = u.booking_date;
    if (!groups[d]) groups[d] = [];
    groups[d].push(u);
  });

  return (
    <div>
      {/* 페이지 제목 */}
      <h2 className="font-[family-name:var(--font-serif)] text-[clamp(22px,3vw,30px)] font-normal leading-[1.3]">
        대기열
      </h2>
      <p className="text-[13px] opacity-40 mt-1.5">
        인터뷰 예정 및 진행 중인 유저
      </p>

      {/* 구분선 */}
      <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />

      {/* 날짜별 그룹 */}
      {Object.entries(groups).map(([date, users]) => (
        <div key={date}>
          {/* 날짜 라벨 */}
          <p className="text-[11px] font-semibold tracking-[1.5px] opacity-30 mb-2.5">
            {date.replace("2026-", "")}
          </p>

          {/* 유저 행들 */}
          {users.map((u) => (
            <button
              key={u.id}
              type="button"
              className="flex w-full justify-between items-center py-3.5 cursor-pointer transition-opacity duration-150 hover:opacity-80 text-left bg-transparent border-none"
              onClick={() => onSelect(u)}
              aria-label={`${u.name} - ${STATUS_MAP[u.status]}`}
            >
              {/* 왼쪽: 이름 + 메타 */}
              <div className="flex flex-col gap-1">
                <span className="text-[15px] font-semibold">{u.name}</span>
                <span className="text-xs opacity-40">
                  {TIER_MAP[u.tier]} · {u.booking_time}
                </span>
              </div>

              {/* 오른쪽: 상태 뱃지 + 진행 도트 */}
              <div className="flex items-center gap-3">
                {/* 상태 뱃지 */}
                <span
                  className={`text-[10px] font-semibold tracking-[0.5px] px-2.5 py-1 rounded ${getBadgeClasses(
                    u.status
                  )}`}
                >
                  {STATUS_MAP[u.status]}
                </span>

                {/* 진행 도트 3개 */}
                <div className="flex gap-1" aria-label="진행 상태">
                  <ProgressDot filled={u.has_interview} title="인터뷰" />
                  <ProgressDot filled={u.has_photos} title="사진" />
                  <ProgressDot filled={u.has_report} title="리포트" />
                </div>
              </div>
            </button>
          ))}

          {/* 그룹 구분선 */}
          <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />
        </div>
      ))}
    </div>
  );
}
