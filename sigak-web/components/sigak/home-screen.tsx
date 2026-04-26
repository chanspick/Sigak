// SIGAK MVP v1.2 (Rebrand) — HomeScreen / Upload
//
// 3-col grid (Instagram 느낌), 인덱스 스탬프 제거, serif 헤드라인.
// 업로드 상태머신 + createVerdict 호출은 그대로 유지 (기능 동산).
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";
import { createVerdictV2, MAX_PHOTOS, UX_MIN_PHOTOS } from "@/lib/api/verdicts";
import { ApiError } from "@/lib/api/fetch";
import { AnalyzingScreen } from "./analyzing-screen";

// Analyzing 진행바가 POST 응답과 동기화되므로 별도 MIN 대기 불필요.
// 빠른 응답 → 약 2.9초(climb 2.5s + snap 0.4s)에 완료.
// 느린 응답 → 90%에서 hold 하며 응답 대기 후 완료.

interface UploadItem {
  file: File;
  previewUrl: string;
}

export function HomeScreen() {
  const router = useRouter();
  const [items, setItems] = useState<UploadItem[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisDone, setAnalysisDone] = useState(false);
  const verdictIdRef = useRef<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      for (const it of items) URL.revokeObjectURL(it.previewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilesSelected(fileList: FileList | null) {
    if (!fileList) return;
    const incoming = Array.from(fileList);
    const room = MAX_PHOTOS - items.length;
    if (room <= 0) return;
    const accepted = incoming.slice(0, room);
    const newItems: UploadItem[] = accepted.map((f) => ({
      file: f,
      previewUrl: URL.createObjectURL(f),
    }));
    setItems((prev) => [...prev, ...newItems]);
    setError(null);
  }

  function openPicker() {
    fileInputRef.current?.click();
  }

  function removeAt(index: number) {
    setItems((prev) => {
      const target = prev[index];
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((_, i) => i !== index);
    });
  }

  async function handleStart() {
    if (items.length < UX_MIN_PHOTOS || analyzing) return;
    setAnalyzing(true);
    setAnalysisDone(false);
    verdictIdRef.current = null;
    setError(null);

    try {
      // v2 cross-analysis 로 전환 — 응답에 preview(hook_line+reason_summary) 포함.
      // full_content 는 /verdict/[id] 에서 10 토큰 unlock.
      const response = await createVerdictV2(items.map((it) => it.file));
      verdictIdRef.current = response.verdict_id;
      setAnalysisDone(true); // AnalyzingScreen이 90→100%로 snap 후 onFinish 호출
    } catch (e) {
      setAnalyzing(false);
      setAnalysisDone(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setError(
        e instanceof Error
          ? e.message
          : "판정 생성에 실패했습니다. 다시 시도해주세요.",
      );
    }
  }

  function handleAnalysisFinish() {
    const id = verdictIdRef.current;
    if (id) router.push(`/verdict/${id}`);
  }

  if (analyzing) {
    return (
      <AnalyzingScreen
        candidateCount={items.length}
        done={analysisDone}
        onFinish={handleAnalysisFinish}
      />
    );
  }

  const canStart = items.length >= UX_MIN_PHOTOS;

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--color-paper)",
        color: "var(--color-ink)",
        fontFamily: "var(--font-sans)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <TopBar backTarget="/" />

      {/* 헤드라인 — 마케터 정합 (Noto Serif 24-26 700 + period accent) */}
      <section style={{ padding: "44px 24px 32px", maxWidth: 480, margin: "0 auto", width: "100%" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 24,
            fontWeight: 700,
            lineHeight: 1.42,
            letterSpacing: "-0.022em",
            margin: 0,
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          올린 사진 중에<br />
          한 장 골라드려요
          <span style={{ color: "var(--color-danger)" }}>.</span>
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 10,
            fontSize: 14,
            color: "var(--color-mute)",
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
          }}
        >
          3장 이상 올려주시면 시각이 가장 잘 맞는 한 장을 골라드려요.
        </p>
      </section>

      {/* 사진 섹션 */}
      <section style={{ padding: "0 24px 24px", maxWidth: 480, margin: "0 auto", width: "100%" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <Label>PHOTO</Label>
          <LabelRight>{items.length} / {MAX_PHOTOS}</LabelRight>
        </div>

        {items.length === 0 ? (
          <DropzoneEmpty onAdd={openPicker} />
        ) : (
          <DropzoneGrid items={items} onAdd={openPicker} onRemove={removeAt} />
        )}

        {error && (
          <p
            className="font-sans"
            style={{
              marginTop: 16,
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
            role="alert"
          >
            {error}
          </p>
        )}
      </section>

      <div style={{ flex: 1 }} />

      {/* CTA — 마케터 pill (radius 100) */}
      <div style={{ padding: "20px 24px 24px", maxWidth: 480, margin: "0 auto", width: "100%" }}>
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
            color: canStart ? "var(--color-paper)" : "#fff",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor: canStart ? "pointer" : "not-allowed",
            transition: "all 0.2s ease",
          }}
        >
          {canStart ? "분석 시작하기 →" : "3장 이상 올려주세요"}
        </button>
      </div>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />

      {/* hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: "none" }}
        onChange={(e) => {
          handleFilesSelected(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Dropzone (empty) — 16:10 aspect + thin plus
// ─────────────────────────────────────────────

function DropzoneEmpty({ onAdd }: { onAdd: () => void }) {
  return (
    <button
      type="button"
      onClick={onAdd}
      aria-label="사진 올리기"
      style={{
        width: "100%",
        aspectRatio: "16/10",
        background: "rgba(0, 0, 0, 0.04)",
        border: "1.5px dashed var(--color-line-strong)",
        borderRadius: 12,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        fontFamily: "var(--font-sans)",
        color: "var(--color-mute)",
        marginTop: 10,
        padding: 0,
        gap: 10,
        transition: "border-color 0.2s ease, background 0.2s ease",
      }}
    >
      <span
        style={{
          fontSize: 22,
          color: "var(--color-mute-2)",
          lineHeight: 1,
        }}
      >
        +
      </span>
      <span
        style={{
          fontSize: 13,
          color: "var(--color-mute)",
          letterSpacing: "-0.005em",
        }}
      >
        사진 올리기
      </span>
    </button>
  );
}

// ─────────────────────────────────────────────
//  Dropzone (filled) — 3-col grid, no index stamps
// ─────────────────────────────────────────────

function DropzoneGrid({
  items,
  onAdd,
  onRemove,
}: {
  items: UploadItem[];
  onAdd: () => void;
  onRemove: (i: number) => void;
}) {
  const canAdd = items.length < MAX_PHOTOS;
  return (
    <div
      style={{
        marginTop: 10,
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 8,
      }}
    >
      {items.map((it, i) => (
        <div key={it.previewUrl} style={{ position: "relative" }}>
          <div
            style={{
              width: "100%",
              aspectRatio: "1/1",
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.06)",
              borderRadius: 12,
              border: "1.5px solid var(--color-line-strong)",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={it.previewUrl}
              alt={`upload ${i + 1}`}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                display: "block",
                borderRadius: 10,
              }}
            />
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove(i);
            }}
            aria-label="삭제"
            style={{
              position: "absolute",
              top: 7,
              right: 7,
              width: 22,
              height: 22,
              borderRadius: "50%",
              border: "none",
              background: "rgba(45, 45, 45, 0.65)",
              color: "#fff",
              fontSize: 12,
              cursor: "pointer",
              padding: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ✕
          </button>
        </div>
      ))}
      {canAdd && (
        <button
          type="button"
          onClick={onAdd}
          aria-label="사진 추가"
          style={{
            aspectRatio: "1/1",
            border: "1.5px dashed var(--color-line-strong)",
            background: "rgba(0, 0, 0, 0.04)",
            borderRadius: 12,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 0,
            transition: "border-color 0.2s ease, background 0.2s ease",
          }}
        >
          <span
            style={{
              fontSize: 22,
              color: "var(--color-mute-2)",
              lineHeight: 1,
            }}
          >
            +
          </span>
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Shared small bits
// ─────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="uppercase"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        letterSpacing: "0.12em",
        color: "var(--color-mute)",
      }}
    >
      {children}
    </span>
  );
}

function LabelRight({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="tabular-nums"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--color-mute-2)",
        letterSpacing: "0.04em",
      }}
    >
      {children}
    </span>
  );
}
