import type { Metadata } from "next";
import { ReportNav } from "@/components/report/report-nav";
import { SectionRenderer } from "@/components/report/section-renderer";
import { ShareButtons } from "@/components/report/share-buttons";
import { DEMO_REPORT } from "./demo-data";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://sigak.asia";

export const metadata: Metadata = {
  title: "SIGAK - 데모 리포트",
  description: "AI 이목구비 분석 데모 리포트 — 얼굴 구조, 퍼스널컬러, 추구미 갭 분석",
  openGraph: {
    title: "SIGAK 데모 리포트",
    description: "AI 이목구비 분석 데모 리포트 — 얼굴 구조, 퍼스널컬러, 추구미 갭 분석",
    url: `${SITE_URL}/demo`,
    siteName: "SIGAK",
    type: "article",
  },
  twitter: {
    card: "summary",
    title: "SIGAK 데모 리포트",
    description: "AI 이목구비 분석 데모 리포트",
  },
};

export default function DemoPage() {
  const summarySection = DEMO_REPORT.sections.find((s) => s.id === "executive_summary");
  const summaryText =
    (summarySection?.content as { summary?: string })?.summary || "";

  return (
    <main className="min-h-screen bg-[var(--color-bg)]">
      <ReportNav />
      <div className="pt-4 pb-20">
        <div className="max-w-2xl mx-auto px-[var(--spacing-page-x-mobile)] md:px-[var(--spacing-page-x)]">
          {DEMO_REPORT.sections.map((section) => (
            <SectionRenderer
              key={section.id}
              section={section}
              accessLevel={DEMO_REPORT.access_level}
            />
          ))}

          {/* 공유 */}
          <div className="py-10 border-t border-[var(--color-border)]">
            <p className="text-xs text-center text-[var(--color-muted)] mb-4">
              데모 리포트가 마음에 드셨나요? 공유해보세요
            </p>
            <ShareButtons
              title="SIGAK 데모 리포트"
              description={summaryText.length > 80 ? summaryText.slice(0, 80) + "..." : summaryText}
            />
          </div>

          {/* CTA */}
          <section className="py-10 border-t border-[var(--color-border)]">
            <div className="flex flex-col items-center gap-4">
              <p className="text-2xl font-serif font-bold text-center leading-snug">
                나만의 리포트를 받아보세요
              </p>
              <p className="text-sm text-[var(--color-muted)] text-center max-w-xs">
                사진 한 장으로 AI가 분석하는
                이목구비 비율 · 퍼스널컬러 · 맞춤 스타일링
              </p>
              <a
                href="/start"
                className="inline-flex items-center justify-center px-8 py-3.5 text-lg font-medium bg-[var(--color-fg)] text-[var(--color-bg)] hover:opacity-90 transition-colors mt-2"
              >
                분석 시작하기
              </a>
            </div>
          </section>

          <div className="h-10" />
        </div>
      </div>
    </main>
  );
}
