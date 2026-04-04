"use client";

import { useState } from "react";
import type { DashboardView, QueueUser } from "@/lib/types/dashboard";
import type { PaymentRequest } from "@/lib/types/payment";
import { MOCK_QUEUE, MOCK_STATS } from "@/lib/constants/mock-data";
import { MOCK_PAYMENTS } from "@/lib/constants/mock-payments";
import { QueueView } from "@/components/dashboard/queue-view";
import { EntryView } from "@/components/dashboard/entry-view";
import { StatsView } from "@/components/dashboard/stats-view";
import { PaymentsView } from "@/components/dashboard/payments-view";

// 대시보드 메인 페이지 — Nav + 4개 뷰 전환 (queue, entry, stats, payments)
export default function DashboardPage() {
  // 현재 뷰 상태
  const [view, setView] = useState<DashboardView>("queue");
  // 대기열 데이터
  const [queue] = useState<QueueUser[]>(MOCK_QUEUE);
  // 통계 데이터
  const [stats] = useState(MOCK_STATS);
  // 결제 데이터
  const [payments] = useState<PaymentRequest[]>(MOCK_PAYMENTS);
  // 선택된 유저 (entry 뷰에서 사용)
  const [selectedUser, setSelectedUser] = useState<QueueUser | null>(null);

  // 유저 선택 → entry 뷰로 전환
  const openEntry = (user: QueueUser) => {
    setSelectedUser(user);
    setView("entry");
  };

  // entry 뷰에서 대기열로 복귀
  const backToQueue = () => {
    setView("queue");
    setSelectedUser(null);
  };

  return (
    <div>
      {/* 네비게이션 바: 스티키 검은 바, SIGAK 로고, 탭 전환 */}
      <nav className="sticky top-0 z-[100] flex items-center gap-4 px-10 h-14 bg-[var(--color-fg)] text-[var(--color-bg)]">
        {/* 로고 */}
        <span className="text-xs font-bold tracking-[5px]">SIGAK</span>
        {/* 서브타이틀 */}
        <span className="text-[10px] font-medium tracking-[2.5px] opacity-40">
          INTERVIEWER DASHBOARD
        </span>
        {/* 스페이서 */}
        <div className="flex-1" />
        {/* 대기열 탭 */}
        <button
          type="button"
          className={`bg-transparent border-none text-[var(--color-bg)] text-[11px] font-semibold tracking-[1.5px] cursor-pointer px-4 py-2 transition-opacity duration-200 ${
            view === "queue" || view === "entry" ? "opacity-100" : "opacity-40"
          } hover:opacity-80`}
          onClick={() => setView("queue")}
        >
          대기열
        </button>
        {/* 결제 탭 */}
        <button
          type="button"
          className={`bg-transparent border-none text-[var(--color-bg)] text-[11px] font-semibold tracking-[1.5px] cursor-pointer px-4 py-2 transition-opacity duration-200 ${
            view === "payments" ? "opacity-100" : "opacity-40"
          } hover:opacity-80`}
          onClick={() => setView("payments")}
        >
          결제
        </button>
        {/* 지표 탭 */}
        <button
          type="button"
          className={`bg-transparent border-none text-[var(--color-bg)] text-[11px] font-semibold tracking-[1.5px] cursor-pointer px-4 py-2 transition-opacity duration-200 ${
            view === "stats" ? "opacity-100" : "opacity-40"
          } hover:opacity-80`}
          onClick={() => setView("stats")}
        >
          지표
        </button>
      </nav>

      {/* 콘텐츠 영역 */}
      <div className="max-w-[720px] mx-auto px-10 pt-8 pb-20">
        {view === "queue" && (
          <QueueView queue={queue} onSelect={openEntry} />
        )}
        {view === "entry" && selectedUser && (
          <EntryView user={selectedUser} onBack={backToQueue} />
        )}
        {view === "payments" && <PaymentsView payments={payments} />}
        {view === "stats" && <StatsView stats={stats} />}
      </div>
    </div>
  );
}
