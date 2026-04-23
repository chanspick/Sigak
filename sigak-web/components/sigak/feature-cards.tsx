/**
 * FeatureCards — 홈 피드 상단 4 기능 진입 카드 (2026-04-23 런칭 스코프).
 *
 * 스코프: Sia 대화 / Best Shot / 추구미 분석 / Verdict 4종.
 * 제외: 이달의 시각 (Monthly), PI 전용 리포트 — 다음 순차 추가 시 활성.
 *
 * 카피: 페르소나 B 친밀체 (~해요 / ~쪽이신가봐요?).
 *       토큰 소모량은 백엔드 COST_* 확정 후 subtitle 에 주입 (현재 placeholder).
 */

"use client";

import Link from "next/link";

interface FeatureCardProps {
  href: string;
  label: string;
  subtitle: string;
}

const FEATURES: FeatureCardProps[] = [
  {
    href: "/sia",
    label: "Sia 대화",
    subtitle: "대화로 당신을 같이 정리해요",
  },
  {
    href: "/verdict/new",
    label: "시각의 판정",
    subtitle: "지금 장면 한 장을 골라드려요",
  },
  {
    href: "/best-shot",
    label: "Best Shot",
    subtitle: "사진 여러 장에서 한 장",
  },
  {
    href: "/aspiration",
    label: "추구미 분석",
    subtitle: "따라가는 이미지, 실제로 뭐가 다른지",
  },
];

export function FeatureCards() {
  return (
    <section
      aria-label="기능 진입"
      style={{
        padding: "28px 28px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div
        className="font-sans uppercase"
        style={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "1.5px",
          opacity: 0.4,
          marginBottom: 4,
          color: "var(--color-ink)",
        }}
      >
        기능
      </div>
      {FEATURES.map((f) => (
        <FeatureCard key={f.href} {...f} />
      ))}
    </section>
  );
}

function FeatureCard({ href, label, subtitle }: FeatureCardProps) {
  return (
    <Link
      href={href}
      className="font-sans"
      style={{
        display: "block",
        padding: "18px 20px",
        background: "var(--color-paper)",
        border: "1px solid var(--color-line-strong)",
        color: "var(--color-ink)",
        textDecoration: "none",
        transition: "opacity 180ms ease-out",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.opacity = "0.7";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.opacity = "1";
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
            }}
          >
            {label}
          </div>
          <div
            style={{
              marginTop: 4,
              fontSize: 12,
              lineHeight: 1.5,
              letterSpacing: "-0.005em",
              opacity: 0.55,
              color: "var(--color-ink)",
            }}
          >
            {subtitle}
          </div>
        </div>
        <span
          aria-hidden
          style={{
            fontSize: 18,
            opacity: 0.4,
            color: "var(--color-ink)",
          }}
        >
          →
        </span>
      </div>
    </Link>
  );
}
