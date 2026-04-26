/**
 * /photo-upload — Sia 종료 → 사진 업로드 → 옛 SIGAK_V3 PI 시스템 entry.
 *
 * Flow:
 *   /sia → /sia/done (LoadingSlides 15s) → /photo-upload (이 페이지)
 *   → POST /api/v1/submit (사진 + interview JSON)
 *   → POST /api/v1/analyze/{user_id} (AI 파이프라인)
 *   → /report/{report_id}/full redirect
 *
 * BETA 5/15 까지 무료. backend `_is_pi_beta_free()` 가 access_level="full" 강제.
 *
 * 입력:
 *   - query ?from_session={sessionId}  옵션, Sia session reference (현재 미사용)
 *   - localStorage `sigak_user_id`  필수 (Kakao 로그인)
 *
 * 페르소나 B 톤:
 *   - "정면 사진 한 장 보여주세요"
 *   - "얼굴이 또렷하게 잡히는 사진이면 돼요. 화장은 안 하셔도 분석 가능해요."
 */

"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  ApiError,
  runAnalysis,
  submitAll,
} from "@/lib/api/client";
import { getCurrentUser } from "@/lib/auth";

const MAX_PHOTOS = 3;

interface PhotoEntry {
  url: string;
  file: File;
}

function PhotoUploadContent() {
  const router = useRouter();
  const params = useSearchParams();
  const fromSession = params.get("from_session");

  const [photos, setPhotos] = useState<PhotoEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [stage, setStage] = useState<"idle" | "submit" | "analyze">("idle");
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const replaceIdxRef = useRef<number | null>(null);

  // 인증 가드
  useEffect(() => {
    const user = getCurrentUser();
    if (!user) {
      router.replace("/");
    }
  }, [router]);

  // unmount 시 object URL 해제
  useEffect(() => {
    return () => {
      photos.forEach((p) => URL.revokeObjectURL(p.url));
    };
    // 의도적으로 mount 시점 photos snapshot 만 cleanup. ignore deps lint.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const url = URL.createObjectURL(file);

      if (replaceIdxRef.current !== null) {
        const idx = replaceIdxRef.current;
        setPhotos((prev) => {
          const next = [...prev];
          if (next[idx]) URL.revokeObjectURL(next[idx].url);
          next[idx] = { url, file };
          return next;
        });
        replaceIdxRef.current = null;
      } else {
        setPhotos((prev) => [...prev, { url, file }]);
      }
      e.target.value = "";
    },
    [],
  );

  const handleAdd = useCallback(() => {
    replaceIdxRef.current = null;
    fileRef.current?.click();
  }, []);

  const handleReplace = useCallback((idx: number) => {
    replaceIdxRef.current = idx;
    fileRef.current?.click();
  }, []);

  const handleRemove = useCallback((idx: number) => {
    setPhotos((prev) => {
      const removed = prev[idx];
      if (removed) URL.revokeObjectURL(removed.url);
      return prev.filter((_, i) => i !== idx);
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (photos.length === 0) return;
    const user = getCurrentUser();
    if (!user) {
      router.replace("/");
      return;
    }

    setSubmitting(true);
    setError(null);
    setStage("submit");

    try {
      const files = photos.map((p) => p.file);

      // Phase 1: /api/v1/submit — 사진 + 최소 interview JSON 저장
      // Sia 대화 결과는 신 vault 에 별도 저장됨. 옛 main.py 는 자체 INTERVIEWS dict 사용.
      // 최소 필드 (name / gender / tier) 만 전달, 나머지는 옵션이라 누락 OK.
      const submitResult = await submitAll(
        {
          user_id: user.userId,
          name: user.name || "익명",
          gender: "female",
          tier: "standard",
          ...(fromSession ? { sia_session_id: fromSession } : {}),
        },
        files,
      );

      // Phase 2: /api/v1/analyze/{user_id} — AI 파이프라인 실행 → report_id 회수
      setStage("analyze");
      const analyzeResult = await runAnalysis(submitResult.user_id);

      if (!analyzeResult.report_id) {
        throw new Error("리포트 생성에 실패했어요.");
      }

      // Phase 3: /report/{report_id}/full redirect
      // BETA 우회 분기로 backend 가 access_level="full" 강제 응답 → paywall 미노출.
      router.replace(`/report/${analyzeResult.report_id}/full`);
    } catch (err) {
      setSubmitting(false);
      setStage("idle");
      if (err instanceof ApiError) {
        if (err.status === 401) {
          router.replace("/");
          return;
        }
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("제출 중 오류가 발생했어요. 잠시 후 다시 시도해 주세요.");
      }
    }
  }, [photos, router, fromSession]);

  // 진행 중 화면 — 마케터 redesign/로딩_1815.html 차용 (dotPulse + 로고 + 서브 힌트)
  if (submitting) {
    return (
      <main
        style={{
          minHeight: "100vh",
          background: "var(--color-paper)",
          color: "var(--color-ink)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "40px 28px",
          textAlign: "center",
        }}
        aria-busy
      >
        {/* SIGAK 로고 60x60 */}
        <svg
          width="60"
          height="60"
          viewBox="0 0 40 40"
          xmlns="http://www.w3.org/2000/svg"
          style={{ marginBottom: 40 }}
          aria-hidden
        >
          <rect width="40" height="40" rx="7" fill="#1a1a1a" />
          <g stroke="#ffffff" strokeWidth="1.5" fill="none" strokeLinecap="round">
            <line x1="20" y1="6" x2="20" y2="13" />
            <path d="M 6 19.5 Q 20 11.5 34 19.5 Q 20 27.5 6 19.5 Z" />
            <circle cx="20" cy="19.5" r="2.6" />
          </g>
          <path
            d="M 20 22.5 C 18.4 25, 17.4 28, 17.4 30 C 17.4 31.9, 18.6 32.8, 20 32.8 C 21.4 32.8, 22.6 31.9, 22.6 30 C 22.6 28, 21.6 25, 20 22.5 Z"
            fill="#ffffff"
          />
        </svg>

        <p
          className="font-sans"
          style={{
            fontSize: 16,
            color: "var(--color-ink)",
            opacity: 0.75,
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
            marginBottom: 28,
          }}
        >
          sia가 피드를 분석중이에요.
        </p>

        {/* dot-pulse 3-dot */}
        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            marginBottom: 36,
          }}
          aria-hidden
        >
          <span
            className="animate-dot-pulse"
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--color-danger)",
            }}
          />
          <span
            className="animate-dot-pulse-delay-1"
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--color-danger)",
            }}
          />
          <span
            className="animate-dot-pulse-delay-2"
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--color-danger)",
            }}
          />
        </div>

        <p
          className="font-sans"
          style={{
            fontSize: 12,
            color: "var(--color-mute)",
            letterSpacing: "-0.003em",
          }}
        >
          최대 30초 정도 걸릴 수 있어요
        </p>
      </main>
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
        padding: "60px 28px 40px",
      }}
    >
      <section
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          maxWidth: 380,
          width: "100%",
          marginInline: "auto",
        }}
      >
        <span
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
          }}
        >
          PHOTO
        </span>
        <h1
          className="font-serif"
          style={{
            marginTop: 16,
            fontSize: 28,
            fontWeight: 400,
            lineHeight: 1.4,
            letterSpacing: "-0.01em",
          }}
        >
          정면 사진 한 장<br />
          보여주세요.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 16,
            fontSize: 13,
            lineHeight: 1.7,
            letterSpacing: "-0.005em",
            opacity: 0.6,
          }}
        >
          얼굴이 또렷하게 잡히는 사진이면 돼요.
          <br />
          화장은 안 하셔도 분석 가능해요.
        </p>

        {/* 사진 슬롯 그리드 — 정면 1 + 측면 2 (마케터 dashed + 슬롯 번호 차용) */}
        <div
          style={{
            marginTop: 32,
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 10,
          }}
        >
          {Array.from({ length: MAX_PHOTOS }, (_, i) => {
            const photo = photos[i];
            const slotLabels = ["정면", "측면 1", "측면 2"];
            const slotNum = `0${i + 1}`;
            const filled = !!photo;
            return (
              <div
                key={i}
                style={{
                  aspectRatio: "3 / 4",
                  borderRadius: 12,
                  border: filled
                    ? "1.5px solid var(--color-line-strong)"
                    : "1.5px dashed var(--color-line-strong)",
                  background: filled ? "transparent" : "rgba(0, 0, 0, 0.04)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                  position: "relative",
                  transition: "border-color 0.2s ease, background 0.2s ease",
                }}
              >
                {/* 슬롯 번호 (좌상단) */}
                <span
                  style={{
                    position: "absolute",
                    top: 10,
                    left: 12,
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    letterSpacing: "0.14em",
                    color: filled ? "rgba(255,255,255,0.85)" : "var(--color-mute-2)",
                    textShadow: filled ? "0 1px 2px rgba(0,0,0,0.4)" : "none",
                    zIndex: 1,
                  }}
                >
                  {slotNum}
                </span>

                {photo ? (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={photo.url}
                      alt={slotLabels[i]}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        borderRadius: 10,
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => handleRemove(i)}
                      className="font-sans"
                      aria-label={`${slotLabels[i]} 사진 제거`}
                      style={{
                        position: "absolute",
                        top: 7,
                        right: 7,
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        border: 0,
                        background: "rgba(45,45,45,0.65)",
                        color: "#fff",
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                    >
                      ✕
                    </button>
                    <button
                      type="button"
                      onClick={() => handleReplace(i)}
                      className="font-sans"
                      style={{
                        position: "absolute",
                        bottom: 6,
                        left: 6,
                        right: 6,
                        padding: "4px 0",
                        borderRadius: 6,
                        border: 0,
                        background: "rgba(45,45,45,0.65)",
                        color: "#fff",
                        fontSize: 10,
                        letterSpacing: "0.3px",
                        cursor: "pointer",
                      }}
                    >
                      재촬영
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    onClick={handleAdd}
                    className="font-sans"
                    aria-label={`${slotLabels[i]} 추가`}
                    style={{
                      width: "100%",
                      height: "100%",
                      border: 0,
                      background: "transparent",
                      color: "var(--color-ink)",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 8,
                    }}
                  >
                    <span style={{ fontSize: 22, color: "var(--color-mute-2)", lineHeight: 1 }}>
                      +
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        color: "var(--color-mute)",
                        letterSpacing: "-0.005em",
                      }}
                    >
                      {slotLabels[i]}
                    </span>
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* count-dot 3개 (마케터 차용) */}
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 8,
            marginTop: 14,
          }}
          aria-hidden
        >
          {Array.from({ length: MAX_PHOTOS }, (_, i) => (
            <span
              key={i}
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background:
                  i < photos.length ? "var(--color-danger)" : "var(--color-line-strong)",
                transition: "background 0.2s ease",
              }}
            />
          ))}
        </div>

        {/* Phase B-7.1 (PI-REVIVE 2026-04-26): capture 속성 제거.
            본인 모바일 피드백: "PI 레포트는 사진 찍게하는데 저건 말도안되고".
            capture="environment" 가 카메라 강제 → 제거 시 OS 피커가
            갤러리/카메라/파일 모두 선택지로 노출. */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          style={{ display: "none" }}
        />

        {error && (
          <p
            role="alert"
            className="font-sans"
            style={{
              marginTop: 16,
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
          >
            {error}
          </p>
        )}
      </section>

      {/* 제출 영역 — 마케터 pill CTA + BETA 무료 라벨 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 4,
          marginInline: "auto",
          maxWidth: 380,
          width: "100%",
          marginTop: 28,
        }}
      >
        <button
          type="button"
          onClick={handleSubmit}
          disabled={photos.length === 0 || submitting}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            width: "100%",
            padding: "17px 24px",
            border: 0,
            borderRadius: 100,
            background:
              photos.length === 0 ? "var(--color-line-strong)" : "var(--color-ink)",
            color: "var(--color-paper)",
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor:
              photos.length === 0 || submitting ? "not-allowed" : "pointer",
            transition: "all 0.25s ease",
          }}
        >
          {photos.length === 0
            ? "사진을 1장 이상 올려주세요"
            : "정밀 분석 시작하기 →"}
        </button>
        <p
          className="font-sans"
          style={{
            textAlign: "center",
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            letterSpacing: "0.08em",
            color: "var(--color-mute)",
            marginTop: 10,
            minHeight: 16,
          }}
        >
          BETA 기간 무료
        </p>
        <a
          href="/"
          className="font-sans"
          style={{
            display: "block",
            height: 44,
            lineHeight: "44px",
            textAlign: "center",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.3px",
            color: "var(--color-mute)",
            textDecoration: "none",
            marginTop: 4,
          }}
        >
          나중에 (홈으로)
        </a>
      </div>
    </main>
  );
}

export default function PhotoUploadPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{ minHeight: "100vh", background: "var(--color-paper)" }}
          aria-hidden
        />
      }
    >
      <PhotoUploadContent />
    </Suspense>
  );
}
