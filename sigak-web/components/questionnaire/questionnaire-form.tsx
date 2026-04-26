"use client";

// 설문 진단 멀티스텝 폼 오케스트레이터
// 스텝: 얼굴&체형 → 현재헤어 → 스타일&추구미 → (티어별) → 사진 → 확인/제출

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getSteps, type StepConfig } from "@/lib/constants/questions";
import { QuestionnaireStep } from "@/components/questionnaire/questionnaire-step";
import { ProgressBar } from "@/components/questionnaire/progress-bar";
import { PhotoUploader } from "@/components/questionnaire/photo-uploader";
import type { PhotoEntry } from "@/components/questionnaire/photo-uploader";
import { Button } from "@/components/ui/button";
import {
  submitAll,
  ApiError,
} from "@/lib/api/client";

interface QuestionnaireFormProps {
  userId: string;
  tier: "standard" | "full" | "basic" | "creator" | "wedding";
  gender: "female" | "male";
  userName?: string;
  userPhone?: string;
}

const STORAGE_PREFIX = "questionnaire-";

interface SavedState {
  step: number;
  answers: Record<string, string>;
}

function loadSavedState(storageKey: string): SavedState | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) return JSON.parse(raw);
  } catch {
    // 파싱 실패 시 무시
  }
  return null;
}

/** 스텝의 필수 질문이 충분히 답변되었는지 확인 */
function isStepValid(
  stepConfig: StepConfig,
  answers: Record<string, string>,
): boolean {
  const required = stepConfig.questions.filter((q) => q.required !== false);
  if (required.length === 0) return true;

  // 필수 질문의 60% 이상 답변 시 통과 (최소 1개)
  const threshold = Math.max(1, Math.ceil(required.length * 0.6));
  const answered = required.filter((q) => {
    const val = answers[q.key];
    return val && val.trim().length > 0;
  }).length;

  return answered >= threshold;
}

/** 설문 진단 멀티스텝 폼 */
export function QuestionnaireForm({
  userId,
  tier,
  gender,
  userName = "",
  userPhone = "",
}: QuestionnaireFormProps) {
  const router = useRouter();
  const storageKey = STORAGE_PREFIX + userId;

  // 스텝 목록: 질문 스텝들 + 사진 + 확인
  const questionSteps = useMemo(() => getSteps(tier), [tier]);
  const PHOTO_STEP = questionSteps.length + 1;
  const CONFIRM_STEP = questionSteps.length + 2;
  const TOTAL_STEPS = CONFIRM_STEP;

  const [step, setStep] = useState(() => loadSavedState(storageKey)?.step ?? 1);
  const [answers, setAnswers] = useState<Record<string, string>>(
    () => loadSavedState(storageKey)?.answers ?? {},
  );
  const [photos, setPhotos] = useState<string[]>([]);
  const [photoFiles, setPhotoFiles] = useState<PhotoEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // 상태 변경 시 localStorage 자동 저장
  useEffect(() => {
    if (typeof window === "undefined") return;
    const data: SavedState = { step, answers };
    localStorage.setItem(storageKey, JSON.stringify(data));
  }, [step, answers, storageKey]);

  const handleAnswerChange = useCallback((key: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [key]: value }));
  }, []);

  // 현재 스텝 유효성
  const isCurrentStepValid = useMemo(() => {
    if (step <= questionSteps.length) {
      return isStepValid(questionSteps[step - 1], answers);
    }
    if (step === PHOTO_STEP) {
      return photos.length >= 1;
    }
    return true;
  }, [step, questionSteps, answers, photos, PHOTO_STEP]);

  const handleNext = useCallback(() => {
    if (step < TOTAL_STEPS) setStep((s) => s + 1);
  }, [step, TOTAL_STEPS]);

  const handlePrev = useCallback(() => {
    if (step > 1) setStep((s) => s - 1);
  }, [step]);

  // 제출 처리 — /submit 호출 → 송금 안내 페이지로 이동
  const handleSubmit = useCallback(async () => {
    setSubmitting(true);
    setSubmitError(null);

    try {
      const files = photoFiles.map((entry) => entry.file);

      // 통합 제출: 사진 + 질문지 한 번에 (user_id 포함 → 카카오 유저 연결)
      const result = await submitAll(
        { ...answers, gender, tier, name: userName, phone: userPhone, user_id: userId },
        files,
      );

      // localStorage: 설문 데이터 정리 + user_id 저장 (알림 연동)
      if (typeof window !== "undefined") {
        localStorage.removeItem(storageKey);
        if (result.user_id) {
          localStorage.setItem("sigak_user_id", result.user_id);
        }
      }

      // 애널리틱스: 주문 생성
      import("@/lib/analytics").then(({ trackOrderCreated, identifyUser }) => {
        identifyUser(result.user_id);
        trackOrderCreated(result.order_id, tier, result.payment_info.amount);
      });

      // 송금 안내 페이지로 이동 (order_id 전달)
      const params = new URLSearchParams({
        order_id: result.order_id,
        amount: String(result.payment_info.amount),
        bank: result.payment_info.bank,
        account: result.payment_info.account,
        holder: result.payment_info.holder,
        toss: result.payment_info.toss_deeplink,
        kakao: result.payment_info.kakao_deeplink,
      });
      router.push("/questionnaire/payment?" + params.toString());
    } catch (err) {
      setSubmitting(false);
      if (err instanceof ApiError) {
        setSubmitError(err.message);
      } else {
        setSubmitError(
          "제출 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        );
      }
    }
  }, [router, gender, tier, storageKey, photoFiles, answers, userId, userName, userPhone]);

  // 현재 질문 스텝 정보
  const currentQuestionStep =
    step <= questionSteps.length ? questionSteps[step - 1] : null;

  // 답변 완료 수 (전체 질문 중)
  const allQuestions = questionSteps.flatMap((s) => s.questions);
  const totalAnswered = allQuestions.filter((q) => {
    const val = answers[q.key];
    return val && val.trim().length > 0;
  }).length;

  return (
    <div className="max-w-[560px] mx-auto px-[var(--spacing-page-x-mobile)] md:px-0 py-10">
      {/* 진행 표시기 */}
      <ProgressBar current={step} total={TOTAL_STEPS} />

      {/* 질문 스텝들 */}
      {currentQuestionStep && (
        <div>
          <h2 className="font-[family-name:var(--font-serif)] text-lg font-normal mb-0.5">
            {currentQuestionStep.title}
          </h2>
          <p className="text-[12px] opacity-40 mb-6">
            {currentQuestionStep.subtitle}
          </p>
          <QuestionnaireStep
            questions={currentQuestionStep.questions}
            answers={answers}
            onChange={handleAnswerChange}
          />
        </div>
      )}

      {/* 사진 업로드 스텝 */}
      {step === PHOTO_STEP && (
        <div>
          <h2 className="font-[family-name:var(--font-serif)] text-lg font-normal mb-0.5">
            사진
          </h2>
          <p className="text-[12px] opacity-40 mb-6">
            AI 분석을 위한 사진을 올려주세요
          </p>
          <PhotoUploader
            photos={photos}
            onChange={setPhotos}
            photoFiles={photoFiles}
            onFilesChange={setPhotoFiles}
          />
        </div>
      )}

      {/* 확인 & 제출 스텝 */}
      {step === CONFIRM_STEP && (
        <div>
          <h2 className="font-[family-name:var(--font-serif)] text-lg font-normal mb-0.5">
            제출 확인
          </h2>
          <p className="text-[12px] opacity-40 mb-6">
            입력 내용을 확인하고 제출해 주세요 ({totalAnswered}/
            {allQuestions.length} 답변)
          </p>

          {/* 스텝별 답변 요약 */}
          {questionSteps.map((stepConfig) => {
            const answered = stepConfig.questions.filter(
              (q) => answers[q.key]?.trim(),
            );
            if (answered.length === 0) return null;

            return (
              <div
                key={stepConfig.title}
                className="border border-black/10 p-5 mb-4"
              >
                <p className="text-[11px] font-semibold tracking-[1px] opacity-40 mb-3">
                  {stepConfig.title}
                </p>
                {answered.map((q) => (
                  <div
                    key={q.key}
                    className="py-2 border-b border-black/[0.06] last:border-b-0"
                  >
                    <p className="text-[11px] font-semibold opacity-50 mb-0.5">
                      {q.label}
                    </p>
                    <p className="text-sm">
                      {formatAnswer(q, answers[q.key])}
                    </p>
                  </div>
                ))}
              </div>
            );
          })}

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

          {/* 에러 메시지 */}
          {submitError && (
            <div className="mb-4 p-4 border border-[var(--color-line)] text-[13px] leading-relaxed">
              <p className="mb-2">{submitError}</p>
              <button
                type="button"
                className="text-[12px] underline opacity-60 hover:opacity-100"
                onClick={() => {
                  setSubmitError(null);
                  setStep(PHOTO_STEP);
                }}
              >
                사진을 다시 선택하기
              </button>
            </div>
          )}

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

      {/* 이전 / 다음 네비게이션 */}
      {step < CONFIRM_STEP && (
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
            disabled={!isCurrentStepValid}
            onClick={handleNext}
          >
            다음
          </Button>
        </div>
      )}
      {step === CONFIRM_STEP && (
        <div className="flex justify-start mt-4">
          <Button variant="ghost" size="sm" onClick={handlePrev}>
            이전
          </Button>
        </div>
      )}
    </div>
  );
}

/** 답변값을 사람이 읽을 수 있는 형태로 변환 */
function formatAnswer(
  q: { type?: string; options?: { value: string; label: string }[] },
  value: string,
): string {
  if (!value) return "";

  const type = q.type ?? "text";

  if (type === "yes_no") {
    return value === "yes" ? "네" : "아니오";
  }

  if ((type === "single_select" || type === "multi_select") && q.options) {
    const values = value.split(",").filter(Boolean);
    return values
      .map((v) => q.options!.find((o) => o.value === v)?.label ?? v)
      .join(", ");
  }

  return value;
}
