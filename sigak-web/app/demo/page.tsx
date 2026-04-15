import type { Metadata } from "next";
import { ReportNav } from "@/components/report/report-nav";
import { SectionRenderer } from "@/components/report/section-renderer";
import { DEMO_REPORT } from "./demo-data";

export const metadata: Metadata = {
  title: "SIGAK - 데모 리포트",
  description: "AI 이목구비 분석 데모 리포트",
};

export default function DemoPage() {
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
        </div>
      </div>
    </main>
  );
}
