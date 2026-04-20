// SIGAK MVP v1.2 — ResultScreen (3-tier)
//
// refactor/result-screen.jsx v1.2 포팅 + 브리프 3개 수정 반영:
//   1. GOLD 셀 풀 너비 hero (4/5 aspect, SageFrame tick=16)
//   2. PRO 블록 토큰 7 → 50
//   3. Reading 무료 유지 (blur_released=false 에서도 공개)
//
// blur_released=false: GOLD 이미지 + reading + SILVER/BRONZE 블러 + PRO CTA
// blur_released=true:  SILVER/BRONZE URL 복구 + pro_data 렌더
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  MedalLabel,
  SageFrame,
  TopBar,
} from "@/components/ui/sigak";
import { releaseBlur, resolvePhotoUrl } from "@/lib/api/verdicts";
import { ApiError } from "@/lib/api/fetch";
import type { TierPhoto, VerdictResponse } from "@/lib/types/mvp";
import { useTokenBalance } from "@/hooks/use-token-balance";

const BLUR_RELEASE_COST = 50;

interface ResultScreenProps {
  verdict: VerdictResponse;
  /** create 시점의 gold_reading을 sessionStorage에서 주입 (GET 재조회 시엔 빈 문자열). */
  goldReadingOverride?: string;
}

export function ResultScreen({ verdict: initialVerdict, goldReadingOverride }: ResultScreenProps) {
  const router = useRouter();
  const { balance, refetch: refetchBalance } = useTokenBalance();

  // verdict을 로컬 state로 관리 — releaseBlur 성공 시 inline 갱신.
  const [verdict, setVerdict] = useState<VerdictResponse>(initialVerdict);
  const [lightbox, setLightbox] = useState(false);
  const [pulseKey, setPulseKey] = useState(0);
  const [releasing, setReleasing] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);
  const proRef = useRef<HTMLDivElement>(null);

  const gold = verdict.tiers.gold[0] ?? null;
  const silver = verdict.tiers.silver;
  const bronze = verdict.tiers.bronze;
  const reading = verdict.gold_reading || goldReadingOverride || "";
  const released = verdict.blur_released;
  const tokens = balance ?? 0;

  // keyboard esc for lightbox
  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox]);

  function scrollToProAndPulse() {
    if (!proRef.current) return;
    proRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    setPulseKey((k) => k + 1);
  }

  async function handleProCta() {
    if (releasing) return;
    // 잔액 < 50: purchase 페이지로 intent 전달
    if (balance != null && balance < BLUR_RELEASE_COST) {
      router.push(
        `/tokens/purchase?intent=blur_release&verdict_id=${encodeURIComponent(verdict.verdict_id)}`,
      );
      return;
    }
    // 잔액 로딩 중 또는 충분: 직접 release-blur 시도. 실패(402) 시 purchase로 fallback.
    setReleasing(true);
    setReleaseError(null);
    try {
      const res = await releaseBlur(verdict.verdict_id);
      setVerdict((prev) => ({
        ...prev,
        blur_released: true,
        pro_data: res.pro_data,
        // silver/bronze URL을 재조회 응답에서 채워야 완전한 반영 가능 — 간단히 getVerdict 재호출
      }));
      // 재조회로 url 포함된 tiers 복구
      try {
        const { getVerdict } = await import("@/lib/api/verdicts");
        const full = await getVerdict(verdict.verdict_id);
        setVerdict(full);
      } catch {
        // 무시 — 최소 pro_data는 반영됨
      }
      await refetchBalance();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        // 잔액 부족 — purchase로 redirect
        router.push(
          `/tokens/purchase?intent=blur_release&verdict_id=${encodeURIComponent(verdict.verdict_id)}`,
        );
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setReleaseError(
        e instanceof Error ? e.message : "해제에 실패했습니다. 다시 시도해주세요.",
      );
    } finally {
      setReleasing(false);
    }
  }

  return (
    <div className="relative min-h-screen bg-paper text-ink">
      <TopBar variant="result" tokens={tokens} />

      {/* Date line */}
      <DateLine />

      {/* Headline */}
      <div className="px-5 pt-3">
        <h1
          className="m-0 font-sans"
          style={{
            fontSize: 34,
            fontWeight: 500,
            lineHeight: 1.25,
            letterSpacing: "-0.02em",
            color: "var(--color-ink)",
          }}
        >
          이 중에서는,
          <br />이 한{" "}
          <span
            className="font-serif"
            style={{ fontStyle: "italic", fontWeight: 400 }}
          >
            장
          </span>
          .
        </h1>
      </div>

      {/* GOLD — full-width hero (4/5 aspect) */}
      {gold && (
        <GoldHero
          photo={gold}
          onTap={() => setLightbox(true)}
          reading={reading}
        />
      )}

      {/* SILVER / BRONZE rows */}
      <TierRow
        tier="silver"
        photos={silver}
        marginTop={36}
        released={released}
        onLockedTap={scrollToProAndPulse}
      />
      <TierRow
        tier="bronze"
        photos={bronze}
        marginTop={24}
        released={released}
        onLockedTap={scrollToProAndPulse}
      />

      {/* PRO unlock block (or full_analysis if released) */}
      {!released ? (
        <ProUnlockBlock
          refEl={proRef}
          pulseKey={pulseKey}
          onClick={handleProCta}
          balance={balance}
          busy={releasing}
          error={releaseError}
        />
      ) : (
        <ProRevealedBlock verdict={verdict} />
      )}

      {/* Footer actions */}
      <FooterActions onNewVerdict={() => router.push("/")} />

      {lightbox && gold && (
        <GoldLightbox
          url={resolvePhotoUrl(gold.url)}
          onClose={() => setLightbox(false)}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  DateLine
// ─────────────────────────────────────────────

function DateLine() {
  const [label, setLabel] = useState("");
  useEffect(() => {
    const d = new Date();
    setLabel(`${d.getMonth() + 1}월 ${d.getDate()}일`);
  }, []);
  return (
    <div
      className="px-5 pt-[26px] font-sans text-mute"
      style={{ fontSize: 12, letterSpacing: "-0.005em" }}
    >
      {label}
    </div>
  );
}

// ─────────────────────────────────────────────
//  GOLD hero — 브리프 수정 1: 풀 너비 4/5
// ─────────────────────────────────────────────

function GoldHero({
  photo,
  reading,
  onTap,
}: {
  photo: TierPhoto;
  reading: string;
  onTap: () => void;
}) {
  const [pressed, setPressed] = useState(false);
  const src = resolvePhotoUrl(photo.url);
  return (
    <div className="pt-11">
      <div className="px-5">
        <MedalLabel tier="gold" count={1} />
      </div>
      <div
        className="mt-3 px-5"
        onClick={onTap}
        onPointerDown={() => setPressed(true)}
        onPointerUp={() => setPressed(false)}
        onPointerLeave={() => setPressed(false)}
        style={{
          cursor: "pointer",
          transform: pressed ? "scale(0.99)" : "scale(1)",
          transition: "transform 150ms ease-out",
          transformOrigin: "center",
        }}
      >
        <SageFrame inset={10} tick={16} weight={1}>
          <div
            style={{
              width: "100%",
              aspectRatio: "4/5",
              overflow: "hidden",
              background: "var(--color-sage-soft)",
            }}
          >
            {src && (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img
                src={src}
                alt="GOLD"
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  display: "block",
                }}
              />
            )}
          </div>
        </SageFrame>
      </div>

      {reading && (
        <div className="px-5 pt-5">
          <p
            className="max-w-[320px] font-sans"
            style={{
              fontSize: 14,
              fontWeight: 400,
              lineHeight: 1.7,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
              whiteSpace: "pre-wrap",
            }}
          >
            {reading}
          </p>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  TierRow — SILVER / BRONZE
// ─────────────────────────────────────────────

function TierRow({
  tier,
  photos,
  marginTop,
  released,
  onLockedTap,
}: {
  tier: "silver" | "bronze";
  photos: TierPhoto[];
  marginTop: number;
  released: boolean;
  onLockedTap: () => void;
}) {
  const slots = tier === "silver" ? 3 : 5;
  return (
    <div style={{ paddingTop: marginTop }} className="px-5">
      <MedalLabel tier={tier} count={photos.length} />
      <div
        className="mt-3"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: 8,
        }}
      >
        {Array.from({ length: 5 }, (_, i) => {
          if (i >= slots || i >= photos.length) return <div key={i} />;
          const photo = photos[i];
          if (released) {
            const src = resolvePhotoUrl(photo.url);
            return (
              <div
                key={photo.photo_id}
                style={{
                  aspectRatio: "1/1",
                  overflow: "hidden",
                  background: "var(--color-sage-soft)",
                  borderRadius: 2,
                }}
              >
                {src && (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={src}
                    alt={tier}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      display: "block",
                    }}
                  />
                )}
              </div>
            );
          }
          return (
            <BlurredCell
              key={photo.photo_id}
              tier={tier}
              onTap={onLockedTap}
            />
          );
        })}
      </div>
    </div>
  );
}

function BlurredCell({
  tier,
  onTap,
}: {
  tier: "silver" | "bronze";
  onTap: () => void;
}) {
  const [hot, setHot] = useState(false);
  // tier별 살짝 다른 tonal fill — visual variation
  const fill =
    tier === "silver"
      ? "var(--color-silver-fill)"
      : "var(--color-bronze-fill)";
  return (
    <button
      type="button"
      onClick={onTap}
      onPointerEnter={() => setHot(true)}
      onPointerLeave={() => setHot(false)}
      aria-label="블러 해제하려면 탭"
      style={{
        cursor: "pointer",
        overflow: "hidden",
        borderRadius: 2,
        aspectRatio: "1/1",
        border: "none",
        padding: 0,
        background: fill,
      }}
    >
      <div
        style={{
          width: "100%",
          height: "100%",
          filter: hot ? "blur(6px)" : "blur(10px)",
          transform: "scale(1.15)",
          transformOrigin: "center",
          transition: "filter 200ms ease-out",
          background: `repeating-linear-gradient(32deg, ${fill} 0 14px, rgba(15,15,14,0.07) 14px 15px)`,
        }}
      />
    </button>
  );
}

// ─────────────────────────────────────────────
//  PRO Unlock block — 브리프 수정 2: 7 → 50
// ─────────────────────────────────────────────

function ProUnlockBlock({
  refEl,
  pulseKey,
  onClick,
  balance,
  busy,
  error,
}: {
  refEl: React.RefObject<HTMLDivElement | null>;
  pulseKey: number;
  onClick: () => void;
  balance: number | null;
  busy: boolean;
  error: string | null;
}) {
  const innerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!pulseKey || !innerRef.current) return;
    innerRef.current.animate(
      [
        { opacity: 1 },
        { opacity: 0.78 },
        { opacity: 1 },
        { opacity: 0.85 },
        { opacity: 1 },
      ],
      { duration: 900, easing: "ease-out" },
    );
  }, [pulseKey]);

  const insufficient = balance != null && balance < BLUR_RELEASE_COST;

  return (
    <div ref={refEl} className="pt-[52px]">
      <div className="px-5">
        <div
          ref={innerRef}
          onClick={onClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onClick();
          }}
          style={{
            background: "var(--color-sage-soft)",
            borderRadius: 10,
            padding: "20px 22px",
            cursor: "pointer",
          }}
        >
          <div
            className="font-display font-medium uppercase"
            style={{
              fontSize: 10,
              letterSpacing: "0.14em",
              color: "var(--color-sage)",
            }}
          >
            PRO
          </div>

          <div
            className="mt-3 font-sans"
            style={{
              fontSize: 19,
              fontWeight: 500,
              lineHeight: 1.35,
              letterSpacing: "-0.015em",
              color: "var(--color-ink)",
            }}
          >
            가려진 것들
          </div>

          <div
            className="mt-1.5 font-sans"
            style={{
              fontSize: 13,
              fontWeight: 400,
              lineHeight: 1.55,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
            }}
          >
            silver, bronze 사진과 전체 진단까지.
          </div>

          <div className="mt-[14px] flex items-center justify-end gap-3">
            <span
              className="font-display"
              style={{
                fontSize: 16,
                color: "var(--color-ink)",
                lineHeight: 1,
              }}
            >
              →
            </span>
            <span
              className="flex items-center gap-[5px] font-display tabular-nums"
              style={{
                fontSize: 11,
                fontWeight: 400,
                color: "var(--color-ink)",
                letterSpacing: "0.02em",
              }}
            >
              <span
                className="relative inline-block"
                style={{ width: 9, height: 9 }}
              >
                <span
                  className="absolute inset-0 rounded-full"
                  style={{ border: "1px solid var(--color-ink)" }}
                />
                <span
                  className="absolute rounded-full"
                  style={{
                    left: 2.25,
                    top: 2.25,
                    width: 4.5,
                    height: 4.5,
                    background: "var(--color-sage)",
                  }}
                />
              </span>
              {BLUR_RELEASE_COST}
            </span>
          </div>

          {insufficient && !busy && (
            <div
              className="mt-2 font-sans text-mute"
              style={{ fontSize: 11, letterSpacing: "-0.005em", textAlign: "right" }}
            >
              현재 잔액 {balance}토큰 — 충전 페이지로 안내됩니다
            </div>
          )}
          {busy && (
            <div
              className="mt-2 font-sans text-mute"
              style={{ fontSize: 11, letterSpacing: "-0.005em", textAlign: "right" }}
            >
              해제 중...
            </div>
          )}
          {error && (
            <div
              className="mt-2 font-sans"
              style={{
                fontSize: 11,
                letterSpacing: "-0.005em",
                textAlign: "right",
                color: "var(--color-danger)",
              }}
              role="alert"
            >
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  PRO Revealed block (pro_data 렌더)
// ─────────────────────────────────────────────

function ProRevealedBlock({ verdict }: { verdict: VerdictResponse }) {
  const data = verdict.pro_data;
  if (!data) return null;
  const all = [...data.silver_readings, ...data.bronze_readings];
  return (
    <div className="pt-[52px]">
      <div className="mb-3 flex items-baseline gap-2.5 px-5">
        <span
          className="font-mono text-mute"
          style={{ fontSize: 10, letterSpacing: "0.14em" }}
        >
          § 02
        </span>
        <span
          className="font-display font-medium uppercase text-ink"
          style={{ fontSize: 10, letterSpacing: "0.22em" }}
        >
          — READINGS
        </span>
      </div>

      <div className="space-y-4 px-5">
        {all.map((r, i) => (
          <div
            key={r.photo_id}
            className="border-b pb-4"
            style={{ borderColor: "var(--color-line)" }}
          >
            <div
              className="mb-1 font-mono tabular-nums text-mute"
              style={{ fontSize: 10, letterSpacing: "0.14em" }}
            >
              #{String(i + 2).padStart(2, "0")} · Δ shape{" "}
              {formatDelta(r.axis_delta.shape)}, volume{" "}
              {formatDelta(r.axis_delta.volume)}, age {formatDelta(r.axis_delta.age)}
            </div>
            <p
              className="font-sans"
              style={{
                fontSize: 13,
                lineHeight: 1.7,
                color: "var(--color-ink)",
                letterSpacing: "-0.005em",
              }}
            >
              {r.reason}
            </p>
          </div>
        ))}
      </div>

      {/* full_analysis interpretation */}
      {data.full_analysis.interpretation && (
        <div className="mt-8 px-5">
          <div
            className="mb-2 font-display font-medium uppercase text-mute"
            style={{ fontSize: 10, letterSpacing: "0.22em" }}
          >
            § FULL ANALYSIS
          </div>
          <p
            className="font-sans"
            style={{
              fontSize: 14,
              lineHeight: 1.8,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
              whiteSpace: "pre-wrap",
            }}
          >
            {data.full_analysis.interpretation}
          </p>
        </div>
      )}
    </div>
  );
}

function formatDelta(n: number): string {
  const rounded = Math.round(n * 100) / 100;
  const sign = rounded > 0 ? "+" : "";
  return `${sign}${rounded}`;
}

// ─────────────────────────────────────────────
//  Footer actions
// ─────────────────────────────────────────────

function FooterActions({ onNewVerdict }: { onNewVerdict: () => void }) {
  return (
    <div className="flex gap-5 px-5 pb-8 pt-[52px]">
      <button
        type="button"
        onClick={onNewVerdict}
        className="font-sans text-mute"
        style={{
          fontSize: 13,
          fontWeight: 400,
          letterSpacing: "-0.005em",
          cursor: "pointer",
          border: "none",
          background: "transparent",
          padding: 0,
        }}
      >
        다시 판정
      </button>
      {/* 공유/저장은 v1.2에서 비활성 — placeholder만 */}
      <span
        className="font-sans text-mute-2"
        style={{
          fontSize: 13,
          letterSpacing: "-0.005em",
          color: "var(--color-mute-2)",
        }}
      >
        공유
      </span>
      <span
        className="font-sans text-mute-2"
        style={{
          fontSize: 13,
          letterSpacing: "-0.005em",
          color: "var(--color-mute-2)",
        }}
      >
        저장
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────
//  GOLD lightbox
// ─────────────────────────────────────────────

function GoldLightbox({ url, onClose }: { url: string; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      className="animate-fade-in"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15,15,14,0.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px 24px",
        zIndex: 50,
      }}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        aria-label="닫기"
        style={{
          position: "absolute",
          top: 56,
          right: 20,
          width: 32,
          height: 32,
          borderRadius: 999,
          background: "transparent",
          border: "0.5px solid rgba(250,250,247,0.5)",
          cursor: "pointer",
          padding: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg width="11" height="11" viewBox="0 0 11 11">
          <path
            d="M1 1l9 9M10 1L1 10"
            stroke="var(--color-paper)"
            strokeWidth="1"
            strokeLinecap="round"
          />
        </svg>
      </button>

      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: "100%", maxWidth: 320 }}
      >
        <SageFrame inset={10} tick={16} weight={1}>
          <div
            style={{
              width: "100%",
              aspectRatio: "4/5",
              overflow: "hidden",
              background: "var(--color-sage-soft)",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt="GOLD"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
              }}
            />
          </div>
        </SageFrame>
      </div>
    </div>
  );
}
