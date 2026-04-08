// Before/After 오버레이 비교 슬라이더
// 디자인 레퍼런스: overlayui.jsx
// 구조: 이미지 위 clipPath 슬라이더 + 아래 range input + 액션 태그

"use client";

import { useState, useRef, useCallback, useEffect } from "react";

interface OverlayCompareProps {
  beforeUrl: string;
  afterUrl: string;
  actionTags?: { label: string; priority: string }[];
  locked?: boolean;
}

export function OverlayCompare({
  beforeUrl,
  afterUrl,
  actionTags = [],
  locked = false,
}: OverlayCompareProps) {
  const [sliderPos, setSliderPos] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const updatePosition = useCallback((clientX: number) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPos(pct);
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      updatePosition(e.clientX);
    },
    [updatePosition]
  );

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      setIsDragging(true);
      updatePosition(e.touches[0].clientX);
    },
    [updatePosition]
  );

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => updatePosition(e.clientX);
    const onTouchMove = (e: TouchEvent) => {
      e.preventDefault();
      updatePosition(e.touches[0].clientX);
    };
    const onUp = () => setIsDragging(false);

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onUp);
    };
  }, [isDragging, updatePosition]);

  const showingBefore = sliderPos > 80;
  const showingAfter = sliderPos < 20;
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "";

  return (
    <div className="w-full max-w-[480px] mx-auto">
      {/* 이미지 컨테이너 */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        className="relative w-full overflow-hidden rounded-sm select-none"
        style={{
          aspectRatio: "4 / 5",
          cursor: isDragging ? "grabbing" : "ew-resize",
          boxShadow: "0 2px 20px rgba(0,0,0,0.08)",
        }}
      >
        {/* AFTER 레이어 (바닥) */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(${apiBase}${afterUrl})`,
            filter: locked ? "blur(20px)" : "none",
          }}
        />

        {/* BEFORE 레이어 (clipPath로 좌측만) */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: `url(${apiBase}${beforeUrl})`,
            clipPath: `inset(0 ${100 - sliderPos}% 0 0)`,
            transition: isDragging ? "none" : "clip-path 0.1s ease-out",
            filter: locked ? "blur(20px)" : "none",
          }}
        />

        {/* 디바이더 라인 */}
        <div
          className="absolute top-0 bottom-0 z-10"
          style={{
            left: `${sliderPos}%`,
            width: 2,
            background: "rgba(255,255,255,0.9)",
            transform: "translateX(-50%)",
            transition: isDragging ? "none" : "left 0.1s ease-out",
          }}
        >
          {/* 핸들 */}
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-9 h-9 rounded-full flex items-center justify-center gap-[3px]"
            style={{
              background: "rgba(255,255,255,0.95)",
              boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
              backdropFilter: "blur(4px)",
            }}
          >
            <div className="w-0 h-0 border-y-[5px] border-y-transparent border-r-[5px] border-r-[#888]" />
            <div className="w-0 h-0 border-y-[5px] border-y-transparent border-l-[5px] border-l-[#888]" />
          </div>
        </div>

        {/* Before/After 라벨 */}
        <span
          className="absolute bottom-4 left-4 font-[family-name:var(--font-serif)] text-[12px] tracking-[0.15em] uppercase text-white/85"
          style={{
            opacity: showingAfter ? 0 : 1,
            transition: "opacity 0.3s",
            textShadow: "0 1px 4px rgba(0,0,0,0.3)",
          }}
        >
          Before
        </span>
        <span
          className="absolute bottom-4 right-4 font-[family-name:var(--font-serif)] text-[12px] tracking-[0.15em] uppercase text-white/85"
          style={{
            opacity: showingBefore ? 0 : 1,
            transition: "opacity 0.3s",
            textShadow: "0 1px 4px rgba(0,0,0,0.3)",
          }}
        >
          After
        </span>

        {/* 잠금 오버레이 */}
        {locked && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/20 z-20">
            <span className="text-white/80 text-sm font-medium">
              Standard 이상에서 확인 가능
            </span>
          </div>
        )}
      </div>

      {/* 하단 슬라이더 */}
      <div className="flex items-center gap-3.5 px-1 pt-5 pb-2">
        <span className="font-[family-name:var(--font-serif)] text-[10px] tracking-[0.12em] text-[var(--color-muted)] uppercase min-w-[42px] text-right">
          After
        </span>
        <div className="flex-1 relative h-6 flex items-center">
          <div className="absolute left-0 right-0 h-px bg-[var(--color-border)]" />
          <div
            className="absolute left-0 h-px bg-[var(--color-fg)]"
            style={{
              width: `${sliderPos}%`,
              transition: isDragging ? "none" : "width 0.1s ease-out",
            }}
          />
          <input
            type="range"
            min={0}
            max={100}
            value={sliderPos}
            onChange={(e) => setSliderPos(Number(e.target.value))}
            className="absolute w-full h-6 opacity-0 cursor-ew-resize m-0"
          />
          <div
            className="absolute w-3 h-3 rounded-full bg-[var(--color-fg)] pointer-events-none"
            style={{
              left: `${sliderPos}%`,
              transform: "translateX(-50%)",
              boxShadow: "0 1px 4px rgba(0,0,0,0.12)",
              transition: isDragging ? "none" : "left 0.1s ease-out",
            }}
          />
        </div>
        <span className="font-[family-name:var(--font-serif)] text-[10px] tracking-[0.12em] text-[var(--color-muted)] uppercase min-w-[42px]">
          Before
        </span>
      </div>

      {/* 안내 */}
      <p className="text-center text-[11px] text-[var(--color-muted)] pt-2 pb-1 font-light tracking-[0.02em]">
        드래그하여 변화를 확인하세요
      </p>

      {/* 액션 태그 */}
      {actionTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 justify-center pt-4 pb-2">
          {actionTags.map((tag, i) => (
            <span
              key={i}
              className={`px-3 py-1 rounded-full text-[11px] font-normal tracking-[0.02em] ${
                tag.priority === "핵심 포인트" || tag.priority === "HIGH"
                  ? "bg-[var(--color-fg)] text-[var(--color-bg)]"
                  : "border border-[var(--color-border)] text-[var(--color-muted)]"
              }`}
            >
              {tag.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
