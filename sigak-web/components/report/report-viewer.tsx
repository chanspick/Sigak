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
import { getReport, requestUpgrade } from "@/lib/api/client";
import { SectionRenderer } from "./section-renderer";
import { PaywallGate } from "./paywall-gate";
import { ShareButtons } from "./share-buttons";

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

  // 결제 완료 처리 — API 호출 + pending 상태 전환
  const handlePaymentComplete = useCallback(async (level: UnlockLevel) => {
    if (level === "full") {
      // ₩44,000 업그레이드 요청 → 백엔드 + 웹훅
      try {
        await requestUpgrade(report.id);
      } catch (e) {
        console.error("[upgrade-request]", e);
      }
    }
    // pending 상태로 전환 (폴링 시작됨)
    setReport((prev) => ({
      ...prev,
      access_level: level === "standard" ? "standard_pending" : "full_pending",
      pending_level: level,
    }));
  }, [report.id]);

  // access_level 변경 감지 → 스크롤 위치 유지
  useEffect(() => {
    if (prevAccessLevelRef.current !== report.access_level) {
      const scrollY = window.scrollY;
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollY);
      });
      prevAccessLevelRef.current = report.access_level;
    }
  }, [report.access_level]);

  // pending 상태 폴링 (30초 간격) — 실제 API 호출
  useEffect(() => {
    const isPending = report.access_level.includes("pending");
    if (!isPending) return;

    const cleanup = startPolling(
      async () => {
        return await getReport(report.id);
      },
      {
        interval: 30000,
        onData: (data) => {
          const newReport = data as ReportData;
          if (newReport.access_level !== report.access_level) {
            const scrollY = window.scrollY;
            setReport(newReport);
            requestAnimationFrame(() => window.scrollTo(0, scrollY));
          }
        },
      },
    );

    return cleanup;
  }, [report.access_level, report.id]);

  // pending 요청 시각 (PendingCard에 전달)
  const pendingAt = report.pending_level
    ? new Date().toISOString()
    : null;

  const userName = report.user_name || "회원";

  return (
    <div className="max-w-2xl mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
      {report.sections.map((section) => (
        <div key={section.id}>
          {/* 섹션 렌더링 */}
          <SectionRenderer
            section={section}
            accessLevel={report.access_level}
            overlay={(report as unknown as { overlay?: { before_url: string; after_url: string } }).overlay ?? null}
          />

          {/* 해당 레벨 그룹의 마지막 섹션 뒤에 PaywallGate 삽입 */}
          {lastSectionMap[section.id] && report.paywall?.[lastSectionMap[section.id]] && report.payment_account && (
            <PaywallGate
              level={lastSectionMap[section.id]}
              accessLevel={report.access_level}
              paywall={report.paywall[lastSectionMap[section.id]]!}
              paymentAccount={report.payment_account}
              pendingAt={pendingAt}
              onPaymentComplete={() =>
                handlePaymentComplete(lastSectionMap[section.id])
              }
            />
          )}
        </div>
      ))}

      {/* 리포트 하단 — 공유 버튼 */}
      <div className="py-10 border-t border-[var(--color-border)]">
        <p className="text-xs text-center text-[var(--color-muted)] mb-4">
          리포트가 마음에 드셨나요? 친구에게 공유해보세요
        </p>
        <ShareButtons
          title={`${userName}님의 시각 리포트`}
          description="AI 이목구비 분석 · 퍼스널 스타일링 리포트"
        />
      </div>

      {/* 리포트 하단 여백 */}
      <div className="h-10" />
    </div>
  );
}
