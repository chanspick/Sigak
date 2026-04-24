/**
 * FeatureCards — 홈 피드 하단 "다음 한 걸음" 가로 스와이프 배너 (2026-04-24 redesign).
 *
 * MARKETER.jsx 기반. 수직 4 카드 리스트 → 수평 스크롤 + ◀▶ 네비 버튼.
 * 스코프: Sia 대화 / 시각의 판정 / Best Shot / 추구미 분석.
 * 제외: 이달의 시각 / PI — 다음 순차 추가 시 활성.
 *
 * 토큰 소모량은 tokens.py 실값 (Sia 0 · Verdict 진단 10 · Best Shot 30 · Aspiration 20).
 */

"use client";

import Link from "next/link";
import { useRef } from "react";

interface Feature {
  key: string;
  ko: string;
  sub: string;
  cost: number;     // 0 = "무료"
  href: string;
}

const FEATURES: readonly Feature[] = [
  { key: "sia",        ko: "Sia 대화",     sub: "대화로 당신을 같이 정리해요",          cost: 0,  href: "/sia" },
  { key: "verdict",    ko: "시각의 판정",  sub: "지금 장면 한 장을 골라드려요",          cost: 10, href: "/verdict/new" },
  { key: "bestshot",   ko: "Best Shot",    sub: "사진 여러 장에서 한 장",                cost: 30, href: "/best-shot" },
  { key: "aspiration", ko: "추구미 분석",  sub: "따라가는 이미지, 실제로 뭐가 다른지",   cost: 20, href: "/aspiration" },
];

export function FeatureCards() {
  const bannerRef = useRef<HTMLDivElement | null>(null);

  function scrollBanner(dir: "left" | "right") {
    const el = bannerRef.current;
    if (!el) return;
    const cardWidth = el.offsetWidth * 0.78 + 12;
    el.scrollBy({
      left: dir === "right" ? cardWidth : -cardWidth,
      behavior: "smooth",
    });
  }

  return (
    <section
      aria-label="다음 한 걸음"
      style={{ paddingTop: 28, paddingBottom: 12 }}
    >
      {/* 스크롤바 숨김 유틸리티 */}
      <style>{`
        .feature-cards-scroller::-webkit-scrollbar { display: none; }
        .feature-cards-scroller {
          -ms-overflow-style: none;
          scrollbar-width: none;
          -webkit-overflow-scrolling: touch;
        }
      `}</style>

      {/* 헤더: 제목 + 네비 버튼 */}
      <div
        style={{
          padding: "0 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 14,
        }}
      >
        <div
          className="font-sans"
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          다음 한 걸음
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <NavButton direction="left" onClick={() => scrollBanner("left")} />
          <NavButton direction="right" onClick={() => scrollBanner("right")} />
        </div>
      </div>

      {/* 스와이프 카드 컨테이너 */}
      <div
        ref={bannerRef}
        className="feature-cards-scroller"
        style={{
          display: "flex",
          gap: 12,
          overflowX: "auto",
          scrollSnapType: "x mandatory",
          paddingLeft: 28,
          scrollPaddingLeft: 28,
        }}
      >
        {FEATURES.map((f) => (
          <FeatureCard key={f.key} feature={f} />
        ))}
        <div style={{ flexShrink: 0, width: 28 }} />
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Card
// ─────────────────────────────────────────────

function FeatureCard({ feature }: { feature: Feature }) {
  return (
    <Link
      href={feature.href}
      className="font-sans"
      aria-label={`${feature.ko} — ${feature.cost === 0 ? "무료" : feature.cost + " 토큰"}`}
      style={{
        scrollSnapAlign: "start",
        flexShrink: 0,
        width: "78%",
        background: "var(--color-paper)",
        border: "1px solid var(--color-line-strong)",
        borderRadius: 12,
        color: "var(--color-ink)",
        textDecoration: "none",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: 20,
          height: 140,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 16,
              fontWeight: 700,
              lineHeight: 1.2,
              color: "var(--color-ink)",
            }}
          >
            {feature.ko}
          </div>
          <div
            style={{
              marginTop: 6,
              fontSize: 12.5,
              lineHeight: 1.5,
              letterSpacing: "-0.005em",
              opacity: 0.55,
              color: "var(--color-ink)",
            }}
          >
            {feature.sub}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            className="tabular-nums"
            style={{
              fontSize: 12,
              fontWeight: 500,
              opacity: 0.7,
              color: "var(--color-ink)",
            }}
          >
            {feature.cost === 0 ? "무료" : `${feature.cost} 토큰`}
          </span>
          <span
            aria-hidden
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "rgba(0,0,0,0.06)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <ChevronIcon size={12} direction="right" />
          </span>
        </div>
      </div>
    </Link>
  );
}

// ─────────────────────────────────────────────
//  Nav button (◀ / ▶)
// ─────────────────────────────────────────────

function NavButton({
  direction,
  onClick,
}: {
  direction: "left" | "right";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={direction === "left" ? "이전" : "다음"}
      style={{
        width: 28,
        height: 28,
        borderRadius: "50%",
        border: "1px solid rgba(0,0,0,0.2)",
        background: "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        color: "var(--color-ink)",
      }}
    >
      <ChevronIcon size={12} direction={direction} strokeWidth={1.8} />
    </button>
  );
}

function ChevronIcon({
  size,
  direction,
  strokeWidth = 1.8,
}: {
  size: number;
  direction: "left" | "right";
  strokeWidth?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      aria-hidden
    >
      <path
        d={direction === "left" ? "M15 6l-6 6 6 6" : "M9 6l6 6-6 6"}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
