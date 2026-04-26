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
          <div
            style={{
              padding: "40px 0",
              borderTop: "1px solid var(--color-line)",
            }}
          >
            <p
              className="font-sans"
              style={{
                fontSize: 12.5,
                textAlign: "center",
                color: "var(--color-mute)",
                marginBottom: 16,
                letterSpacing: "-0.005em",
              }}
            >
              데모 리포트가 마음에 드셨나요? 공유해보세요
            </p>
            <ShareButtons
              title="SIGAK 데모 리포트"
              description={summaryText.length > 80 ? summaryText.slice(0, 80) + "..." : summaryText}
            />
          </div>

          {/* CTA — 마케터 정합 (Noto Serif 24 700 + period accent + pill) */}
          <section
            style={{
              padding: "40px 0",
              borderTop: "1px solid var(--color-line)",
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 14,
              }}
            >
              <h2
                className="font-serif"
                style={{
                  margin: 0,
                  fontSize: 24,
                  fontWeight: 700,
                  letterSpacing: "-0.022em",
                  textAlign: "center",
                  lineHeight: 1.42,
                  color: "var(--color-ink)",
                  wordBreak: "keep-all",
                }}
              >
                나만의 리포트를 받아보세요
                <span style={{ color: "var(--color-danger)" }}>.</span>
              </h2>
              <p
                className="font-sans"
                style={{
                  margin: 0,
                  fontSize: 13.5,
                  color: "var(--color-mute)",
                  textAlign: "center",
                  maxWidth: 320,
                  lineHeight: 1.65,
                  letterSpacing: "-0.005em",
                }}
              >
                사진 한 장으로 시각이 분석하는
                <br />
                이목구비 비율 · 퍼스널컬러 · 맞춤 스타일링
              </p>
              <a
                href="/sia"
                className="font-sans"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  padding: "15px 36px",
                  background: "var(--color-ink)",
                  color: "var(--color-paper)",
                  border: "none",
                  borderRadius: 100,
                  fontSize: 15,
                  fontWeight: 600,
                  letterSpacing: "-0.012em",
                  textDecoration: "none",
                  marginTop: 8,
                }}
              >
                분석 시작하기 →
              </a>
            </div>
          </section>

          <div className="h-10" />
        </div>
      </div>
    </main>
  );
}
