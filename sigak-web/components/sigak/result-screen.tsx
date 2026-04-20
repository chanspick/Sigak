// SIGAK MVP v1.2 (Rebrand) — ResultScreen
//
// 브랜딩 리팩토링:
//   - Medal/SageFrame 전면 제거. "GOLD/SILVER/BRONZE" 라벨 문구 삭제
//   - 날짜 라벨 "2026 · 04 · 19" (sans 11px/2px letterSpacing/opacity 0.4)
//   - 헤드라인 "이 한 장." serif 40px weight 400
//   - GOLD 이미지 4/5 프레임 없이 직접 렌더
//   - Reading: Noto Serif 18px lineHeight 1.7
//   - SILVER/BRONZE: 메달 라벨 제거, "나머지 N장" 단일 행으로 통합
//
// 기능은 그대로 유지:
//   - 3-tier 구조(gold[0] + silver + bronze) 응답 그대로 사용
//   - blur_released 분기 (false면 remaining 이미지 블러, true면 전체 공개 + pro_data)
//   - PRO CTA: 잔액 ≥50 → 인라인 releaseBlur / <50 → /tokens/purchase intent
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { TopBar } from "@/components/ui/sigak";
import { releaseBlur, resolvePhotoUrl } from "@/lib/api/verdicts";
import { ApiError } from "@/lib/api/fetch";
import type { TierPhoto, VerdictResponse } from "@/lib/types/mvp";
import { useTokenBalance } from "@/hooks/use-token-balance";

const BLUR_RELEASE_COST = 50;

interface ResultScreenProps {
  verdict: VerdictResponse;
  /** create 시점의 gold_reading을 sessionStorage에서 주입. */
  goldReadingOverride?: string;
}

export function ResultScreen({
  verdict: initialVerdict,
  goldReadingOverride,
}: ResultScreenProps) {
  const router = useRouter();
  const { balance, refetch: refetchBalance } = useTokenBalance();

  const [verdict, setVerdict] = useState<VerdictResponse>(initialVerdict);
  const [lightbox, setLightbox] = useState(false);
  const [pulseKey, setPulseKey] = useState(0);
  const [releasing, setReleasing] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);
  const proRef = useRef<HTMLDivElement>(null);

  const gold = verdict.tiers.gold[0] ?? null;
  const silver = verdict.tiers.silver;
  const bronze = verdict.tiers.bronze;
  const remaining: TierPhoto[] = [...silver, ...bronze];
  const reading = verdict.gold_reading || goldReadingOverride || "";
  const released = verdict.blur_released;
  const tokens = balance ?? 0;

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
    if (balance != null && balance < BLUR_RELEASE_COST) {
      router.push(
        `/tokens/purchase?intent=blur_release&verdict_id=${encodeURIComponent(verdict.verdict_id)}`,
      );
      return;
    }
    setReleasing(true);
    setReleaseError(null);
    try {
      const res = await releaseBlur(verdict.verdict_id);
      setVerdict((prev) => ({
        ...prev,
        blur_released: true,
        pro_data: res.pro_data,
      }));
      try {
        const { getVerdict } = await import("@/lib/api/verdicts");
        const full = await getVerdict(verdict.verdict_id);
        setVerdict(full);
      } catch {
        // ignore
      }
      await refetchBalance();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
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
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
        overflowY: "auto",
      }}
    >
      <TopBar backTarget="/" />

      {/* 날짜 + 헤드라인 */}
      <section style={{ padding: "40px 28px 32px" }}>
        <DateLabel />
        <h1
          className="font-serif"
          style={{
            fontSize: 40,
            fontWeight: 400,
            lineHeight: 1.2,
            letterSpacing: "-0.02em",
            margin: 0,
            marginTop: 16,
            color: "var(--color-ink)",
          }}
        >
          이 한 장.
        </h1>
      </section>

      {/* 선택된 사진 — 풀 너비, 프레임 없음 */}
      {gold && (
        <div
          style={{ padding: "0 28px", cursor: "pointer" }}
          onClick={() => setLightbox(true)}
        >
          <PhotoTile url={resolvePhotoUrl(gold.url)} aspectRatio="4/5" />
        </div>
      )}

      {/* Reading */}
      {reading && (
        <section style={{ padding: "28px 28px 36px" }}>
          <p
            className="font-serif"
            style={{
              fontSize: 18,
              fontWeight: 400,
              lineHeight: 1.7,
              letterSpacing: "-0.01em",
              margin: 0,
              color: "var(--color-ink)",
              whiteSpace: "pre-wrap",
            }}
          >
            {reading}
          </p>
        </section>
      )}

      <Rule />

      {/* 나머지 후보 */}
      {remaining.length > 0 && (
        <section style={{ padding: "28px 28px 32px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
            }}
          >
            <Label>나머지</Label>
            <LabelRight>{remaining.length}장</LabelRight>
          </div>
          <div
            style={{
              marginTop: 16,
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 4,
            }}
          >
            {remaining.map((photo, i) => {
              if (released && photo.url) {
                return (
                  <div key={photo.photo_id} style={{ opacity: 0.5 }}>
                    <PhotoTile url={resolvePhotoUrl(photo.url)} aspectRatio="1/1" />
                  </div>
                );
              }
              return (
                <BlurredTile key={photo.photo_id || i} onTap={scrollToProAndPulse} />
              );
            })}
          </div>
        </section>
      )}

      <Rule />

      {/* PRO 블록 (blur_released=false 에서만) */}
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

      {/* Footer — 공유만 */}
      <section
        style={{
          padding: "32px 28px 40px",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <FooterLink>공유</FooterLink>
      </section>

      {lightbox && gold && (
        <Lightbox url={resolvePhotoUrl(gold.url)} onClose={() => setLightbox(false)} />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Primitives
// ─────────────────────────────────────────────

function DateLabel() {
  const [label, setLabel] = useState("");
  useEffect(() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    setLabel(`${y} · ${m} · ${day}`);
  }, []);
  return (
    <p
      className="font-sans uppercase"
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "2px",
        opacity: 0.4,
        margin: 0,
        color: "var(--color-ink)",
      }}
    >
      {label}
    </p>
  );
}

function PhotoTile({
  url,
  aspectRatio,
}: {
  url: string;
  aspectRatio: string;
}) {
  return (
    <div
      style={{
        width: "100%",
        aspectRatio,
        overflow: "hidden",
        background: "rgba(0, 0, 0, 0.04)",
      }}
    >
      {url && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={url}
          alt=""
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

function BlurredTile({ onTap }: { onTap: () => void }) {
  const [hot, setHot] = useState(false);
  return (
    <button
      type="button"
      onClick={onTap}
      onPointerEnter={() => setHot(true)}
      onPointerLeave={() => setHot(false)}
      aria-label="가려진 사진 — PRO 해제"
      style={{
        cursor: "pointer",
        overflow: "hidden",
        aspectRatio: "1/1",
        border: "none",
        padding: 0,
        background: "rgba(0, 0, 0, 0.06)",
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
          background:
            "repeating-linear-gradient(32deg, rgba(0,0,0,0.08) 0 14px, rgba(0,0,0,0.02) 14px 15px)",
        }}
      />
    </button>
  );
}

function Rule() {
  return (
    <div
      style={{
        height: 1,
        background: "var(--color-ink)",
        margin: "0 28px",
        opacity: 0.15,
      }}
    />
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-sans uppercase"
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "1.5px",
        opacity: 0.4,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}

function LabelRight({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-serif tabular-nums"
      style={{
        fontSize: 14,
        fontWeight: 400,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}

function FooterLink({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-sans"
      style={{
        fontSize: 13,
        opacity: 0.5,
        letterSpacing: "-0.005em",
        cursor: "pointer",
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}

// ─────────────────────────────────────────────
//  PRO unlock block — 50 토큰
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
        { opacity: 0.65 },
        { opacity: 1 },
      ],
      { duration: 900, easing: "ease-out" },
    );
  }, [pulseKey]);

  const insufficient = balance != null && balance < BLUR_RELEASE_COST;

  return (
    <div ref={refEl} style={{ padding: "28px 28px 0" }}>
      <div
        ref={innerRef}
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onClick();
        }}
        style={{
          border: "1px solid rgba(0, 0, 0, 0.15)",
          padding: "24px 22px",
          cursor: "pointer",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "2px",
            opacity: 0.4,
            color: "var(--color-ink)",
          }}
        >
          PRO
        </div>

        <div
          className="font-serif"
          style={{
            marginTop: 14,
            fontSize: 22,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
          }}
        >
          가려진 것들
        </div>

        <div
          className="font-sans"
          style={{
            marginTop: 8,
            fontSize: 13,
            opacity: 0.55,
            lineHeight: 1.55,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          나머지 사진과 전체 진단까지.
        </div>

        <div
          style={{
            marginTop: 20,
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
          }}
        >
          <span
            className="font-sans uppercase"
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "1.5px",
              opacity: 0.4,
              color: "var(--color-ink)",
            }}
          >
            해제
          </span>
          <span
            className="font-serif tabular-nums"
            style={{
              fontSize: 18,
              fontWeight: 400,
              color: "var(--color-ink)",
            }}
          >
            {BLUR_RELEASE_COST} 토큰
          </span>
        </div>

        {insufficient && !busy && (
          <div
            className="font-sans"
            style={{
              marginTop: 10,
              fontSize: 11,
              opacity: 0.5,
              letterSpacing: "-0.005em",
              textAlign: "right",
              color: "var(--color-ink)",
            }}
          >
            현재 잔액 {balance}토큰 — 충전 페이지로 안내
          </div>
        )}
        {busy && (
          <div
            className="font-sans"
            style={{
              marginTop: 10,
              fontSize: 11,
              opacity: 0.5,
              letterSpacing: "-0.005em",
              textAlign: "right",
              color: "var(--color-ink)",
            }}
          >
            해제 중...
          </div>
        )}
        {error && (
          <div
            className="font-sans"
            style={{
              marginTop: 10,
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
  );
}

// ─────────────────────────────────────────────
//  PRO revealed block
// ─────────────────────────────────────────────

function ProRevealedBlock({ verdict }: { verdict: VerdictResponse }) {
  const data = verdict.pro_data;
  if (!data) return null;
  const all = [...data.silver_readings, ...data.bronze_readings];
  return (
    <div style={{ padding: "28px 28px 0" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 18,
        }}
      >
        <Label>해석</Label>
        <LabelRight>{all.length}장</LabelRight>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {all.map((r, i) => (
          <div
            key={r.photo_id}
            style={{
              borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
              paddingBottom: 20,
            }}
          >
            <div
              className="font-sans uppercase tabular-nums"
              style={{
                fontSize: 10,
                letterSpacing: "1.5px",
                opacity: 0.4,
                marginBottom: 8,
                color: "var(--color-ink)",
              }}
            >
              #{String(i + 2).padStart(2, "0")} · Δ shape {formatDelta(r.axis_delta.shape)},
              volume {formatDelta(r.axis_delta.volume)}, age {formatDelta(r.axis_delta.age)}
            </div>
            <p
              className="font-serif"
              style={{
                fontSize: 15,
                lineHeight: 1.7,
                letterSpacing: "-0.005em",
                color: "var(--color-ink)",
                margin: 0,
              }}
            >
              {r.reason}
            </p>
          </div>
        ))}
      </div>

      {data.full_analysis.interpretation && (
        <div style={{ marginTop: 24 }}>
          <Label>전체 해석</Label>
          <p
            className="font-serif"
            style={{
              marginTop: 12,
              fontSize: 16,
              lineHeight: 1.8,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
              whiteSpace: "pre-wrap",
              margin: 0,
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
//  Lightbox
// ─────────────────────────────────────────────

function Lightbox({ url, onClose }: { url: string; onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      className="animate-fade-in"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.92)",
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
          background: "transparent",
          border: "1px solid rgba(255, 255, 255, 0.4)",
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
            stroke="#F3F0EB"
            strokeWidth="1"
            strokeLinecap="round"
          />
        </svg>
      </button>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{ width: "100%", maxWidth: 340 }}
      >
        <PhotoTile url={url} aspectRatio="4/5" />
      </div>
    </div>
  );
}
