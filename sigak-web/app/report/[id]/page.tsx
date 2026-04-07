// 리포트 페이지 (서버 컴포넌트)
// - 백엔드 API에서 리포트 데이터 조회
// - 실패 시 에러 메시지 표시
// - ReportViewer에 initialReport 전달

import { getReportServerSide } from "@/lib/api/client";
import { ReportViewer } from "@/components/report/report-viewer";
import Link from "next/link";

interface ReportPageProps {
  params: Promise<{ id: string }>;
}

// 동적 리포트 페이지 - user_id 기반으로 리포트 데이터를 로드하여 뷰어에 전달
export default async function ReportPage({ params }: ReportPageProps) {
  const { id } = await params;

  // 서버 사이드에서 리포트 데이터 조회
  const report = await getReportServerSide(id);

  return (
    <main className="min-h-screen bg-[var(--color-bg)]">
      {/* 리포트 네비게이션 */}
      <nav className="sticky top-0 z-[100] flex items-center px-10 h-14 bg-[var(--color-fg)] text-[var(--color-bg)]">
        <span className="text-xs font-bold tracking-[5px]">SIGAK</span>
        <span className="ml-3 text-[10px] font-medium tracking-[2.5px] opacity-40">
          REPORT
        </span>
      </nav>

      {/* 리포트 뷰어 또는 에러 */}
      {report ? (
        <div className="pt-4 pb-20">
          <ReportViewer initialReport={report} />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center">
          <h1 className="font-[family-name:var(--font-serif)] text-[24px] font-normal mb-3">
            리포트를 불러올 수 없습니다
          </h1>
          <p className="text-[13px] opacity-50 mb-8 max-w-[360px]">
            분석이 아직 완료되지 않았거나, 유효하지 않은 링크입니다.
            잠시 후 다시 시도해 주세요.
          </p>
          <Link
            href="/start"
            className="inline-block px-8 py-3 text-sm font-bold bg-[var(--color-fg)] text-[var(--color-bg)] transition-opacity duration-200 hover:opacity-85"
          >
            처음으로 돌아가기
          </Link>
        </div>
      )}
    </main>
  );
}
