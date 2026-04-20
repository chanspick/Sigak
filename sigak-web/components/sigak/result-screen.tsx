// SIGAK MVP v1.2 (D-6 Batch 3) — ResultScreen
//
// 나머지 N장 섹션을 페이지에서 제거하고 모달로 분리.
// GOLD 이미지 아래에 "진단 보기" 버튼 — 클릭 시 DiagnosisModal open.
//   - diagnosis_unlocked=false: 모달 안에서 silver/bronze 블러 + PRO CTA (10 토큰)
//   - diagnosis_unlocked=true:  모달 안에서 이미지 복구 + readings + full_analysis
//
// Footer는 "공유"만 (Batch 1에서 반영).
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";
import { resolvePhotoUrl, unlockDiagnosis } from "@/lib/api/verdicts";
import { ApiError } from "@/lib/api/fetch";
import type { TierPhoto, VerdictResponse } from "@/lib/types/mvp";
import { useTokenBalance } from "@/hooks/use-token-balance";

// v2 BM: 10 토큰. (기존 50토큰 BLUR_RELEASE는 deprecated)
const DIAGNOSIS_COST = 10;

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
  const [showDiagnosis, setShowDiagnosis] = useState(false);
  const [releasing, setReleasing] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);

  const gold = verdict.tiers.gold[0] ?? null;
  const remaining: TierPhoto[] = [...verdict.tiers.silver, ...verdict.tiers.bronze];
  const reading = verdict.gold_reading || goldReadingOverride || "";
  // v2 BM: diagnosis_unlocked가 primary. blur_released는 legacy 데이터 폴백.
  const released = Boolean(
    verdict.diagnosis_unlocked ?? verdict.blur_released,
  );

  // lightbox ESC
  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox]);

  // 모달 ESC
  useEffect(() => {
    if (!showDiagnosis) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setShowDiagnosis(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showDiagnosis]);

  // body scroll lock — lightbox 또는 모달
  useEffect(() => {
    if (!showDiagnosis && !lightbox) return;
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = original;
    };
  }, [showDiagnosis, lightbox]);

  async function handleProCta() {
    if (releasing) return;
    if (balance != null && balance < DIAGNOSIS_COST) {
      router.push(
        `/tokens/purchase?intent=unlock_diagnosis&verdict_id=${encodeURIComponent(verdict.verdict_id)}`,
      );
      return;
    }
    setReleasing(true);
    setReleaseError(null);
    try {
      await unlockDiagnosis(verdict.verdict_id);
      // 재조회로 전체 응답 갱신 (pro_data, tiers url 등)
      try {
        const { getVerdict } = await import("@/lib/api/verdicts");
        const full = await getVerdict(verdict.verdict_id);
        setVerdict(full);
      } catch {
        // 재조회 실패해도 diagnosis_unlocked 최소 반영
        setVerdict((prev) => ({ ...prev, diagnosis_unlocked: true }));
      }
      await refetchBalance();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push(
          `/tokens/purchase?intent=unlock_diagnosis&verdict_id=${encodeURIComponent(verdict.verdict_id)}`,
        );
        return;
      }
      if (e instanceof ApiError && e.status === 409) {
        // 이미 해제된 경우 — 재조회로 상태 동기화
        try {
          const { getVerdict } = await import("@/lib/api/verdicts");
          const full = await getVerdict(verdict.verdict_id);
          setVerdict(full);
        } catch {
          setVerdict((prev) => ({ ...prev, diagnosis_unlocked: true }));
        }
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
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
          시각이 본 당신.
        </h1>
      </section>

      {/* GOLD 이미지 */}
      {gold && (
        <div
          style={{ padding: "0 28px", cursor: "pointer" }}
          onClick={() => setLightbox(true)}
        >
          <PhotoTile url={resolvePhotoUrl(gold.url)} aspectRatio="4/5" />
        </div>
      )}

      {/* 진단 보기 버튼 — GOLD 바로 아래 */}
      <div style={{ padding: "20px 28px 0" }}>
        <DiagnosisButton
          locked={!released}
          remainingCount={remaining.length}
          onClick={() => setShowDiagnosis(true)}
        />
      </div>

      {/* Reading (무료) */}
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

      {/* Footer — 공유 */}
      <section
        style={{
          padding: "32px 28px 24px",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <ShareButton verdictId={verdict.verdict_id} />
      </section>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />

      {/* Lightbox — GOLD 확대 */}
      {lightbox && gold && (
        <Lightbox url={resolvePhotoUrl(gold.url)} onClose={() => setLightbox(false)} />
      )}

      {/* Diagnosis Modal */}
      {showDiagnosis && (
        <DiagnosisModal
          verdict={verdict}
          remaining={remaining}
          released={released}
          balance={balance}
          busy={releasing}
          error={releaseError}
          onClose={() => setShowDiagnosis(false)}
          onProCta={handleProCta}
        />
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

function PhotoTile({ url, aspectRatio }: { url: string; aspectRatio: string }) {
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
      style={{ fontSize: 14, fontWeight: 400, color: "var(--color-ink)" }}
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
//  ShareButton — Web Share API + clipboard fallback
// ─────────────────────────────────────────────

function ShareButton({ verdictId }: { verdictId: string }) {
  const [feedback, setFeedback] = useState<string | null>(null);

  async function handleShare() {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}/verdict/${verdictId}`;
    const shareData = {
      title: "SIGAK — 시각이 본 당신",
      text: "오늘 한 장.",
      url,
    };

    const nav = navigator as Navigator & {
      share?: (data: ShareData) => Promise<void>;
      canShare?: (data: ShareData) => boolean;
    };

    // 1) Native share (모바일)
    if (nav.share) {
      try {
        await nav.share(shareData);
        return;
      } catch (e) {
        // AbortError = 사용자가 공유 취소, 무시
        if (e instanceof DOMException && e.name === "AbortError") return;
        // 그 외 → clipboard fallback으로 진행
      }
    }

    // 2) Clipboard fallback (데스크톱)
    try {
      await navigator.clipboard.writeText(url);
      setFeedback("링크 복사됨");
      setTimeout(() => setFeedback(null), 2000);
    } catch {
      setFeedback("공유 실패");
      setTimeout(() => setFeedback(null), 2000);
    }
  }

  return (
    <button
      type="button"
      onClick={handleShare}
      className="font-sans"
      style={{
        background: "transparent",
        border: "none",
        padding: 0,
        fontSize: 13,
        opacity: 0.55,
        letterSpacing: "-0.005em",
        cursor: "pointer",
        color: "var(--color-ink)",
      }}
    >
      {feedback ?? "공유"}
    </button>
  );
}

// ─────────────────────────────────────────────
//  DiagnosisButton — GOLD 아래 CTA
// ─────────────────────────────────────────────

function DiagnosisButton({
  locked,
  remainingCount,
  onClick,
}: {
  locked: boolean;
  remainingCount: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="font-sans"
      style={{
        width: "100%",
        height: 48,
        background: "transparent",
        color: "var(--color-ink)",
        border: "1px solid rgba(0, 0, 0, 0.25)",
        borderRadius: 0,
        fontSize: 13,
        fontWeight: 600,
        letterSpacing: "0.3px",
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
        padding: "0 18px",
      }}
    >
      <span>진단 보기</span>
      {locked && (
        <>
          <svg width="11" height="12" viewBox="0 0 11 12" aria-hidden style={{ opacity: 0.5 }}>
            <rect
              x="1.5"
              y="5.5"
              width="8"
              height="6"
              rx="0.8"
              stroke="var(--color-ink)"
              strokeWidth="1"
              fill="none"
            />
            <path
              d="M3.5 5.5V3.5a2 2 0 014 0v2"
              stroke="var(--color-ink)"
              strokeWidth="1"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
          <span
            className="font-serif tabular-nums"
            style={{ fontSize: 13, fontWeight: 400 }}
          >
            {DIAGNOSIS_COST} 토큰
          </span>
        </>
      )}
      {!locked && remainingCount > 0 && (
        <span
          className="font-serif tabular-nums"
          style={{ fontSize: 13, fontWeight: 400, opacity: 0.5 }}
        >
          · 나머지 {remainingCount}장
        </span>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────
//  DiagnosisModal
// ─────────────────────────────────────────────

function DiagnosisModal({
  verdict,
  remaining,
  released,
  balance,
  busy,
  error,
  onClose,
  onProCta,
}: {
  verdict: VerdictResponse;
  remaining: TierPhoto[];
  released: boolean;
  balance: number | null;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onProCta: () => void;
}) {
  return (
    <div
      className="animate-fade-in"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 100,
        background: "var(--color-paper)",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
      }}
      role="dialog"
      aria-modal="true"
      aria-label="진단"
    >
      {/* 상단: Close + 타이틀 */}
      <header
        style={{
          position: "sticky",
          top: 0,
          zIndex: 10,
          height: 52,
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 20px",
          flexShrink: 0,
        }}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="닫기"
          style={{
            width: 32,
            height: 32,
            padding: 0,
            background: "transparent",
            border: "none",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
            <path
              d="M1 1l12 12M13 1L1 13"
              stroke="var(--color-paper)"
              strokeWidth="1"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </button>
        <span
          className="font-sans"
          style={{
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "4px",
            color: "var(--color-paper)",
          }}
        >
          진단
        </span>
        <span style={{ width: 32 }} aria-hidden />
      </header>

      {/* 나머지 이미지 그리드 */}
      {remaining.length > 0 && (
        <section style={{ padding: "28px 28px 0" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              marginBottom: 12,
            }}
          >
            <Label>나머지</Label>
            <LabelRight>{remaining.length}장</LabelRight>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 4,
            }}
          >
            {remaining.map((photo) => (
              <ModalTile
                key={photo.photo_id}
                photo={photo}
                locked={!released}
              />
            ))}
          </div>
        </section>
      )}

      {/* PRO unlock or pro_data */}
      {!released ? (
        <ProUnlockSection
          balance={balance}
          busy={busy}
          error={error}
          onClick={onProCta}
        />
      ) : (
        <ProRevealedSection verdict={verdict} />
      )}

      <div style={{ height: 48 }} />
    </div>
  );
}

function ModalTile({
  photo,
  locked,
}: {
  photo: TierPhoto;
  locked: boolean;
}) {
  if (locked || !photo.url) {
    return (
      <div
        style={{
          aspectRatio: "1/1",
          overflow: "hidden",
          background: "rgba(0, 0, 0, 0.06)",
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            filter: "blur(10px)",
            transform: "scale(1.15)",
            background:
              "repeating-linear-gradient(32deg, rgba(0,0,0,0.08) 0 14px, rgba(0,0,0,0.02) 14px 15px)",
          }}
        />
      </div>
    );
  }
  const src = resolvePhotoUrl(photo.url);
  return (
    <div
      style={{
        aspectRatio: "1/1",
        overflow: "hidden",
        background: "rgba(0, 0, 0, 0.04)",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          display: "block",
        }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Pro Unlock Section (inside modal)
// ─────────────────────────────────────────────

function ProUnlockSection({
  balance,
  busy,
  error,
  onClick,
}: {
  balance: number | null;
  busy: boolean;
  error: string | null;
  onClick: () => void;
}) {
  const insufficient = balance != null && balance < DIAGNOSIS_COST;
  return (
    <section style={{ padding: "32px 28px 0" }}>
      <div
        style={{
          border: "1px solid rgba(0, 0, 0, 0.15)",
          padding: "24px 22px",
          background: "transparent",
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
          왜 이 한 장인가
        </div>

        <p
          className="font-sans"
          style={{
            marginTop: 8,
            marginBottom: 0,
            fontSize: 13,
            opacity: 0.55,
            lineHeight: 1.55,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          왜 이 사진이 최적인지, 나머지 사진들.
        </p>

        <button
          type="button"
          onClick={onClick}
          disabled={busy}
          className="font-sans"
          style={{
            marginTop: 20,
            width: "100%",
            height: 50,
            background: busy ? "transparent" : "var(--color-ink)",
            color: busy ? "var(--color-ink)" : "var(--color-paper)",
            border: busy ? "1px solid rgba(0, 0, 0, 0.15)" : "none",
            borderRadius: 0,
            fontSize: 13,
            fontWeight: 600,
            letterSpacing: "0.5px",
            cursor: busy ? "default" : "pointer",
            opacity: busy ? 0.5 : 1,
          }}
        >
          {busy
            ? "해제 중..."
            : `해제 · ${DIAGNOSIS_COST} 토큰`}
        </button>

        {insufficient && !busy && (
          <p
            className="font-sans"
            style={{
              marginTop: 10,
              marginBottom: 0,
              fontSize: 11,
              opacity: 0.5,
              letterSpacing: "-0.005em",
              textAlign: "right",
              color: "var(--color-ink)",
            }}
          >
            현재 잔액 {balance}토큰 — 충전 페이지로 안내
          </p>
        )}
        {error && (
          <p
            className="font-sans"
            style={{
              marginTop: 10,
              marginBottom: 0,
              fontSize: 11,
              letterSpacing: "-0.005em",
              textAlign: "right",
              color: "var(--color-danger)",
            }}
            role="alert"
          >
            {error}
          </p>
        )}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────
//  Pro Revealed Section (inside modal)
// ─────────────────────────────────────────────

function ProRevealedSection({ verdict }: { verdict: VerdictResponse }) {
  const data = verdict.pro_data;
  if (!data) return null;
  const all = [...data.silver_readings, ...data.bronze_readings];
  return (
    <section style={{ padding: "32px 28px 0" }}>
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
              #{String(i + 2).padStart(2, "0")} · Δ shape{" "}
              {formatDelta(r.axis_delta.shape)}, volume{" "}
              {formatDelta(r.axis_delta.volume)}, age{" "}
              {formatDelta(r.axis_delta.age)}
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
    </section>
  );
}

function formatDelta(n: number): string {
  const rounded = Math.round(n * 100) / 100;
  const sign = rounded > 0 ? "+" : "";
  return `${sign}${rounded}`;
}

// ─────────────────────────────────────────────
//  Lightbox (GOLD 확대)
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
        zIndex: 200,
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
