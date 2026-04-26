/**
 * /sia/done — Sia 세션 종료 직후 흐름.
 *
 * 흐름:
 *   /sia (대화) → /sia/done?report={sessionId}
 *     → LoadingSlides 15s
 *     → VerdictUploadView (redesign/업로드_1815.html 패턴)
 *     → createVerdictV2 (사진 3-5장)
 *     → AnalyzingScreen
 *     → /verdict/{id}
 *
 * Phase B-7 (PI-REVIVE 2026-04-26): 본인 결정 — Sia 초회 사용 직후
 * verdict 무조건 1회 강제 사용. /photo-upload 옛 SIGAK_V3 흐름 폐기,
 * 홈으로 escape link 제거. redesign/업로드_1815.html 기준 디자인 차용
 * (토큰은 globals.css 그대로, UI 패턴/카피만 차용).
 *
 * query: ?report={session_id} 필수. 없으면 홈으로.
 */

"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { LoadingSlides } from "@/components/sia/LoadingSlides";
import { AnalyzingScreen } from "@/components/sigak/analyzing-screen";
import { TokenInsufficientModal } from "@/components/sigak/token-insufficient-modal";
import { useTokenBalance } from "@/hooks/use-token-balance";
import {
  createVerdictV2,
  MIN_PHOTOS,
  MAX_PHOTOS,
} from "@/lib/api/verdicts";
import { ApiError } from "@/lib/api/fetch";

// 2026-04-26 선결제 — 사진 장당 3 토큰 (HomeScreen 과 일치).
const COST_PER_PHOTO = 3;

interface UploadItem {
  file: File;
  previewUrl: string;
}

function DoneContent() {
  const router = useRouter();
  const params = useSearchParams();
  const reportId = params.get("report");
  const [slidesDone, setSlidesDone] = useState(false);

  useEffect(() => {
    if (!reportId) {
      router.replace("/");
    }
  }, [reportId, router]);

  if (!reportId) {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-hidden
      />
    );
  }

  if (!slidesDone) {
    return <LoadingSlides onComplete={() => setSlidesDone(true)} />;
  }

  return <VerdictUploadView />;
}

function VerdictUploadView() {
  const router = useRouter();
  const { balance } = useTokenBalance();
  const [items, setItems] = useState<UploadItem[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisDone, setAnalysisDone] = useState(false);
  const verdictIdRef = useRef<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showTokenModal, setShowTokenModal] = useState(false);

  // 슬롯별 파일 input ref (각 슬롯이 독립 input)
  const slotInputs = useRef<Array<HTMLInputElement | null>>([null, null, null]);

  useEffect(() => {
    return () => {
      for (const it of items) URL.revokeObjectURL(it.previewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSlotChange(idx: number, files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);
    const fileArr = Array.from(files);
    setItems((prev) => {
      const next = [...prev];
      // 첫 파일은 클릭한 슬롯에 (replace 가능)
      const replaced = next[idx];
      if (replaced) URL.revokeObjectURL(replaced.previewUrl);
      next[idx] = {
        file: fileArr[0],
        previewUrl: URL.createObjectURL(fileArr[0]),
      };
      // Phase B-7.1: multiple 선택 시 추가 파일은 다음 빈 슬롯 spillover
      // 본인 모바일 피드백: "사진 올리기 너무 불편" → 갤러리에서 batch 선택 → 자동 채움
      let cursor = idx + 1;
      for (let i = 1; i < fileArr.length && cursor < 3; i++) {
        // 빈 슬롯 찾기 (이미 차 있으면 skip)
        while (cursor < 3 && next[cursor]) cursor++;
        if (cursor >= 3) break;
        next[cursor] = {
          file: fileArr[i],
          previewUrl: URL.createObjectURL(fileArr[i]),
        };
        cursor++;
      }
      return next;
    });
  }

  function removeAt(idx: number) {
    setItems((prev) => {
      const next = [...prev];
      const target = next[idx];
      if (target) URL.revokeObjectURL(target.previewUrl);
      delete next[idx];
      return next;
    });
    // 해당 슬롯 input value reset (다음 같은 파일 선택 가능)
    const inp = slotInputs.current[idx];
    if (inp) inp.value = "";
  }

  // 실제 채워진 파일 list (sparse → dense)
  const filledFiles: File[] = items
    .filter((it): it is UploadItem => Boolean(it))
    .map((it) => it.file);
  const filledCount = filledFiles.length;
  const canStart = filledCount >= MIN_PHOTOS;

  async function handleStart() {
    if (!canStart || analyzing) return;

    const requiredCost = filledCount * COST_PER_PHOTO;
    if (balance !== null && balance < requiredCost) {
      setShowTokenModal(true);
      return;
    }

    setAnalyzing(true);
    setAnalysisDone(false);
    verdictIdRef.current = null;
    setError(null);

    try {
      const response = await createVerdictV2(filledFiles);
      verdictIdRef.current = response.verdict_id;
      setAnalysisDone(true);
    } catch (e) {
      setAnalyzing(false);
      setAnalysisDone(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      if (e instanceof ApiError && e.status === 402) {
        setShowTokenModal(true);
        return;
      }
      setError(
        e instanceof Error
          ? e.message
          : "판정 생성에 실패했어요. 잠시 후 다시 시도해 주세요.",
      );
    }
  }

  function handleAnalysisFinish() {
    const id = verdictIdRef.current;
    if (id) router.replace(`/verdict/${id}`);
  }

  if (analyzing) {
    return (
      <AnalyzingScreen
        candidateCount={filledCount}
        done={analysisDone}
        onFinish={handleAnalysisFinish}
      />
    );
  }

  return (
    <main
      className="animate-fade-in"
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Top nav — 중앙 SIGAK (TopBar 정합) */}
      <nav
        style={{
          height: 52,
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          flexShrink: 0,
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span
            className="font-sans"
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "6px",
              color: "var(--color-paper)",
            }}
          >
            SIGAK
          </span>
        </div>
      </nav>

      {/* Page content */}
      <section
        style={{
          flex: 1,
          maxWidth: 440,
          margin: "0 auto",
          width: "100%",
          padding: "44px 24px 80px",
        }}
      >
        {/* Phase B-7.2: Sia · Done oval badge 제거 (본인 피드백 — 좌상단 안 좋음) */}

        {/* Headline */}
        <h2
          className="font-serif"
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: "var(--color-ink)",
            lineHeight: 1.42,
            letterSpacing: "-0.022em",
            margin: 0,
            marginBottom: 10,
            wordBreak: "keep-all",
          }}
        >
          피드와 추구미 분석이<br />
          완료되었어요
          <span style={{ color: "var(--color-danger)" }}>!</span>
        </h2>
        <p
          className="font-sans"
          style={{
            fontSize: 14,
            color: "var(--color-mute)",
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
            margin: 0,
            marginBottom: 36,
            wordBreak: "keep-all",
          }}
        >
          정밀 분석 받고 싶은 피드, 사진이나 프사를<br />
          {MIN_PHOTOS}장 올려주세요
        </p>

        {/* Photo slots — 3 column grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 10,
            marginBottom: 14,
          }}
        >
          {[0, 1, 2].map((idx) => {
            const item = items[idx];
            const filled = Boolean(item);
            return (
              <div
                key={idx}
                style={{
                  aspectRatio: "3 / 4",
                  borderRadius: 12,
                  border: filled
                    ? "1.5px solid var(--color-line)"
                    : "1.5px dashed var(--color-line-strong)",
                  background: filled
                    ? "transparent"
                    : "rgba(0, 0, 0, 0.03)",
                  position: "relative",
                  overflow: "hidden",
                  cursor: "pointer",
                  transition: "border-color 0.2s ease, background 0.2s ease",
                }}
              >
                <input
                  ref={(el) => {
                    slotInputs.current[idx] = el;
                  }}
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={(e) => handleSlotChange(idx, e.target.files)}
                  style={{
                    position: "absolute",
                    inset: 0,
                    opacity: 0,
                    cursor: "pointer",
                    zIndex: 2,
                  }}
                  aria-label={`사진 ${idx + 1} 추가 (여러 장 선택 가능)`}
                />
                {filled ? (
                  <>
                    <img
                      src={item.previewUrl}
                      alt={`사진 ${idx + 1}`}
                      style={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        borderRadius: 10,
                      }}
                    />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        removeAt(idx);
                      }}
                      aria-label={`사진 ${idx + 1} 삭제`}
                      style={{
                        position: "absolute",
                        top: 7,
                        right: 7,
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        background: "rgba(45, 45, 45, 0.65)",
                        color: "#fff",
                        fontSize: 12,
                        lineHeight: "22px",
                        textAlign: "center",
                        border: "none",
                        cursor: "pointer",
                        padding: 0,
                        zIndex: 3,
                        fontFamily: "inherit",
                      }}
                    >
                      ✕
                    </button>
                  </>
                ) : (
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                      pointerEvents: "none",
                    }}
                  >
                    <span
                      className="uppercase"
                      style={{
                        position: "absolute",
                        top: 10,
                        left: 12,
                        fontFamily: "var(--font-mono, monospace)",
                        fontSize: 10,
                        letterSpacing: "0.14em",
                        color: "var(--color-mute-2, var(--color-mute))",
                      }}
                    >
                      {String(idx + 1).padStart(2, "0")}
                    </span>
                    <div
                      style={{
                        fontSize: 22,
                        color: "var(--color-mute-2, var(--color-mute))",
                        lineHeight: 1,
                        marginTop: 16,
                      }}
                    >
                      +
                    </div>
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--color-mute-2, var(--color-mute))",
                        letterSpacing: "-0.005em",
                      }}
                    >
                      사진 추가
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Count dots */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            marginBottom: 10,
          }}
        >
          {[0, 1, 2].map((idx) => (
            <div
              key={idx}
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background:
                  idx < filledCount
                    ? "var(--color-danger)"
                    : "var(--color-line-strong)",
                transition: "background 0.2s ease",
              }}
            />
          ))}
        </div>

        <p
          className="font-sans"
          style={{
            fontSize: 12.5,
            color: "var(--color-mute)",
            textAlign: "center",
            letterSpacing: "-0.005em",
            margin: 0,
            marginBottom: 32,
            lineHeight: 1.5,
          }}
        >
          정밀 분석을 위해 {MIN_PHOTOS}장 모두 올려주세요. 갤러리에서 여러 장 한번에 선택 가능
        </p>

        {error && (
          <p
            className="font-sans"
            role="alert"
            style={{
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              textAlign: "center",
              margin: 0,
              marginBottom: 16,
            }}
          >
            {error}
          </p>
        )}

        {/* CTA */}
        <button
          type="button"
          onClick={handleStart}
          disabled={!canStart}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            width: "100%",
            padding: "17px 24px",
            background: canStart ? "var(--color-ink)" : "var(--color-line-strong)",
            color: "var(--color-paper)",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor: canStart ? "pointer" : "not-allowed",
            transition: "all 0.25s ease",
          }}
        >
          정밀 분석 시작하기 →
        </button>
        <p
          className="uppercase"
          style={{
            textAlign: "center",
            fontFamily: "var(--font-mono, monospace)",
            fontSize: 11,
            letterSpacing: "0.08em",
            color: "var(--color-mute)",
            marginTop: 10,
            marginBottom: 0,
            minHeight: 16,
          }}
        >
          {filledCount > 0 ? `🪙 ${filledCount * COST_PER_PHOTO}토큰` : ""}
        </p>
      </section>

      <TokenInsufficientModal
        open={showTokenModal}
        balance={balance ?? 0}
        required={filledCount * COST_PER_PHOTO}
        onCharge={() => router.push("/tokens/purchase?intent=verdict_v2")}
        onClose={() => setShowTokenModal(false)}
      />
    </main>
  );
}

export default function SiaDonePage() {
  return (
    <Suspense
      fallback={
        <div
          style={{ minHeight: "100vh", background: "var(--color-paper)" }}
          aria-hidden
        />
      }
    >
      <DoneContent />
    </Suspense>
  );
}
