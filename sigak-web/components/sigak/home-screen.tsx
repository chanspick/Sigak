// SIGAK MVP v1.2 — HomeScreen (upload zone)
//
// refactor/home-screen.jsx v1.1 포팅. 상태머신:
//   idle     → 빈 SageFrame dropzone + 중앙 + icon
//   filled   → 2×5 grid + "N / 10" + "어울리는 사진 고르기" CTA
//   analyzing → AnalyzingScreen inline 렌더 (동일 컴포넌트 교체)
//
// UX 규칙(백엔드 제약과 별개):
//   - 1-2장: 힌트 "3장부터 시작할 수 있어요"
//   - 3-10장: CTA 활성
//   - createVerdict 호출 + 최소 4.4초 분석 애니 보장 → /verdict/{id}
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { SageFrame, TopBar, PrimaryButton } from "@/components/ui/sigak";
import { createVerdict, MAX_PHOTOS, UX_MIN_PHOTOS } from "@/lib/api/verdicts";
import { ApiError } from "@/lib/api/fetch";
import { useTokenBalance } from "@/hooks/use-token-balance";
import { AnalyzingScreen } from "./analyzing-screen";

const ANALYSIS_MIN_MS = 4400;

interface UploadItem {
  file: File;
  previewUrl: string;
}

interface HomeScreenProps {
  /** 헤더에 표시할 토큰 수 override. 지정하지 않으면 내부 hook으로 조회. */
  tokensOverride?: number | null;
}

export function HomeScreen({ tokensOverride }: HomeScreenProps = {}) {
  const router = useRouter();
  const { balance } = useTokenBalance();
  const tokens = tokensOverride ?? balance ?? 0;

  const [items, setItems] = useState<UploadItem[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // previewUrl cleanup — 언마운트 시 해제
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
    setError(null);

    const startedAt = Date.now();
    try {
      const response = await createVerdict(items.map((it) => it.file));
      // verdict 응답의 gold_reading은 create 시점만 반환 — sessionStorage로 전달
      try {
        sessionStorage.setItem(
          `sigak_gold_reading:${response.verdict_id}`,
          response.gold_reading ?? "",
        );
      } catch {
        // private mode 등 — 무시
      }
      // 최소 애니메이션 시간 보장
      const elapsed = Date.now() - startedAt;
      if (elapsed < ANALYSIS_MIN_MS) {
        await new Promise((r) => setTimeout(r, ANALYSIS_MIN_MS - elapsed));
      }
      router.push(`/verdict/${response.verdict_id}`);
    } catch (e) {
      setAnalyzing(false);
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

  // ─── Analyzing 상태 — 동일 마운트에서 컴포넌트 교체 ───
  if (analyzing) {
    return (
      <AnalyzingScreen
        tokens={tokens}
        candidateCount={items.length}
      />
    );
  }

  const canStart = items.length >= UX_MIN_PHOTOS;

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <TopBar variant="home" tokens={tokens} />

      {/* Main block */}
      <div className="px-5 pt-7">
        {items.length === 0 ? (
          <DropzoneEmpty onAdd={openPicker} />
        ) : (
          <DropzoneGrid items={items} onAdd={openPicker} onRemove={removeAt} />
        )}
        <Hint count={items.length} />
        {error && (
          <p
            className="mt-3 font-sans"
            style={{
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
            role="alert"
          >
            {error}
          </p>
        )}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* CTA */}
      <div className="px-5 pb-8 pt-5">
        <PrimaryButton
          onClick={handleStart}
          disabled={!canStart}
          disabledLabel={
            items.length === 0
              ? "사진을 올려주세요"
              : `사진을 ${UX_MIN_PHOTOS}장 이상 올려주세요`
          }
        >
          어울리는 사진 고르기
        </PrimaryButton>
      </div>

      {/* hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => {
          handleFilesSelected(e.target.files);
          // reset input so same-file reselection works
          e.target.value = "";
        }}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Dropzone (empty)
// ─────────────────────────────────────────────

function DropzoneEmpty({ onAdd }: { onAdd: () => void }) {
  return (
    <button
      type="button"
      onClick={onAdd}
      className="block w-full cursor-pointer bg-transparent p-0 text-left"
      aria-label="사진 올리기"
    >
      <SageFrame inset={10} tick={16} weight={1}>
        <div
          className="flex flex-col items-center justify-center"
          style={{ aspectRatio: "1/1", background: "transparent" }}
        >
          {/* plus glyph */}
          <span className="relative block" style={{ width: 28, height: 28 }}>
            <span
              style={{
                position: "absolute",
                left: 2,
                top: 13.5,
                width: 24,
                height: 1,
                background: "var(--color-ink)",
              }}
            />
            <span
              style={{
                position: "absolute",
                left: 13.5,
                top: 2,
                width: 1,
                height: 24,
                background: "var(--color-ink)",
              }}
            />
          </span>
          <span style={{ height: 14 }} />
          <span
            className="font-sans font-medium text-ink"
            style={{ fontSize: 16, letterSpacing: "-0.005em", lineHeight: 1 }}
          >
            사진 올리기
          </span>
          <span style={{ height: 10 }} />
          <span
            className="font-sans text-mute"
            style={{ fontSize: 11, letterSpacing: "0.01em", lineHeight: 1 }}
          >
            {UX_MIN_PHOTOS} ~ {MAX_PHOTOS}장
          </span>
        </div>
      </SageFrame>
    </button>
  );
}

// ─────────────────────────────────────────────
//  Dropzone (filled grid)
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
    <SageFrame inset={10} tick={16} weight={1}>
      <div className="flex flex-col" style={{ gap: 10 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: 6,
          }}
        >
          {items.map((it, i) => (
            <div key={`${it.previewUrl}`} style={{ position: "relative" }}>
              <div
                style={{
                  width: "100%",
                  aspectRatio: "1/1",
                  overflow: "hidden",
                  background: "var(--color-sage-soft)",
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
              {/* index stamp bottom-left */}
              <span
                className="font-mono tabular-nums"
                style={{
                  position: "absolute",
                  left: 3,
                  bottom: 3,
                  fontSize: 9,
                  color: "var(--color-mute)",
                  background: "rgba(250,250,247,0.85)",
                  padding: "1px 4px",
                  lineHeight: 1.2,
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              {/* × remove */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(i);
                }}
                aria-label="삭제"
                style={{
                  position: "absolute",
                  top: 3,
                  right: 3,
                  width: 18,
                  height: 18,
                  borderRadius: 999,
                  background: "var(--color-ink)",
                  border: "none",
                  cursor: "pointer",
                  padding: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg width="8" height="8" viewBox="0 0 8 8">
                  <path
                    d="M1 1l6 6M7 1L1 7"
                    stroke="var(--color-paper)"
                    strokeWidth="1"
                    strokeLinecap="square"
                  />
                </svg>
              </button>
            </div>
          ))}
          {canAdd && (
            <button
              type="button"
              onClick={onAdd}
              aria-label="사진 추가"
              style={{
                cursor: "pointer",
                aspectRatio: "1/1",
                border: "0.5px dashed var(--color-sage)",
                background: "var(--color-sage-soft)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span className="relative block" style={{ width: 14, height: 14 }}>
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 6.75,
                    width: 14,
                    height: 0.5,
                    background: "var(--color-sage)",
                  }}
                />
                <span
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 6.75,
                    width: 0.5,
                    height: 14,
                    background: "var(--color-sage)",
                  }}
                />
              </span>
            </button>
          )}
        </div>

        {/* N / 10 */}
        <div
          className="flex justify-end font-sans tabular-nums text-mute"
          style={{ fontSize: 11, letterSpacing: "-0.005em" }}
        >
          {items.length} / {MAX_PHOTOS}
        </div>
      </div>
    </SageFrame>
  );
}

function Hint({ count }: { count: number }) {
  if (count === 0 || count >= UX_MIN_PHOTOS) return null;
  return (
    <p
      className="mt-4 font-sans text-mute"
      style={{ fontSize: 12, letterSpacing: "-0.005em" }}
    >
      {UX_MIN_PHOTOS}장부터 시작할 수 있어요
    </p>
  );
}
