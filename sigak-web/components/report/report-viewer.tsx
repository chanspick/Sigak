"use client";

// 리포트 뷰어 메인 오케스트레이터
// 1. sections를 순서대로 렌더링 (section-renderer 사용)
// 2. 각 unlock_level 그룹의 마지막 섹션 뒤에 PaywallGate 삽입
// 3. pending 상태면 30초 폴링 시작 (startPolling 사용)
// 4. access_level 변경 감지 시 블러 fade-out + 스크롤 위치 유지
// 5. visibilitychange로 탭 비활성 시 폴링 중지

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import type { ReportData, UnlockLevel } from "@/lib/types/report";
import { getLastSectionOfLevel, getPaywallGateLevels } from "@/lib/utils/report";
import { startPolling } from "@/lib/utils/polling";
import { getReport, requestUpgrade } from "@/lib/api/client";
import { SectionRenderer } from "./section-renderer";
import { PaywallGate } from "./paywall-gate";
import { ShareButtons } from "./share-buttons";
import { FinaleStepsCard } from "@/components/finale/FinaleStepsCard";
// Phase B-6 (PI-REVIVE 2026-04-26): CastingOptInBanner import 제거.
// 본인 결정: 캐스팅 풀 영역 리포트 하단에서 노출 X.
// CastingOptInBanner 컴포넌트 자체는 보존 (v1.5+ 부활 가능).

interface ReportViewerProps {
  initialReport: ReportData;
}

// 리포트 뷰어 - 섹션 렌더링, 페이월 게이트, 폴링을 통합 관리
export function ReportViewer({ initialReport }: ReportViewerProps) {
  // 리포트 상태 (폴링으로 업데이트)
  const [report, setReport] = useState<ReportData>(initialReport);
  // 이전 access_level 추적 (fade-out 트리거용)
  const prevAccessLevelRef = useRef(report.access_level);

  // 소유권 검증: 이미 로그인된 본인 리포트일 때만 컨텍스트 보존
  // 미로그인 or 타인 리포트 → localStorage 건드리지 않음 (공유 링크 보안)
  useEffect(() => {
    // 애널리틱스: 리포트 조회
    import("@/lib/analytics").then(({ trackReportViewed }) => {
      trackReportViewed(report.id, report.access_level);
    });
  }, [report.id, report.access_level]);

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

  const router = useRouter();

  // 토스 위젯용 주문 ID 상태
  const [tossOrderId, setTossOrderId] = useState<string | null>(null);

  // 업그레이드 결제 — 주문 생성 + 결제 플로우 분기
  const handlePaymentComplete = useCallback(async (level: UnlockLevel) => {
    if (level === "full") {
      try {
        const res = await requestUpgrade(report.id);
        if (res.payment_info) {
          const p = res.payment_info;
          const paywall = report.paywall?.full;

          // 토스 위젯 결제 모드: 주문 ID만 저장 → PaywallGate가 위젯 표시
          if (paywall?.method === "auto" && res.order_id) {
            setTossOrderId(res.order_id);
            return;
          }

          // 수동 결제 모드: 결제 안내 페이지로 이동
          const params = new URLSearchParams({
            order_id: res.order_id || "",
            amount: String(p.amount),
            bank: p.bank,
            account: p.account,
            holder: p.holder,
            toss: (p as unknown as Record<string, string>).toss_deeplink || "",
            kakao: (p as unknown as Record<string, string>).kakao_deeplink || "",
          });
          router.push(`/questionnaire/payment?${params.toString()}`);
          return;
        }
        // payment_info 없으면 이미 풀 결제 완료 상태
        if (res.status === "already_full") {
          window.location.reload();
          return;
        }
      } catch (e) {
        console.error("[upgrade-request]", e);
        alert("주문 생성에 실패했습니다. 잠시 후 다시 시도해주세요.");
        return;
      }
    }
    // fallback: pending 상태 전환
    setReport((prev) => ({
      ...prev,
      access_level: level === "standard" ? "standard_pending" : "full_pending",
      pending_level: level,
    }));
  }, [report.id, report.paywall, router]);

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
          {/* 섹션 렌더링 — Phase B-2.5: overlay/hair_simulation props 제거 */}
          <SectionRenderer
            section={section}
            accessLevel={report.access_level}
          />

          {/* 해당 레벨 그룹의 마지막 섹션 뒤에 PaywallGate 삽입 */}
          {lastSectionMap[section.id] && report.paywall?.[lastSectionMap[section.id]] && report.payment_account && (
            <PaywallGate
              level={lastSectionMap[section.id]}
              accessLevel={report.access_level}
              paywall={report.paywall[lastSectionMap[section.id]]!}
              paymentAccount={report.payment_account}
              pendingAt={pendingAt}
              orderId={tossOrderId || undefined}
              onPaymentComplete={() =>
                handlePaymentComplete(lastSectionMap[section.id])
              }
            />
          )}
        </div>
      ))}

      {/* SPEC-PI-FINALE-001 Card 2 — 4-step (디저트). 공유하기 위에 위치.
          report.sia_finale 미존재 시 컴포넌트 자체가 null 반환 (graceful). */}
      <FinaleStepsCard finale={report.sia_finale} />

      {/* 리포트 하단 — 공유 버튼 */}
      <div className="py-10 border-t border-[var(--color-line)]">
        <p className="text-xs text-center text-[var(--color-muted)] mb-4">
          리포트가 마음에 드셨나요? 친구에게 공유해보세요
        </p>
        <ShareButtons
          title={`${userName}님의 시각 리포트`}
          description="AI 이목구비 분석 · 퍼스널 스타일링 리포트"
        />
      </div>

      {/* Phase B-6: 캐스팅 풀 opt-in 영역 제거 (본인 결정 2026-04-26).
          CastingOptInBanner 컴포넌트 자체는 보존 — v1.5+ 부활 시 복원. */}

      {/* 리포트 하단 여백 */}
      <div className="h-10" />
    </div>
  );
}
