// SIGAK MVP v1.2 (Rebrand) — /onboarding/step/[n]
//
// 4스텝 질문지. 기능(save-step 호출, 필수 필드 검증)은 유지.
// 브랜딩: TopBar + serif 헤드라인 + pill/textarea(검정 테두리, sage 제거).
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
//  Helpers
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
      }
      setBooting(false);
    })();
  }, [router]);

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
    return <div style={{ minHeight: "100vh", background: "var(--color-paper)" }} aria-hidden />;
  }

  const progressPct = Math.round(((stepN - 1) / ONBOARDING_STEPS.length) * 100);

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

      {/* Step label + progress */}
      <section style={{ padding: "28px 28px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <Label>Step {stepN} / 4</Label>
          <LabelRight>{String(Math.round((stepN / 4) * 100)).padStart(3, " ")}%</LabelRight>
        </div>
        <div style={{ marginTop: 12 }}>
          <ProgressBar pct={progressPct} label="진행" hideValue />
        </div>
      </section>

      {/* 제목 */}
      <section style={{ padding: "36px 28px 0" }}>
        <h1
          className="font-serif"
          style={{
            fontSize: 28,
            fontWeight: 400,
            lineHeight: 1.3,
            letterSpacing: "-0.01em",
            margin: 0,
            color: "var(--color-ink)",
          }}
        >
          {step.title}
        </h1>
        {step.subtitle && (
          <p
            className="font-sans"
            style={{
              marginTop: 12,
              fontSize: 13,
              opacity: 0.5,
              lineHeight: 1.6,
              color: "var(--color-ink)",
            }}
          >
            {step.subtitle}
          </p>
        )}
      </section>

      {/* 질문 */}
      <main
        key={stepN}
        className="animate-slide-right"
        style={{ padding: "32px 28px 140px", flex: 1 }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 36 }}>
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
            className="font-sans"
            role="alert"
            style={{
              marginTop: 20,
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
          >
            {error}
          </p>
        )}
      </main>

      {/* CTA */}
      <div
        style={{
          position: "sticky",
          bottom: 0,
          background: "var(--color-paper)",
          borderTop: "1px solid rgba(0, 0, 0, 0.1)",
          padding: "20px 28px 32px",
        }}
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
//  FieldBlock
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
        className="font-sans"
        style={{
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "-0.005em",
          margin: 0,
          marginBottom: 4,
          color: "var(--color-ink)",
        }}
      >
        {q.label}
      </h2>
      {q.description && (
        <p
          className="font-sans"
          style={{
            margin: 0,
            marginBottom: 12,
            fontSize: 12,
            lineHeight: 1.6,
            opacity: 0.5,
            letterSpacing: "-0.005em",
            color: "var(--color-ink)",
          }}
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
          className="mt-1"
        />
      )}

      {q.type === "multi_select" && q.options && (
        <PillGroupMulti
          name={q.key}
          options={q.options.map((o) => ({ value: o.value, label: o.label }))}
          value={splitCsv(value)}
          onChange={(arr) => onChange(joinCsv(arr))}
          max={q.maxSelect}
          className="mt-1"
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
        className="font-sans"
        style={{
          marginTop: 4,
          width: "100%",
          padding: "12px 14px",
          fontSize: 14,
          lineHeight: 1.6,
          letterSpacing: "-0.005em",
          border: "1px solid rgba(0, 0, 0, 0.15)",
          borderRadius: 0,
          background: "transparent",
          color: "var(--color-ink)",
          outline: "none",
          resize: "none",
        }}
      />
      {(minLength != null || maxLength != null) && (
        <div
          className="font-sans tabular-nums"
          style={{
            marginTop: 4,
            display: "flex",
            justifyContent: "flex-end",
            fontSize: 10,
            letterSpacing: "1.5px",
            opacity: 0.4,
            color: "var(--color-ink)",
          }}
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

// ─────────────────────────────────────────────
//  Labels
// ─────────────────────────────────────────────

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
