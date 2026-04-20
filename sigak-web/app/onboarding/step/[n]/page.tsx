// SIGAK MVP v1.2 — /onboarding/step/[n]
//
// 동적 라우트 하나로 step 1~4 모두 처리. 각 step 정의는
// lib/constants/onboarding-steps.ts 의 ONBOARDING_STEPS.
//
// 진입 시 GET /api/v1/onboarding/state 로 기존 응답 불러와 pre-fill.
// "다음" CTA 클릭 → POST /api/v1/onboarding/save-step → 다음 step 또는 /complete.
//
// 권한 게이트: JWT 없음 → /auth/login. consent 미완료 → /onboarding/welcome.
// 최종 가드 로직은 D-5의 useOnboardingGuard가 담당하지만 여기서도 기본 방어.
"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import {
  getMe,
  getOnboardingState,
  saveOnboardingStep,
} from "@/lib/api/onboarding";
import {
  ONBOARDING_STEPS,
  getStep,
  type OnboardingStep,
  type Question,
} from "@/lib/constants/onboarding-steps";
import type { OnboardingData, StepNumber } from "@/lib/types/mvp";
import {
  PillGroup,
  PillGroupMulti,
  PrimaryButton,
  ProgressBar,
  TopBar,
} from "@/components/ui/sigak";

// ─────────────────────────────────────────────
//  Helpers — comma-join 처리 (backend가 string 받음)
// ─────────────────────────────────────────────

function splitCsv(v: unknown): string[] {
  if (!v) return [];
  if (Array.isArray(v)) return v.filter((x) => typeof x === "string");
  if (typeof v === "string") return v ? v.split(",") : [];
  return [];
}

function joinCsv(arr: string[]): string {
  return arr.join(",");
}

// ─────────────────────────────────────────────
//  Validation — required 필드 모두 값 있음?
// ─────────────────────────────────────────────

function validateStep(step: OnboardingStep, values: OnboardingData): boolean {
  for (const q of step.questions) {
    if (!q.required) continue;
    const raw = values[q.key];
    if (q.type === "multi_select") {
      const list = splitCsv(raw);
      if (list.length === 0) return false;
      if (q.maxSelect != null && list.length > q.maxSelect) return false;
    } else if (q.type === "text") {
      const s = typeof raw === "string" ? raw.trim() : "";
      if (!s) return false;
      if (q.minLength != null && s.length < q.minLength) return false;
    } else {
      if (!raw || typeof raw !== "string") return false;
    }
  }
  return true;
}

// ─────────────────────────────────────────────
//  Page
// ─────────────────────────────────────────────

export default function OnboardingStepPage() {
  const router = useRouter();
  const params = useParams<{ n: string }>();
  const rawN = Number(params.n);
  const step = getStep(rawN);
  const stepN = (step?.step ?? 1) as StepNumber;

  const [values, setValues] = useState<OnboardingData>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);

  // 1. 권한 게이트 + 기존 데이터 pre-fill
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/auth/login");
      return;
    }
    (async () => {
      try {
        const me = await getMe();
        if (!me.consent_completed) {
          router.replace("/onboarding/welcome");
          return;
        }
        if (me.onboarding_completed) {
          router.replace("/onboarding/complete");
          return;
        }
        const state = await getOnboardingState();
        if (state.onboarding_data) {
          setValues(state.onboarding_data);
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        // 네트워크 실패 시 빈 값으로 진행
      }
      setBooting(false);
    })();
  }, [router]);

  // 2. route param이 범위 밖이면 step 1로 보냄
  useEffect(() => {
    if (!step) {
      router.replace("/onboarding/step/1");
    }
  }, [step, router]);

  const canProceed = useMemo(
    () => (step ? validateStep(step, values) : false),
    [step, values],
  );

  function handleFieldChange(key: string, value: string) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleNext() {
    if (!step || !canProceed || submitting) return;
    setSubmitting(true);
    setError(null);

    // 현재 step에서 변경된 필드만 추려서 전송
    const fieldsForStep: OnboardingData = {};
    for (const q of step.questions) {
      const v = values[q.key];
      if (v !== undefined && v !== null && v !== "") {
        fieldsForStep[q.key] = v;
      }
    }

    try {
      await saveOnboardingStep(stepN, fieldsForStep);
      if (stepN === 4) {
        router.push("/onboarding/complete");
      } else {
        router.push(`/onboarding/step/${stepN + 1}`);
      }
    } catch (e) {
      setSubmitting(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setError(
        e instanceof Error ? e.message : "저장에 실패했습니다. 다시 시도해주세요.",
      );
    }
  }

  if (booting || !step) {
    return <div className="min-h-screen bg-paper" aria-hidden />;
  }

  const progressPct = Math.round(((stepN - 1) / ONBOARDING_STEPS.length) * 100);

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      <TopBar
        variant="onboarding"
        stepLabel={`STEP 0${stepN} / 04`}
        hideTokens
      />

      {/* Progress */}
      <div className="mt-6 px-5">
        <ProgressBar
          pct={progressPct}
          label={`STEP ${stepN}`}
          hideValue
        />
      </div>

      {/* 제목 */}
      <div className="mt-8 px-5">
        <h1
          className="font-sans font-medium text-ink"
          style={{ fontSize: 24, lineHeight: 1.3, letterSpacing: "-0.02em" }}
        >
          {step.title}
        </h1>
        {step.subtitle && (
          <p
            className="mt-2 font-sans text-mute"
            style={{ fontSize: 13, lineHeight: 1.6, letterSpacing: "-0.005em" }}
          >
            {step.subtitle}
          </p>
        )}
      </div>

      {/* 질문들 */}
      <main
        key={stepN /* step 변경 시 slide-in 애니 */}
        className="flex-1 animate-slide-right px-5 pb-32 pt-8"
      >
        <div className="space-y-10">
          {step.questions.map((q) => (
            <FieldBlock
              key={q.key}
              q={q}
              value={values[q.key]}
              onChange={(v) => handleFieldChange(q.key, v)}
            />
          ))}
        </div>

        {error && (
          <p
            className="mt-6 font-sans"
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
      </main>

      {/* 하단 CTA — fixed bottom */}
      <div
        className="sticky bottom-0 border-t bg-paper px-5 pb-8 pt-4"
        style={{ borderColor: "var(--color-line)" }}
      >
        <PrimaryButton
          onClick={handleNext}
          disabled={!canProceed || submitting}
          disabledLabel={submitting ? "저장 중..." : "답변을 완성해주세요"}
        >
          {stepN === 4 ? "완료" : "다음"}
        </PrimaryButton>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  FieldBlock — 질문 타입별 렌더러
// ─────────────────────────────────────────────

interface FieldBlockProps {
  q: Question;
  value: unknown;
  onChange: (v: string) => void;
}

function FieldBlock({ q, value, onChange }: FieldBlockProps) {
  return (
    <section>
      <h2
        className="mb-1 font-sans font-medium text-ink"
        style={{ fontSize: 15, letterSpacing: "-0.005em" }}
      >
        {q.label}
      </h2>
      {q.description && (
        <p
          className="mb-3 font-sans text-mute"
          style={{ fontSize: 12, lineHeight: 1.6, letterSpacing: "-0.005em" }}
        >
          {q.description}
        </p>
      )}

      {q.type === "single_select" && q.options && (
        <PillGroup
          name={q.key}
          options={q.options.map((o) => ({ value: o.value, label: o.label }))}
          value={typeof value === "string" ? value : null}
          onChange={onChange}
          className="mt-2"
        />
      )}

      {q.type === "multi_select" && q.options && (
        <PillGroupMulti
          name={q.key}
          options={q.options.map((o) => ({ value: o.value, label: o.label }))}
          value={splitCsv(value)}
          onChange={(arr) => onChange(joinCsv(arr))}
          max={q.maxSelect}
          className="mt-2"
        />
      )}

      {q.type === "text" && (
        <TextArea
          value={typeof value === "string" ? value : ""}
          onChange={onChange}
          placeholder={q.placeholder}
          rows={q.rows ?? 3}
          maxLength={q.maxLength}
          minLength={q.minLength}
        />
      )}
    </section>
  );
}

interface TextAreaProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows: number;
  minLength?: number;
  maxLength?: number;
}

function TextArea({ value, onChange, placeholder, rows, maxLength, minLength }: TextAreaProps) {
  const count = value.length;
  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        maxLength={maxLength}
        className="w-full resize-none font-sans text-ink"
        style={{
          marginTop: 8,
          padding: "12px 14px",
          fontSize: 14,
          lineHeight: 1.6,
          letterSpacing: "-0.005em",
          border: "0.5px solid var(--color-line-strong)",
          borderRadius: 8,
          background: "transparent",
          color: "var(--color-ink)",
          outline: "none",
        }}
      />
      {(minLength != null || maxLength != null) && (
        <div
          className="mt-1 flex justify-end font-mono text-mute tabular-nums"
          style={{ fontSize: 10, letterSpacing: "0.04em" }}
        >
          {minLength != null && count < minLength
            ? `${count} / 최소 ${minLength}`
            : maxLength != null
              ? `${count} / ${maxLength}`
              : null}
        </div>
      )}
    </div>
  );
}
