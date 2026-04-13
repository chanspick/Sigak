// 상세 리포트 페이지 (결제 완료자 전용)
// - 미결제 시 오버뷰 페이지로 리다이렉트
// - 결제 완료 시 전체 섹션 표시 (기존 ReportViewer 재사용)

import { redirect } from "next/navigation";
import Link from "next/link";
import { getReportServerSide } from "@/lib/api/client";
import { ReportViewer } from "@/components/report/report-viewer";
import { ReportNav } from "@/components/report/report-nav";

interface FullReportPageProps {
  params: Promise<{ id: string }>;
}

export default async function FullReportPage({ params }: FullReportPageProps) {
  const { id } = await params;
  const report = await getReportServerSide(id);

  if (!report) {
    return (
      <main className="min-h-screen bg-[var(--color-bg)]">
        <ReportNav />
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
          <h1 className="font-[family-name:var(--font-serif)] text-[24px] font-normal mb-3">
            리포트를 불러올 수 없습니다
          </h1>
          <p className="text-[13px] opacity-50 mb-8 max-w-[360px]">
            분석이 아직 완료되지 않았거나, 유효하지 않은 링크입니다.
          </p>
          <Link
            href={`/report/${id}`}
            className="inline-block px-8 py-3 text-sm font-bold bg-[var(--color-fg)] text-[var(--color-bg)] transition-opacity duration-200 hover:opacity-85"
          >
            오버뷰로 돌아가기
          </Link>
        </div>
      </main>
    );
  }

  // 미결제 → 오버뷰로 리다이렉트
  if (report.access_level === "free") {
    redirect(`/report/${id}`);
  }

  return (
    <main className="min-h-screen bg-[var(--color-bg)]">
      {/* 네비게이션 */}
      <ReportNav rightLink={{ href: `/report/${id}`, label: "OVERVIEW" }} />

      {/* 리포트 뷰어 */}
      <div className="pt-4 pb-20">
        <ReportViewer initialReport={report} />
      </div>
    </main>
  );
}
