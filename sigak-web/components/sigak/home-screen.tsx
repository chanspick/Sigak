// SIGAK MVP v1.2 (Rebrand) — HomeScreen / Upload
//
// 3-col grid (Instagram 느낌), 인덱스 스탬프 제거, serif 헤드라인.
// 업로드 상태머신 + createVerdict 호출은 그대로 유지 (기능 동산).
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import { createVerdict, MAX_PHOTOS, UX_MIN_PHOTOS } from "@/lib/api/verdicts";
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
      const response = await createVerdict(items.map((it) => it.file));
      try {
        sessionStorage.setItem(
          `sigak_gold_reading:${response.verdict_id}`,
          response.gold_reading ?? "",
        );
      } catch {
        // ignore
      }
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
      <TopBar />

      {/* Serif 헤드라인 */}
      <section style={{ padding: "48px 28px 40px" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 34,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          당신을 읽겠습니다.
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 16,
            fontSize: 13,
            opacity: 0.5,
            lineHeight: 1.6,
            color: "var(--color-ink)",
          }}
        >
          사진 세 장부터.
        </p>
      </section>

      <Rule />

      {/* 사진 섹션 */}
      <section style={{ padding: "28px 28px 24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <Label>사진</Label>
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

      {/* CTA */}
      <div style={{ padding: "20px 28px 32px" }}>
        <PrimaryButton
          onClick={handleStart}
          disabled={!canStart}
          disabledLabel="세 장부터"
        >
          읽기 시작
        </PrimaryButton>
      </div>

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
        background: "transparent",
        border: "1px solid rgba(0, 0, 0, 0.15)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        fontFamily: "var(--font-sans)",
        color: "var(--color-ink)",
        marginTop: 12,
        padding: 0,
      }}
    >
      <div style={{ position: "relative", width: 20, height: 20, marginBottom: 12 }}>
        <div
          style={{
            position: "absolute",
            top: 9.5,
            left: 0,
            width: 20,
            height: 1,
            background: "var(--color-ink)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 9.5,
            top: 0,
            width: 1,
            height: 20,
            background: "var(--color-ink)",
          }}
        />
      </div>
      <span style={{ fontSize: 14, fontWeight: 500 }}>사진 올리기</span>
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
        marginTop: 12,
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 6,
      }}
    >
      {items.map((it, i) => (
        <div key={it.previewUrl} style={{ position: "relative" }}>
          <div
            style={{
              width: "100%",
              aspectRatio: "1/1",
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.04)",
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
              top: 6,
              right: 6,
              width: 20,
              height: 20,
              border: "none",
              background: "var(--color-ink)",
              color: "var(--color-paper)",
              fontSize: 10,
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
            border: "1px solid rgba(0, 0, 0, 0.15)",
            background: "transparent",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 0,
          }}
        >
          <div style={{ position: "relative", width: 14, height: 14 }}>
            <div
              style={{
                position: "absolute",
                top: 6.5,
                left: 0,
                width: 14,
                height: 1,
                background: "var(--color-ink)",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 6.5,
                top: 0,
                width: 1,
                height: 14,
                background: "var(--color-ink)",
              }}
            />
          </div>
        </button>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Shared small bits
// ─────────────────────────────────────────────

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
