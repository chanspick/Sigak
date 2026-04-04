import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AnalysisLoader } from "@/components/questionnaire/analysis-loader";

// SEO 메타데이터
export const metadata: Metadata = {
  title: "분석 중 | 시각",
};

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** /questionnaire/complete 라우트 - 분석 대기 화면 */
export default async function QuestionnaireCompletePage({
  searchParams,
}: PageProps) {
  const params = await searchParams;
  const userId = typeof params.user_id === "string" ? params.user_id : null;

  if (!userId) {
    redirect("/start");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] text-[var(--color-fg)] px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
      <AnalysisLoader userId={userId} />
    </div>
  );
}
