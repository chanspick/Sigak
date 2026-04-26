/**
 * /pi/upload — 정면 baseline 사진 업로드 (Phase I PI-D).
 *
 * 흐름:
 *   transition CTA → /pi/upload?next=preview
 *   사진 선택 (native picker) → uploadPIv3Baseline → 성공 시 next param 으로 redirect
 *     - next=preview  : /pi/preview 로 → preview 자동 생성
 *     - next=vision   : /vision 로 (PI 진입점 재진입)
 *     - 기본          : /pi/preview
 *
 * 화장 검증:
 *   서버 응답 makeup_warning 이 채워지면 soft toast (블락 X).
 */

"use client";

import { Suspense, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { ApiError } from "@/lib/api/fetch";
import { uploadPIv3Baseline } from "@/lib/api/pi";

function UploadContent() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "preview";

  const inputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  function pickFile() {
    inputRef.current?.click();
  }

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    // 클라이언트 사전 검증 — 10MB hard limit
    const MAX_SIZE = 10 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setError("사진은 10MB 이하로 부탁해요.");
      return;
    }
    if (!file.type.startsWith("image/")) {
      setError("이미지 파일만 올려주세요.");
      return;
    }

    setUploading(true);
    setError(null);
    setWarning(null);

    try {
      const res = await uploadPIv3Baseline(file);
      if (res.makeup_warning) {
        setWarning(res.makeup_warning);
      }
      // 성공 → next 분기
      const target = next === "vision" ? "/vision" : "/pi/preview";
      router.replace(target);
    } catch (e) {
      setUploading(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
        return;
      }
      setError(
        e instanceof Error ? e.message : "사진 업로드에 실패했어요.",
      );
    }
  }

  return (
    <main
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
          justifyContent: "center",
          maxWidth: 380,
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
          정면 한 컷,<br />가능한 한 또렷하게
        </h1>
        <ul
          className="font-sans"
          style={{
            marginTop: 20,
            paddingLeft: 16,
            fontSize: 13,
            lineHeight: 1.8,
            opacity: 0.6,
            letterSpacing: "-0.005em",
          }}
        >
          <li>밝은 곳, 정면을 바라보는 사진</li>
          <li>얼굴이 가려지지 않은 한 사람</li>
          <li>화장 유무는 분석에 영향 없어요</li>
        </ul>

        {warning && (
          <div
            role="alert"
            className="font-sans"
            style={{
              marginTop: 16,
              padding: "10px 14px",
              border: "1px solid rgba(0,0,0,0.15)",
              fontSize: 12,
              lineHeight: 1.7,
              opacity: 0.75,
              letterSpacing: "-0.005em",
            }}
          >
            {warning}
          </div>
        )}
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

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={onFileChange}
          style={{ display: "none" }}
          aria-label="정면 사진 업로드"
        />
        <button
          type="button"
          onClick={pickFile}
          disabled={uploading}
          className="font-sans"
          style={{
            width: "100%",
            height: 54,
            background: uploading ? "transparent" : "var(--color-ink)",
            color: uploading ? "var(--color-ink)" : "var(--color-paper)",
            border: uploading ? "1px solid rgba(0,0,0,0.15)" : "none",
            borderRadius: 0,
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: "0.5px",
            cursor: uploading ? "default" : "pointer",
            opacity: uploading ? 0.55 : 1,
          }}
        >
          {uploading ? "분석 준비 중..." : "📷 갤러리에서 고르기"}
        </button>
        <Link
          href="/vision"
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
          }}
        >
          나중에 할게요
        </Link>
      </div>
    </main>
  );
}

export default function PIUploadPage() {
  return (
    <Suspense
      fallback={
        <div
          style={{ minHeight: "100vh", background: "var(--color-paper)" }}
          aria-hidden
        />
      }
    >
      <UploadContent />
    </Suspense>
  );
}
