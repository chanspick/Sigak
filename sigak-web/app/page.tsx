"use client";

// 랜딩 페이지 - 7개 섹션 조립
import { useState, useCallback } from "react";
import { Nav } from "@/components/landing/nav";
import { Hero } from "@/components/landing/hero";
import { TierSection } from "@/components/landing/tier-section";
import { ExpertSection } from "@/components/landing/expert-section";
import { SeatsSection } from "@/components/landing/seats-section";
import { CtaSection } from "@/components/landing/cta-section";
import { Footer } from "@/components/landing/footer";
import { BookingOverlay } from "@/components/landing/booking-overlay";
import { Divider } from "@/components/ui/divider";
import { TIERS } from "@/lib/constants/tiers";
import { bookedByTier } from "@/lib/constants/bookings";
import type { Tier } from "@/lib/types/tier";

export default function LandingPage() {
  const [overlayOpen, setOverlayOpen] = useState(false);
  const [overlayTier, setOverlayTier] = useState<Tier["id"] | null>(null);

  const book = useCallback((tierId?: Tier["id"]) => {
    setOverlayTier(tierId ?? null);
    setOverlayOpen(true);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-fg)]">
      {/* NAV */}
      <Nav onBook={() => book()} />

      {/* HERO */}
      <Hero onBook={() => book()} />

      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* TIERS */}
      {TIERS.map((tier) => (
        <div key={tier.id}>
          <TierSection
            tier={tier}
            bookedCount={bookedByTier(tier.id)}
            onBook={book}
          />
          <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />
        </div>
      ))}

      {/* EXPERTS */}
      <ExpertSection
        name="HAN"
        role="미감 엔지니어"
        description="4년간 수천 개의 얼굴을 읽으며 쌓아온 미감 판단 체계. 얼굴 구조, 피부톤, 트렌드 포지셔닝."
      />
      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />
      <ExpertSection
        name="JIN"
        role="비주얼 디렉터"
        description="카메라 앞 이미지 최적화 4년. 각도, 조명, 포즈 분석을 통한 비주얼 포텐셜 극대화."
      />
      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* SEATS */}
      <SeatsSection />
      <Divider className="mx-[var(--spacing-page-x-mobile)] md:mx-[var(--spacing-page-x)]" />

      {/* CTA */}
      <CtaSection onBook={() => book()} />

      {/* FOOTER */}
      <Footer />

      {/* BOOKING OVERLAY */}
      <BookingOverlay key={overlayTier}
        open={overlayOpen}
        onClose={() => setOverlayOpen(false)}
        initTier={overlayTier}
      />
    </div>
  );
}
