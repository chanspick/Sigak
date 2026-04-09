"use client";

// 사진 업로더 컴포넌트
// 정면 1장 필수 + 측면 최대 2장 선택

import { useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";

export interface PhotoEntry {
  url: string; // 미리보기용 object URL
  file: File; // 업로드용 원본 File 객체
}

interface PhotoUploaderProps {
  photos: string[];
  onChange: (photos: string[]) => void;
  /** File 객체 참조 목록 — API 업로드에 사용 */
  photoFiles?: PhotoEntry[];
  onFilesChange?: (entries: PhotoEntry[]) => void;
}

/** 사진 업로드 + 미리보기 + 재촬영 */
export function PhotoUploader({ photos, onChange, photoFiles, onFilesChange }: PhotoUploaderProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const replaceIndexRef = useRef<number | null>(null);

  const MAX_PHOTOS = 3;

  /** 파일 선택 처리 */
  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const url = URL.createObjectURL(file);

      if (replaceIndexRef.current !== null) {
        // 재촬영: 특정 인덱스 교체
        const idx = replaceIndexRef.current;
        const next = [...photos];
        // 이전 URL 해제
        if (next[idx]) {
          URL.revokeObjectURL(next[idx]);
        }
        next[idx] = url;
        onChange(next);

        // File 목록도 업데이트
        if (photoFiles && onFilesChange) {
          const nextFiles = [...photoFiles];
          nextFiles[idx] = { url, file };
          onFilesChange(nextFiles);
        }

        replaceIndexRef.current = null;
      } else {
        // 새 사진 추가
        onChange([...photos, url]);
        // File 목록도 추가
        if (onFilesChange) {
          onFilesChange([...(photoFiles || []), { url, file }]);
        }
      }

      // input 초기화 (동일 파일 재선택 허용)
      e.target.value = "";
    },
    [photos, onChange, photoFiles, onFilesChange],
  );

  /** 새 사진 추가 트리거 */
  const handleAdd = useCallback(() => {
    replaceIndexRef.current = null;
    fileRef.current?.click();
  }, []);

  /** 재촬영 트리거 */
  const handleReplace = useCallback((index: number) => {
    replaceIndexRef.current = index;
    fileRef.current?.click();
  }, []);

  /** 사진 삭제 */
  const handleRemove = useCallback(
    (index: number) => {
      URL.revokeObjectURL(photos[index]);
      onChange(photos.filter((_, i) => i !== index));
      // File 목록도 삭제
      if (photoFiles && onFilesChange) {
        onFilesChange(photoFiles.filter((_, i) => i !== index));
      }
    },
    [photos, onChange, photoFiles, onFilesChange],
  );

  // 슬롯 라벨
  const slotLabels = ["정면 (필수)", "측면 1 (선택)", "측면 2 (선택)"];

  return (
    <div className="flex flex-col gap-4">
      {/* 안내 텍스트 */}
      <div>
        <p className="text-[11px] font-semibold tracking-[0.5px] opacity-50 mb-1">
          얼굴 사진
        </p>
        <p className="text-[12px] opacity-40 leading-relaxed">
          정면을 바라보고, 밝은 곳에서 촬영해 주세요.
          선글라스·마스크·모자는 벗어주세요.
        </p>
      </div>

      {/* 사진 슬롯 그리드 */}
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: MAX_PHOTOS }, (_, i) => {
          const photo = photos[i];
          return (
            <div
              key={i}
              className="aspect-[3/4] border border-black/[0.12] flex flex-col items-center justify-center overflow-hidden relative"
            >
              {photo ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={photo}
                    alt={slotLabels[i]}
                    className="w-full h-full object-cover"
                  />
                  {/* 오버레이 버튼 */}
                  <div className="absolute bottom-0 left-0 right-0 flex gap-1 p-1 bg-black/40">
                    <button
                      type="button"
                      className="flex-1 text-[10px] text-white py-1 bg-transparent border-none cursor-pointer hover:underline"
                      onClick={() => handleReplace(i)}
                    >
                      재촬영
                    </button>
                    <button
                      type="button"
                      className="flex-1 text-[10px] text-white py-1 bg-transparent border-none cursor-pointer hover:underline"
                      onClick={() => handleRemove(i)}
                    >
                      삭제
                    </button>
                  </div>
                </>
              ) : (
                <span className="text-[10px] opacity-30 text-center px-2">
                  {slotLabels[i]}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* 사진 추가 버튼 */}
      {photos.length < MAX_PHOTOS && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={handleAdd}
        >
          사진 추가 ({photos.length}/{MAX_PHOTOS})
        </Button>
      )}

      {/* 정면 사진 필수 경고 */}
      {photos.length === 0 && (
        <p className="text-[11px] text-[var(--color-danger)]">
          정면 사진 필수
        </p>
      )}

      {/* 숨겨진 file input */}
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
