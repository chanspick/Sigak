"use client";

// 리포트 뷰어 메인 오케스트레이터
// 1. sections를 순서대로 렌더링 (section-renderer 사용)
// 2. 각 unlock_level 그룹의 마지막 섹션 뒤에 PaywallGate 삽입
// 3. pending 상태면 30초 폴링 시작 (startPolling 사용)
// 4. access_level 변경 감지 시 블러 fade-out + 스크롤 위치 유지
// 5. visibilitychange로 탭 비활성 시 폴링 중지

import { useState, useEffect, useRef, useCallback } from "react";
import type { ReportData, UnlockLevel } from "@/lib/types/report";
import { getLastSectionOfLevel, getPaywallGateLevels } from "@/lib/utils/report";
import { startPolling } from "@/lib/utils/polling";
import { SectionRenderer } from "./section-renderer";
import { PaywallGate } from "./paywall-gate";

interface ReportViewerProps {
  initialReport: ReportData;
}

// 리포트 뷰어 - 섹션 렌더링, 페이월 게이트, 폴링을 통합 관리
export function ReportViewer({ initialReport }: ReportViewerProps) {
  // 리포트 상태 (폴링으로 업데이트)
  const [report, setReport] = useState<ReportData>(initialReport);
  // 이전 access_level 추적 (fade-out 트리거용)
  const prevAccessLevelRef = useRef(report.access_level);

  // 페이월 게이트를 표시할 레벨 목록
  const gateLevels = getPaywallGateLevels(report.access_level);

  // 각 unlock_level 그룹의 마지막 섹션 ID 매핑
  const lastSectionMap: Record<string, UnlockLevel> = {};
  const levels: UnlockLevel[] = ["standard", "full"];
  for (const level of levels) {
    const lastId = getLastSectionOfLevel(report.sections, level);
    if (lastId && gateLevels.includes(level)) {
      lastSectionMap[lastId] = level;
    }
  }

  // 결제 완료 처리 (pending 상태로 전환)
  const handlePaymentComplete = useCallback((level: UnlockLevel) => {
    // 실제로는 POST /api/v1/payment-request 호출
    // mock: access_level을 pending으로 변경
    setReport((prev) => ({
      ...prev,
      access_level: level === "standard" ? "standard_pending" : "full_pending",
      pending_level: level,
    }));
  }, []);

  // access_level 변경 감지 → 스크롤 위치 유지
  useEffect(() => {
    if (prevAccessLevelRef.current !== report.access_level) {
      // pending → unlocked 전환 시 스크롤 위치 보존
      const scrollY = window.scrollY;
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollY);
      });
      prevAccessLevelRef.current = report.access_level;
    }
  }, [report.access_level]);

  // pending 상태 폴링 (30초 간격)
  useEffect(() => {
    const isPending = report.access_level.includes("pending");
    if (!isPending) return;

    const cleanup = startPolling(
      async () => {
        // mock: 실제로는 fetch(`/api/v1/report/${report.id}`)
        // 현재는 상태 변경 없음 (관리자 확인 시 변경됨)
        return report;
      },
      {
        interval: 30000,
        onData: (data) => {
          const newReport = data as ReportData;
          if (newReport.access_level !== report.access_level) {
            // 스크롤 위치 저장
            const scrollY = window.scrollY;
            setReport(newReport);
            // fade-out 후 스크롤 복원
            requestAnimationFrame(() => window.scrollTo(0, scrollY));
          }
        },
      },
    );

    return cleanup;
  }, [report.access_level, report.id, report]);

  // pending 요청 시각 (PendingCard에 전달)
  const pendingAt = report.pending_level
    ? new Date().toISOString()
    : null;

  return (
    <div className="max-w-2xl mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
      {report.sections.map((section) => (
        <div key={section.id}>
          {/* 섹션 렌더링 */}
          <SectionRenderer
            section={section}
            accessLevel={"full" as any} // TODO: 피드백용 임시 해제 — 배포 전 복구
            overlay={(report as any).overlay ?? null}
          />

          {/* 해당 레벨 그룹의 마지막 섹션 뒤에 PaywallGate 삽입 */}
          {lastSectionMap[section.id] && (
            <PaywallGate
              level={lastSectionMap[section.id]}
              accessLevel={report.access_level}
              paywall={report.paywall[lastSectionMap[section.id]]}
              paymentAccount={report.payment_account}
              pendingAt={pendingAt}
              onPaymentComplete={() =>
                handlePaymentComplete(lastSectionMap[section.id])
              }
            />
          )}
        </div>
      ))}

      {/* 리포트 하단 여백 */}
      <div className="h-20" />
    </div>
  );
}
