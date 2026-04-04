// 리포트 페이지 (서버 컴포넌트)
// - mock 데이터 사용 (실제 API 연동은 후행)
// - ReportViewer에 initialReport 전달

import { MOCK_REPORT } from "@/lib/constants/mock-report";
import { ReportViewer } from "@/components/report/report-viewer";

interface ReportPageProps {
  params: Promise<{ id: string }>;
}

// 동적 리포트 페이지 - ID 기반으로 리포트 데이터를 로드하여 뷰어에 전달
export default async function ReportPage({ params }: ReportPageProps) {
  // 파라미터에서 리포트 ID 추출 (현재는 mock 데이터 사용)
  const { id } = await params;

  // 실제로는 fetch(`/api/v1/report/${id}`) 호출
  // mock: MOCK_REPORT를 id 덮어쓰기로 사용
  const report = {
    ...MOCK_REPORT,
    id,
  };

  return (
    <main className="min-h-screen bg-[var(--color-bg)]">
      {/* 리포트 네비게이션 */}
      <nav className="sticky top-0 z-[100] flex items-center px-10 h-14 bg-[var(--color-fg)] text-[var(--color-bg)]">
        <span className="text-xs font-bold tracking-[5px]">SIGAK</span>
        <span className="ml-3 text-[10px] font-medium tracking-[2.5px] opacity-40">
          REPORT
        </span>
      </nav>

      {/* 리포트 뷰어 */}
      <div className="pt-4 pb-20">
        <ReportViewer initialReport={report} />
      </div>
    </main>
  );
}
