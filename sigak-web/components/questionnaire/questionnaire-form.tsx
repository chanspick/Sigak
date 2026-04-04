"use client";

// 설문 진단 멀티스텝 폼 오케스트레이터
// 3페이지: 핵심 질문 -> 티어별 추가 질문 + 사진 -> 확인/제출

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  CORE_QUESTIONS,
  WEDDING_QUESTIONS,
  CREATOR_QUESTIONS,
} from "@/lib/constants/questions";
import { QuestionnaireStep } from "@/components/questionnaire/questionnaire-step";
import { ProgressBar } from "@/components/questionnaire/progress-bar";
import { PhotoUploader } from "@/components/questionnaire/photo-uploader";
import { Button } from "@/components/ui/button";

interface QuestionnaireFormProps {
  userId: string;
  tier: "basic" | "creator" | "wedding";
}

const TOTAL_STEPS = 3;
const STORAGE_PREFIX = "questionnaire-";
// 핵심 질문 6개 중 최소 4개 답변 필수
const MIN_CORE_ANSWERS = 4;

interface SavedState {
  step: number;
  answers: Record<string, string>;
  photos: string[];
}

/** 설문 진단 멀티스텝 폼 */
export function QuestionnaireForm({ userId, tier }: QuestionnaireFormProps) {
  const router = useRouter();
  const storageKey = STORAGE_PREFIX + userId;

  const [step, setStep] = useState(1);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [photos, setPhotos] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // 티어별 추가 질문
  const tierQuestions = useMemo(() => {
    if (tier === "wedding") return WEDDING_QUESTIONS;
    if (tier === "creator") return CREATOR_QUESTIONS;
    return [];
  }, [tier]);

  // localStorage에서 복원 (마운트 시 1회)
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const saved: SavedState = JSON.parse(raw);
        if (saved.step) setStep(saved.step);
        if (saved.answers) setAnswers(saved.answers);
        // 사진은 object URL이므로 복원 불가 -- 건너뜀
      }
    } catch {
      // 파싱 실패 시 무시
    }
  }, [storageKey]);

  // 상태 변경 시 localStorage 자동 저장
  useEffect(() => {
    if (typeof window === "undefined") return;
    const data: SavedState = { step, answers, photos: [] };
    localStorage.setItem(storageKey, JSON.stringify(data));
  }, [step, answers, storageKey]);

  // 답변 변경 핸들러
  const handleAnswerChange = useCallback((key: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }, []);

  // 핵심 질문 답변 수
  const coreAnswerCount = useMemo(() => {
    return CORE_QUESTIONS.filter(
      (q) => answers[q.key] && answers[q.key].trim().length > 0,
    ).length;
  }, [answers]);

  // 페이지 1 유효성: 핵심 질문 4/6 이상 답변
  const isPage1Valid = coreAnswerCount >= MIN_CORE_ANSWERS;

  // 페이지 2 유효성: 사진 1장 이상 (정면 필수)
  const isPage2Valid = photos.length >= 1;

  // 다음 버튼 클릭
  const handleNext = useCallback(() => {
    if (step < TOTAL_STEPS) {
      setStep((s) => s + 1);
    }
  }, [step]);

  // 이전 버튼 클릭
  const handlePrev = useCallback(() => {
    if (step > 1) {
      setStep((s) => s - 1);
    }
  }, [step]);

  // 제출 처리
  const handleSubmit = useCallback(() => {
    setSubmitting(true);
    // localStorage 정리
    if (typeof window !== "undefined") {
      localStorage.removeItem(storageKey);
    }
    // 완료 페이지로 이동
    router.push("/questionnaire/complete?user_id=" + userId);
  }, [router, userId, storageKey]);

  // 다음 버튼 비활성화 조건
  const isNextDisabled = (step === 1 && !isPage1Valid) || (step === 2 && !isPage2Valid);

  return (
    <div className="max-w-[560px] mx-auto px-[var(--spacing-page-x-mobile)] md:px-0 py-10">
      {/* 진행 표시기 */}
      <ProgressBar current={step} total={TOTAL_STEPS} />

      {/* 페이지 1: 핵심 질문 */}
      {step === 1 && (
        <div>
          <h2 className="font-[family-name:var(--font-serif)] text-lg font-normal mb-1">
            기본 질문
          </h2>
          <p className="text-[12px] opacity-40 mb-5">
            6개 중 최소 {MIN_CORE_ANSWERS}개 이상 답변해 주세요 (
            {coreAnswerCount}/{CORE_QUESTIONS.length} 완료)
          </p>
          <QuestionnaireStep
            questions={CORE_QUESTIONS}
            answers={answers}
            onChange={handleAnswerChange}
          />
        </div>
      )}

      {/* 페이지 2: 티어별 추가 질문 + 사진 업로드 */}
      {step === 2 && (
        <div>
          {tierQuestions.length > 0 && (
            <div className="mb-8">
              <h2 className="font-[family-name:var(--font-serif)] text-lg font-normal mb-1">
                추가 질문
              </h2>
              <p className="text-[12px] opacity-40 mb-5">
                {tier === "wedding" ? "웨딩" : "크리에이터"} 맞춤 질문입니다
              </p>
              <QuestionnaireStep
                questions={tierQuestions}
                answers={answers}
                onChange={handleAnswerChange}
              />
            </div>
          )}
          <PhotoUploader photos={photos} onChange={setPhotos} />
        </div>
      )}

      {/* 페이지 3: 확인 + 제출 */}
      {step === 3 && (
        <div>
          <h2 className="font-[family-name:var(--font-serif)] text-lg font-normal mb-1">
            제출 확인
          </h2>
          <p className="text-[12px] opacity-40 mb-5">
            입력 내용을 확인하고 제출해 주세요
          </p>
          {/* 답변 요약 */}
          <div className="border border-black/10 p-5 mb-6">
            <p className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-3">
              답변 요약
            </p>
            {[...CORE_QUESTIONS, ...tierQuestions]
              .filter((q) => answers[q.key]?.trim())
              .map((q) => (
                <div
                  key={q.key}
                  className="py-2.5 border-b border-black/[0.06] last:border-b-0"
                >
                  <p className="text-[11px] font-semibold opacity-50 mb-1">
                    {q.label}
                  </p>
                  <p className="text-sm">{answers[q.key]}</p>
                </div>
              ))}
          </div>
          {/* 사진 요약 */}
          <div className="border border-black/10 p-5 mb-6">
            <p className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-3">
              사진 ({photos.length}장)
            </p>
            <div className="grid grid-cols-3 gap-2">
              {photos.map((photo, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={i}
                  src={photo}
                  alt={"사진 " + (i + 1)}
                  className="w-full aspect-[3/4] object-cover border border-black/[0.06]"
                />
              ))}
            </div>
          </div>
          {/* 제출 버튼 */}
          <Button
            variant="primary"
            size="lg"
            className="w-full"
            disabled={submitting}
            onClick={handleSubmit}
          >
            {submitting ? "제출 중..." : "진단 요청하기"}
          </Button>
        </div>
      )}

      {/* 이전 / 다음 네비게이션 (페이지 3 제외) */}
      {step < TOTAL_STEPS && (
        <div className="flex justify-between mt-8">
          <Button
            variant="ghost"
            size="sm"
            disabled={step === 1}
            onClick={handlePrev}
          >
            이전
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={isNextDisabled}
            onClick={handleNext}
          >
            다음
          </Button>
        </div>
      )}
      {step === TOTAL_STEPS && step > 1 && (
        <div className="flex justify-start mt-4">
          <Button variant="ghost" size="sm" onClick={handlePrev}>
            이전
          </Button>
        </div>
      )}
    </div>
  );
}
