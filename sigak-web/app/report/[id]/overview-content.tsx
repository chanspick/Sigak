"use client";

// 오버뷰 랜딩 콘텐츠 (클라이언트 컴포넌트)
// - cover + executive_summary 전체 공개
// - 잠금 섹션은 teaser 카드로 표시
// - CTA 결제 버튼 + 공유 버튼
// - 이미 결제된 경우 → /report/[id]/full 자동 이동 안내

import { useRouter } from "next/navigation";
import type { ReportData, ReportSection } from "@/lib/types/report";
import { Cover } from "@/components/report/sections/cover";
import { ExecutiveSummary } from "@/components/report/sections/executive-summary";
import { ShareButtons } from "@/components/report/share-buttons";

interface OverviewContentProps {
  report: ReportData;
  reportId: string;
}

// 섹션 ID → 한글 라벨 매핑
const SECTION_LABELS: Record<string, string> = {
  face_structure: "얼굴 구조 분석",
  skin_analysis: "퍼스널 컬러 분석",
  gap_analysis: "추구미 갭 분석",
  coordinate_map: "미감 좌표 맵",
  hair_recommendation: "헤어 추천",
  action_plan: "액션 플랜",
  type_reference: "유형 레퍼런스",
  celeb_reference: "셀럽 레퍼런스",
  trend_context: "트렌드 컨텍스트",
};

// teaser에서 헤드라인 텍스트 추출
function getTeaserText(section: ReportSection): string | null {
  if (!section.teaser) return null;
  if ("headline" in section.teaser && section.teaser.headline) {
    return section.teaser.headline as string;
  }
  if ("categories" in section.teaser && Array.isArray(section.teaser.categories)) {
    return (section.teaser.categories as string[]).join(" · ");
  }
  return null;
}

export function OverviewContent({ report, reportId }: OverviewContentProps) {
  const router = useRouter();

  // 이미 결제 완료된 경우
  const isPaid = ["standard", "full_pending", "full"].includes(report.access_level);

  // cover / executive_summary 분리
  const coverSection = report.sections.find((s) => s.id === "cover");
  const summarySection = report.sections.find((s) => s.id === "executive_summary");

  // 잠금 섹션 (teaser가 있는 것만)
  const lockedSections = report.sections.filter(
    (s) => s.id !== "cover" && s.id !== "executive_summary" && s.unlock_level
  );

  // standard / full 그룹 분리
  const standardSections = lockedSections.filter((s) => s.unlock_level === "standard");
  const fullSections = lockedSections.filter((s) => s.unlock_level === "full");

  const userName = report.user_name || "회원";
  const summaryText =
    (summarySection?.content as { summary?: string })?.summary || "";

  return (
    <div className="max-w-2xl mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
      {/* 1. Cover */}
      {coverSection?.content && (
        <Cover
          content={coverSection.content as unknown as Parameters<typeof Cover>[0]["content"]}
          locked={false}
        />
      )}

      {/* 2. Executive Summary */}
      {summarySection?.content && (
        <ExecutiveSummary
          content={summarySection.content as unknown as Parameters<typeof ExecutiveSummary>[0]["content"]}
          locked={false}
        />
      )}

      {/* 3. 공유 버튼 */}
      <div className="py-8 border-b border-[var(--color-border)]">
        <ShareButtons
          title={`${userName}님의 시각 리포트`}
          description={summaryText.length > 80 ? summaryText.slice(0, 80) + "..." : summaryText}
        />
      </div>

      {/* 4. 분석 항목 미리보기 (Teaser 카드) */}
      <section className="py-10">
        <h2 className="text-xs font-semibold tracking-[4px] uppercase text-[var(--color-muted)] mb-8">
          ANALYSIS OVERVIEW
        </h2>

        {/* Standard 티어 섹션 */}
        {standardSections.length > 0 && (
          <div className="mb-8">
            <div className="flex flex-col gap-4">
              {standardSections.map((section) => {
                const teaser = getTeaserText(section);
                return (
                  <div
                    key={section.id}
                    className="flex items-start gap-4 py-4 border-b border-[var(--color-border)]"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-fg)] mt-2 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold mb-0.5">
                        {SECTION_LABELS[section.id] || section.id}
                      </p>
                      {teaser && (
                        <p className="text-xs text-[var(--color-muted)] truncate">
                          {teaser}
                        </p>
                      )}
                    </div>
                    <svg
                      className="w-4 h-4 text-[var(--color-muted)] mt-1 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <rect x="3" y="7" width="10" height="7" rx="1" />
                      <path d="M5 7V5a3 3 0 016 0v2" />
                    </svg>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Full 티어 섹션 */}
        {fullSections.length > 0 && (
          <div className="mb-8">
            <div className="flex flex-col gap-4">
              {fullSections.map((section) => {
                const teaser = getTeaserText(section);
                return (
                  <div
                    key={section.id}
                    className="flex items-start gap-4 py-4 border-b border-[var(--color-border)]"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-[var(--color-muted)] mt-2 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold mb-0.5 text-[var(--color-muted)]">
                        {SECTION_LABELS[section.id] || section.id}
                      </p>
                      {teaser && (
                        <p className="text-xs text-[var(--color-muted)] opacity-60 truncate">
                          {teaser}
                        </p>
                      )}
                    </div>
                    <svg
                      className="w-4 h-4 text-[var(--color-muted)] opacity-40 mt-1 shrink-0"
                      viewBox="0 0 16 16"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <rect x="3" y="7" width="10" height="7" rx="1" />
                      <path d="M5 7V5a3 3 0 016 0v2" />
                    </svg>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      {/* 5. CTA */}
      <section className="py-10 border-t border-[var(--color-border)]">
        {isPaid ? (
          /* 이미 결제 완료 → 상세 리포트 이동 */
          <div className="flex flex-col items-center gap-4">
            <p className="text-sm text-[var(--color-muted)]">
              결제가 완료되었습니다
            </p>
            <button
              onClick={() => router.push(`/report/${reportId}/full`)}
              className="inline-flex items-center justify-center px-8 py-3.5 text-lg font-medium bg-[var(--color-fg)] text-[var(--color-bg)] hover:opacity-90 transition-colors"
            >
              상세 리포트 보기
            </button>
          </div>
        ) : (
          /* 미결제 → 잠금 해제 CTA */
          <div className="flex flex-col items-center gap-4">
            <p className="text-2xl font-serif font-bold text-center leading-snug">
              나만의 스타일 분석,<br />지금 확인하세요
            </p>
            <p className="text-sm text-[var(--color-muted)] text-center max-w-xs">
              AI가 분석한 얼굴 구조 · 퍼스널 컬러 · 추구미 갭 분석과
              맞춤 헤어 추천까지 확인할 수 있습니다
            </p>
            <button
              onClick={() => router.push(`/report/${reportId}/full`)}
              className="inline-flex items-center justify-center px-8 py-3.5 text-lg font-medium bg-[var(--color-fg)] text-[var(--color-bg)] hover:opacity-90 transition-colors mt-2"
            >
              {report.paywall?.standard
                ? `₩${report.paywall.standard.price.toLocaleString()} 잠금 해제`
                : "상세 리포트 보기"}
            </button>
            <p className="text-[10px] text-[var(--color-muted)]">
              카카오뱅크 송금 · 관리자 확인 후 즉시 열림
            </p>
          </div>
        )}
      </section>

      {/* 하단 여백 */}
      <div className="h-10" />
    </div>
  );
}
