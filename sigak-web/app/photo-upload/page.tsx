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

  // 진행 중 화면
  if (submitting) {
    const stageLabel =
      stage === "submit"
        ? "사진 보내는 중"
        : stage === "analyze"
          ? "분석하는 중"
          : "처리 중";
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
          padding: "60px 28px",
        }}
        aria-busy
      >
        <p
          className="font-sans uppercase"
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
            marginBottom: 16,
          }}
        >
          {stageLabel}
        </p>
        <h2
          className="font-serif"
          style={{
            fontSize: 24,
            fontWeight: 400,
            lineHeight: 1.4,
            letterSpacing: "-0.01em",
            textAlign: "center",
            maxWidth: 320,
          }}
        >
          {stage === "analyze"
            ? "한참 들여다보고 있어요.\n조금만요."
            : "정면 사진을 받고 있어요."}
        </h2>
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

        {/* 사진 슬롯 그리드 — 정면 1 + 측면 2 */}
        <div
          style={{
            marginTop: 32,
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 12,
          }}
        >
          {Array.from({ length: MAX_PHOTOS }, (_, i) => {
            const photo = photos[i];
            const slotLabels = ["정면", "측면 1", "측면 2"];
            return (
              <div
                key={i}
                style={{
                  aspectRatio: "3 / 4",
                  border: "1px solid var(--color-line-strong)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                  position: "relative",
                  background: "var(--color-paper)",
                }}
              >
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
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => handleRemove(i)}
                      className="font-sans"
                      aria-label={`${slotLabels[i]} 사진 제거`}
                      style={{
                        position: "absolute",
                        top: 6,
                        right: 6,
                        width: 22,
                        height: 22,
                        borderRadius: "50%",
                        border: 0,
                        background: "rgba(0,0,0,0.55)",
                        color: "#fff",
                        fontSize: 11,
                        cursor: "pointer",
                      }}
                    >
                      ×
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
                        border: 0,
                        background: "rgba(0,0,0,0.55)",
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
                      gap: 6,
                    }}
                  >
                    <span style={{ fontSize: 24, opacity: 0.3 }}>+</span>
                    <span
                      style={{
                        fontSize: 11,
                        opacity: 0.5,
                        letterSpacing: "-0.005em",
                      }}
                    >
                      {slotLabels[i]}
                    </span>
                    {i === 0 && (
                      <span
                        style={{
                          fontSize: 10,
                          opacity: 0.4,
                          letterSpacing: "-0.005em",
                        }}
                      >
                        필수
                      </span>
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
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

      {/* 제출 영역 */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginInline: "auto",
          maxWidth: 380,
          width: "100%",
        }}
      >
        <button
          type="button"
          onClick={handleSubmit}
          disabled={photos.length === 0 || submitting}
          className="font-sans"
          style={{
            display: "block",
            width: "100%",
            padding: "18px 22px",
            border: 0,
            background:
              photos.length === 0 ? "var(--color-line-strong)" : "var(--color-ink)",
            color: "var(--color-paper)",
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.005em",
            cursor:
              photos.length === 0 || submitting ? "not-allowed" : "pointer",
            opacity: photos.length === 0 ? 0.5 : 1,
          }}
        >
          {photos.length === 0 ? "정면 한 장만 있어도 시작" : "분석 시작"}
        </button>
        <a
          href="/"
          className="font-sans"
          style={{
            display: "block",
            height: 48,
            lineHeight: "48px",
            textAlign: "center",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "0.3px",
            opacity: 0.5,
            color: "var(--color-ink)",
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
