// SIGAK Step 0 essentials (SPEC-ONBOARDING-V2 REQ-ONBD-001/002)
//
// welcome (약관) → 여기 (gender + 생년월일 + ig handle optional) → /sia/new
// Sia 대화 진입 전 구조화 필드 확보. users + user_profiles 에 저장.
//
// 가드:
//   - JWT 없음        → /auth/login
//   - consent 미완료  → /onboarding/welcome
//   - 이미 essentials 완료 + onboarding 완료 → /
//   - 이미 essentials 완료 + Sia 미완료      → /sia/new
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getToken, logout } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe, saveEssentials } from "@/lib/api/onboarding";
import type { Gender } from "@/lib/types/mvp";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

const CURRENT_YEAR = new Date().getFullYear();
const MIN_YEAR = CURRENT_YEAR - 80;    // 80세까지
const MAX_YEAR = CURRENT_YEAR - 14;    // 만 14세 이상 (consent 와 정합)

export default function OnboardingEssentialsPage() {
  const router = useRouter();
  const [booting, setBooting] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [gender, setGender] = useState<Gender | null>(null);
  const [birthYear, setBirthYear] = useState<string>("");
  const [birthMonth, setBirthMonth] = useState<string>("");
  const [birthDay, setBirthDay] = useState<string>("");
  const [igHandle, setIgHandle] = useState<string>("");

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
        if (me.essentials_completed) {
          // 이미 Step 0 완료 — 다음 단계로
          router.replace(me.onboarding_completed ? "/" : "/sia");
          return;
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

  const { birthDateIso, dateValid } = useMemo(() => {
    const y = Number(birthYear);
    const m = Number(birthMonth);
    const d = Number(birthDay);
    if (!y || !m || !d) return { birthDateIso: null, dateValid: false };
    if (y < MIN_YEAR || y > MAX_YEAR) return { birthDateIso: null, dateValid: false };
    if (m < 1 || m > 12) return { birthDateIso: null, dateValid: false };
    if (d < 1 || d > 31) return { birthDateIso: null, dateValid: false };
    const dt = new Date(y, m - 1, d);
    if (
      dt.getFullYear() !== y ||
      dt.getMonth() !== m - 1 ||
      dt.getDate() !== d
    ) {
      return { birthDateIso: null, dateValid: false };
    }
    if (dt > new Date()) return { birthDateIso: null, dateValid: false };
    const pad = (n: number) => n.toString().padStart(2, "0");
    return {
      birthDateIso: `${y}-${pad(m)}-${pad(d)}`,
      dateValid: true,
    };
  }, [birthYear, birthMonth, birthDay]);

  const normalizedIgHandle = useMemo(() => {
    const trimmed = igHandle.trim();
    if (!trimmed) return null;
    return trimmed.startsWith("@") ? trimmed.slice(1) : trimmed;
  }, [igHandle]);

  const igHandleValid = useMemo(() => {
    if (!normalizedIgHandle) return true; // 선택 필드
    return /^[A-Za-z0-9._]{1,30}$/.test(normalizedIgHandle);
  }, [normalizedIgHandle]);

  const canSubmit = gender !== null && dateValid && igHandleValid && !submitting;

  const handleSubmit = useCallback(async () => {
    if (!canSubmit || !gender || !birthDateIso) return;
    setSubmitting(true);
    setError(null);
    try {
      await saveEssentials({
        gender,
        birth_date: birthDateIso,
        ig_handle: normalizedIgHandle ?? null,
      });
      router.replace("/sia");
    } catch (e) {
      setSubmitting(false);
      if (e instanceof ApiError) {
        if (e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        setError(e.message);
        return;
      }
      setError("저장에 실패했어요. 다시 시도해주세요.");
    }
  }, [canSubmit, gender, birthDateIso, normalizedIgHandle, router]);

  if (booting) {
    return <div style={{ minHeight: "100vh", background: "var(--color-paper)" }} aria-hidden />;
  }

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
      <TopBar
        onBack={() => {
          if (
            typeof window !== "undefined" &&
            !window.confirm("뒤로 가면 로그아웃돼요. 진행할까요?")
          ) {
            return;
          }
          logout();
        }}
      />

      <main style={{ padding: "48px 28px 24px", flex: 1 }}>
        {/* 헤드라인 */}
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
          기본 정보를.
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
          진단 전에 세 가지만 받아요.
        </p>

        {/* 성별 */}
        <section style={{ marginTop: 40 }}>
          <Label>성별</Label>
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            {(
              [
                { id: "female" as Gender, label: "여성" },
                { id: "male" as Gender, label: "남성" },
              ]
            ).map((g) => {
              const active = gender === g.id;
              return (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setGender(g.id)}
                  className="font-sans"
                  style={{
                    flex: 1,
                    height: 50,
                    fontSize: 14,
                    fontWeight: 600,
                    letterSpacing: "0.3px",
                    background: active ? "var(--color-ink)" : "transparent",
                    color: active ? "var(--color-paper)" : "var(--color-ink)",
                    border: active
                      ? "1px solid var(--color-ink)"
                      : "1px solid rgba(0, 0, 0, 0.15)",
                    borderRadius: 0,
                    cursor: "pointer",
                    transition: "opacity 180ms ease-out",
                  }}
                >
                  {g.label}
                </button>
              );
            })}
          </div>
        </section>

        {/* 생년월일 */}
        <section style={{ marginTop: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <Label>생년월일</Label>
            <LabelHint>만 14세 이상</LabelHint>
          </div>
          <div
            style={{
              marginTop: 12,
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr",
              gap: 8,
            }}
          >
            <DateField
              value={birthYear}
              onChange={setBirthYear}
              placeholder="YYYY"
              maxLength={4}
              ariaLabel="출생 연도"
            />
            <DateField
              value={birthMonth}
              onChange={setBirthMonth}
              placeholder="MM"
              maxLength={2}
              ariaLabel="출생 월"
            />
            <DateField
              value={birthDay}
              onChange={setBirthDay}
              placeholder="DD"
              maxLength={2}
              ariaLabel="출생 일"
            />
          </div>
          {!dateValid && (birthYear || birthMonth || birthDay) && (
            <p
              className="font-sans"
              style={{
                marginTop: 8,
                fontSize: 11,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
              }}
            >
              올바른 생년월일을 입력해주세요
            </p>
          )}
        </section>

        {/* 인스타그램 핸들 */}
        <section style={{ marginTop: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <Label>인스타그램</Label>
            <LabelHint>선택</LabelHint>
          </div>
          <p
            className="font-sans"
            style={{
              margin: "4px 0 12px",
              fontSize: 12,
              lineHeight: 1.6,
              opacity: 0.5,
              letterSpacing: "-0.005em",
              color: "var(--color-ink)",
            }}
          >
            피드 이미지를 함께 보면 분석이 정확해져요. 공개 계정만 조회돼요.
          </p>
          <input
            type="text"
            value={igHandle}
            onChange={(e) => setIgHandle(e.target.value)}
            placeholder="@username"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            maxLength={50}
            className="font-sans"
            style={{
              width: "100%",
              height: 50,
              padding: "0 14px",
              fontSize: 14,
              letterSpacing: "-0.005em",
              background: "transparent",
              color: "var(--color-ink)",
              border: "1px solid rgba(0, 0, 0, 0.15)",
              borderRadius: 0,
              outline: "none",
            }}
          />
          {igHandle && !igHandleValid && (
            <p
              className="font-sans"
              style={{
                marginTop: 8,
                fontSize: 11,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
              }}
            >
              영문·숫자·.·_ 로 30자 이내여야 해요
            </p>
          )}
        </section>

        {error && (
          <p
            className="font-sans"
            role="alert"
            style={{
              marginTop: 24,
              fontSize: 12,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
            }}
          >
            {error}
          </p>
        )}
      </main>

      <div style={{ padding: "20px 28px 24px" }}>
        <PrimaryButton
          onClick={handleSubmit}
          disabled={!canSubmit}
          disabledLabel={submitting ? "저장 중..." : "항목을 채워주세요"}
        >
          다음
        </PrimaryButton>
      </div>

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Subcomponents
// ─────────────────────────────────────────────

interface DateFieldProps {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  maxLength: number;
  ariaLabel: string;
}

function DateField({ value, onChange, placeholder, maxLength, ariaLabel }: DateFieldProps) {
  return (
    <input
      type="text"
      inputMode="numeric"
      pattern="[0-9]*"
      value={value}
      onChange={(e) => {
        // 숫자만 허용
        const digits = e.target.value.replace(/\D/g, "").slice(0, maxLength);
        onChange(digits);
      }}
      placeholder={placeholder}
      maxLength={maxLength}
      aria-label={ariaLabel}
      className="font-sans tabular-nums"
      style={{
        height: 50,
        padding: "0 14px",
        fontSize: 14,
        letterSpacing: "-0.005em",
        background: "transparent",
        color: "var(--color-ink)",
        border: "1px solid rgba(0, 0, 0, 0.15)",
        borderRadius: 0,
        outline: "none",
        textAlign: "center",
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

function LabelHint({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="font-sans"
      style={{
        fontSize: 11,
        letterSpacing: "-0.005em",
        opacity: 0.4,
        color: "var(--color-ink)",
      }}
    >
      {children}
    </span>
  );
}
