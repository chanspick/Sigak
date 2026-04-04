"use client";

import { useState, useCallback } from "react";
import type { QueueUser, InterviewQuestion } from "@/lib/types/dashboard";
import { TIER_MAP } from "@/lib/constants/mock-data";
import {
  CORE_QUESTIONS,
  WEDDING_QUESTIONS,
  CREATOR_QUESTIONS,
} from "@/lib/constants/questions";

interface EntryViewProps {
  user: QueueUser;
  onBack: () => void;
}

// 인터뷰 입력 뷰 — 질문 응답, 메모, 사진 업로드
export function EntryView({ user, onBack }: EntryViewProps) {
  // 폼 데이터: 각 질문의 key를 키로, 응답을 값으로 저장
  const [form, setForm] = useState<Record<string, string>>({});
  // 업로드할 사진 파일 목록
  const [photos, setPhotos] = useState<File[]>([]);
  // 저장/분석 진행 상태
  const [saving, setSaving] = useState(false);
  // 저장 완료 여부 (저장 후 분석 버튼으로 전환)
  const [saved, setSaved] = useState(false);

  // 폼 필드 업데이트
  const setField = useCallback((key: string, val: string) => {
    setForm((f) => ({ ...f, [key]: val }));
  }, []);

  // 티어별 추가 질문 결정
  const tierQuestions: InterviewQuestion[] =
    user.tier === "wedding"
      ? WEDDING_QUESTIONS
      : user.tier === "creator"
        ? CREATOR_QUESTIONS
        : [];

  // 전체 질문 목록 (코어 + 티어별)
  const allQuestions = [...CORE_QUESTIONS, ...tierQuestions];

  // 채워진 질문 수 계산
  const filledCount = allQuestions.filter(
    (q) => form[q.key]?.trim()
  ).length;

  // 진행률 퍼센트
  const progress = Math.round((filledCount / allQuestions.length) * 100);

  // 인터뷰 데이터 저장
  const handleSave = async () => {
    setSaving(true);
    // TODO: POST /api/v1/interview/{user.id} — 백엔드 연동 시 교체
    // TODO: POST /api/v1/photos/{user.id} — 사진 업로드
    await new Promise((r) => setTimeout(r, 1200));
    setSaving(false);
    setSaved(true);
  };

  // 분석 파이프라인 실행
  const handleAnalyze = async () => {
    setSaving(true);
    // TODO: POST /api/v1/analyze/{user.id} — 백엔드 연동 시 교체
    await new Promise((r) => setTimeout(r, 2000));
    setSaving(false);
    alert("분석 완료 — 리포트 생성됨");
  };

  return (
    <div>
      {/* ← 대기열 돌아가기 버튼 */}
      <button
        type="button"
        className="bg-transparent border-none text-[13px] font-medium cursor-pointer opacity-50 p-0 mb-6 hover:opacity-80 transition-opacity"
        onClick={onBack}
      >
        ← 대기열
      </button>

      {/* 상단 헤더: 유저 정보 + 진행률 */}
      <div className="flex justify-between items-end">
        <div>
          <h2 className="font-[family-name:var(--font-serif)] text-[clamp(22px,3vw,30px)] font-normal leading-[1.3]">
            {user.name}
          </h2>
          <p className="text-[13px] opacity-40 mt-1.5">
            {TIER_MAP[user.tier]} · {user.booking_date.replace("2026-", "")}{" "}
            {user.booking_time}
          </p>
        </div>

        {/* 진행률 표시 */}
        <div className="text-right">
          <span className="text-[11px] font-semibold opacity-40 tracking-[1px]">
            {progress}%
          </span>
          {/* 진행률 바 */}
          <div
            className="w-[120px] h-1 bg-black/[0.06] rounded-sm mt-1.5 overflow-hidden"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="인터뷰 진행률"
          >
            <div
              className="h-full bg-[var(--color-fg)] rounded-sm transition-[width] duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* 구분선 */}
      <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />

      {/* 인터뷰 질문 섹션 */}
      <div className="py-1">
        <p className="text-[10px] font-bold tracking-[2.5px] opacity-30 mb-4 uppercase">
          인터뷰 응답
        </p>
        {allQuestions.map((q) => (
          <div key={q.key} className="mb-5">
            <label className="block text-xs font-semibold tracking-[0.5px] opacity-60 mb-2">
              {q.label}
            </label>
            <textarea
              className="w-full px-3.5 py-3 text-sm leading-relaxed bg-transparent border border-black/10 outline-none resize-y transition-colors duration-200 focus:border-[var(--color-fg)] rounded-none"
              rows={q.rows}
              placeholder={q.placeholder}
              value={form[q.key] || ""}
              onChange={(e) => setField(q.key, e.target.value)}
            />
          </div>
        ))}
      </div>

      {/* 구분선 */}
      <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />

      {/* 알바 메모 섹션 */}
      <div className="py-1">
        <p className="text-[10px] font-bold tracking-[2.5px] opacity-30 mb-4 uppercase">
          알바 메모
        </p>
        <textarea
          className="w-full px-3.5 py-3 text-sm leading-relaxed bg-transparent border border-black/10 outline-none resize-y transition-colors duration-200 focus:border-[var(--color-fg)] rounded-none"
          rows={4}
          placeholder="인터뷰 중 특이사항, 분위기, 추가 관찰 사항"
          value={form.raw_notes || ""}
          onChange={(e) => setField("raw_notes", e.target.value)}
        />
      </div>

      {/* 구분선 */}
      <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />

      {/* 사진 업로드 섹션 */}
      <div className="py-1">
        <p className="text-[10px] font-bold tracking-[2.5px] opacity-30 mb-4 uppercase">
          사진 업로드
        </p>
        <p className="text-[11px] opacity-30 mb-2">
          정면 1장 + 45도 측면 2장 권장
        </p>
        <input
          type="file"
          accept="image/*"
          multiple
          onChange={(e) => {
            if (e.target.files) {
              setPhotos([...e.target.files]);
            }
          }}
          className="text-[13px] mt-1"
        />
        {photos.length > 0 && (
          <p className="text-[11px] opacity-30 mt-2">
            {photos.length}장 선택됨
          </p>
        )}
      </div>

      {/* 구분선 */}
      <div className="h-px bg-[var(--color-fg)] opacity-[0.08] my-6" />

      {/* 액션 버튼 */}
      <div className="py-4">
        {!saved ? (
          <button
            type="button"
            className="w-full p-4 text-sm font-bold bg-[var(--color-fg)] text-[var(--color-bg)] border-none cursor-pointer transition-opacity duration-200 tracking-[0.5px] hover:opacity-80 disabled:opacity-30 disabled:cursor-not-allowed"
            onClick={handleSave}
            disabled={saving || filledCount === 0}
          >
            {saving ? "저장 중..." : "인터뷰 데이터 저장"}
          </button>
        ) : (
          <button
            type="button"
            className="w-full p-4 text-sm font-bold bg-[var(--color-fg)] text-[var(--color-bg)] border-none cursor-pointer transition-opacity duration-200 tracking-[0.5px] hover:opacity-80 disabled:opacity-30 disabled:cursor-not-allowed"
            onClick={handleAnalyze}
            disabled={saving}
          >
            {saving ? "분석 중..." : "→ 분석 파이프라인 실행"}
          </button>
        )}
      </div>
    </div>
  );
}
