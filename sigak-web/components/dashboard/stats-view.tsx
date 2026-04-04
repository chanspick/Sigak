// 가설 검증 지표 뷰 (Server Component 가능)

import type { DashboardStats } from "@/lib/types/dashboard";
import { StatCard } from "./stat-card";

interface StatsViewProps {
  stats: DashboardStats;
}

// 가설 검증 지표 뷰 — H1 Market, H2 Product, H4 Growth 섹션
export function StatsView({ stats }: StatsViewProps) {
  return (
    <div>
      {/* 페이지 제목 */}
      <h2 className="font-[family-name:var(--font-serif)] text-[clamp(22px,3vw,30px)] font-normal leading-[1.3]">
        가설 검증 지표
      </h2>
      <p className="text-[13px] opacity-40 mt-1.5">
        트랙아웃 2주 스프린트 대시보드
      </p>

      {/* 구분선 */}
      <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />

      {/* H1: MARKET — 시장 검증 지표 */}
      <div className="mb-8">
        <p className="text-[10px] font-bold tracking-[2.5px] opacity-30 mb-4 uppercase">
          H1 — MARKET
        </p>
        <div className="grid grid-cols-3 border border-black/[0.08]">
          <StatCard
            label="총 예약"
            value={stats.total_bookings}
            unit="건"
          />
          <StatCard
            label="인터뷰 완료"
            value={stats.interviewed}
            unit="건"
          />
          <StatCard
            label="리포트 발송"
            value={stats.reports_sent}
            unit="건"
          />
        </div>
      </div>

      {/* H2: PRODUCT — 제품 만족도 지표 */}
      <div className="mb-8">
        <p className="text-[10px] font-bold tracking-[2.5px] opacity-30 mb-4 uppercase">
          H2 — PRODUCT
        </p>
        <div className="grid grid-cols-3 border border-black/[0.08]">
          <StatCard
            label="만족도 평균"
            value={stats.avg_satisfaction}
            unit="/ 5"
            alert={stats.avg_satisfaction < stats.nps_target}
          />
          <StatCard
            label="유용성 평균"
            value={stats.avg_usefulness}
            unit="/ 5"
            target="목표 4.2"
            alert={stats.avg_usefulness < stats.nps_target}
          />
          <StatCard
            label="피드백 수집"
            value={stats.feedbacks_received}
            unit="건"
          />
        </div>
      </div>

      {/* H4: GROWTH — 성장 지표 */}
      <div className="mb-8">
        <p className="text-[10px] font-bold tracking-[2.5px] opacity-30 mb-4 uppercase">
          H4 — GROWTH
        </p>
        <div className="grid grid-cols-3 border border-black/[0.08]">
          <StatCard
            label="B2B Opt-in"
            value={stats.b2b_opt_in_rate}
            unit="%"
          />
          <StatCard
            label="재구매 의향"
            value={stats.repurchase_rate}
            unit="%"
          />
          {/* 세 번째 칸: 빈 셀로 그리드 정렬 유지 */}
          <div className="px-[22px] py-5 border-r border-black/[0.08] last:border-r-0" />
        </div>
      </div>
    </div>
  );
}
