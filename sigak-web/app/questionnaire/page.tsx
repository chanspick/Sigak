import { redirect } from "next/navigation";
import type { Metadata } from "next";
import { QuestionnaireForm } from "@/components/questionnaire/questionnaire-form";

// SEO 메타데이터
export const metadata: Metadata = {
  title: "설문 진단 | 시각",
};

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

/** /questionnaire 라우트 - 설문 진단 멀티스텝 폼 */
export default async function QuestionnairePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const userId = typeof params.user_id === "string" ? params.user_id : null;
  const tier = typeof params.tier === "string" ? params.tier : null;
  const gender = typeof params.gender === "string" ? params.gender : "female";

  // 필수 파라미터 누락 시 /start로 리다이렉트
  if (!userId || !tier || !["basic", "creator", "wedding"].includes(tier)) {
    redirect("/start");
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      <QuestionnaireForm
        userId={userId as string}
        tier={tier as "basic" | "creator" | "wedding"}
        gender={(gender ?? "female") as "female" | "male"}
      />
    </div>
  );
}
