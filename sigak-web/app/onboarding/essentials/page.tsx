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
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

const CURRENT_YEAR = new Date().getFullYear();
// 마케터 정합 (redesign/온보딩_1815.html): 16~50세 + "50세 이상" 단일 dropdown.
// backend 는 birth_date ISO 받으므로 frontend 에서 (현재년도 - age, 1월 1일) 변환.
const MIN_AGE = 16;
const MAX_AGE_EXACT = 50;  // 51 이상은 "50세 이상" 으로

export default function OnboardingEssentialsPage() {
  const router = useRouter();
  const [booting, setBooting] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [gender, setGender] = useState<Gender | null>(null);
  const [age, setAge] = useState<string>("");  // "16" ~ "50" 또는 "50+"
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

  // age (e.g. "20" 또는 "50+") → birth_date ISO 변환
  // 마케터 단순 dropdown 호환 위해 day/month 정확치 X — 1월 1일로 approx.
  // backend birth_date ISO 형식만 만족하면 됨 (정확한 생일 X, 만 N세 추정용).
  const { birthDateIso, dateValid } = useMemo(() => {
    if (!age) return { birthDateIso: null, dateValid: false };
    const numericAge = age === "50+" ? 51 : Number(age);
    if (!Number.isFinite(numericAge) || numericAge < MIN_AGE) {
      return { birthDateIso: null, dateValid: false };
    }
    const birthYear = CURRENT_YEAR - numericAge;
    return {
      birthDateIso: `${birthYear}-01-01`,
      dateValid: true,
    };
  }, [age]);

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
      const resp = await saveEssentials({
        gender,
        birth_date: birthDateIso,
        ig_handle: normalizedIgHandle ?? null,
      });
      // ig_handle 있으면 분석 대기 페이지로 — 폴링 후 자동 /sia 이동.
      // 없으면 Vision 없는 Sia 폴백 경로 (페르소나 B placeholder) — 바로 /sia.
      if (resp.ig_fetch_status === "pending") {
        router.replace("/onboarding/ig-loading");
      } else {
        router.replace("/sia");
      }
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

      <main style={{ padding: "48px 24px 24px", flex: 1, maxWidth: 480, margin: "0 auto", width: "100%" }}>
        {/* 헤드라인 — 마케터 카피 차용 */}
        <h1
          className="font-serif"
          style={{
            fontSize: 24,
            fontWeight: 700,
            lineHeight: 1.42,
            letterSpacing: "-0.022em",
            margin: 0,
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          인스타 피드를 읽어올게요!
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 10,
            fontSize: 14,
            color: "var(--color-mute)",
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
          }}
        >
          나이와 성별을 알려주시면 더 정확히 분석할 수 있어요.
        </p>

        {/* 인스타그램 핸들 (선택) */}
        <section style={{ marginTop: 40 }}>
          <Label>INSTAGRAM HANDLE</Label>
          <div
            style={{
              marginTop: 8,
              display: "flex",
              alignItems: "center",
              border: "1px solid var(--color-line-strong)",
              borderRadius: 12,
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.04)",
              transition: "border-color 0.2s ease",
            }}
          >
            <span
              className="font-sans"
              style={{
                padding: "14px 10px 14px 14px",
                fontSize: 15,
                color: "var(--color-mute-2)",
                userSelect: "none",
                flexShrink: 0,
              }}
            >
              @
            </span>
            <input
              type="text"
              value={igHandle}
              onChange={(e) => setIgHandle(e.target.value)}
              placeholder="instagram ID"
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              maxLength={50}
              className="font-sans"
              style={{
                flex: 1,
                padding: "14px 14px 14px 0",
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 15,
                color: "var(--color-ink)",
              }}
            />
          </div>
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

        {/* 성별 */}
        <section style={{ marginTop: 22 }}>
          <Label>GENDER</Label>
          <div style={{ marginTop: 8, display: "flex", gap: 10 }}>
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
                    padding: "13px 0",
                    fontSize: 14,
                    fontWeight: 500,
                    letterSpacing: "-0.008em",
                    background: active ? "var(--color-ink)" : "rgba(0, 0, 0, 0.04)",
                    color: active ? "var(--color-paper)" : "var(--color-mute)",
                    border: active
                      ? "1.5px solid var(--color-ink)"
                      : "1.5px solid var(--color-line-strong)",
                    borderRadius: 12,
                    cursor: "pointer",
                    transition: "all 0.18s ease",
                    textAlign: "center",
                  }}
                >
                  {g.label}
                </button>
              );
            })}
          </div>
        </section>

        {/* 나이 — 마케터 정합 (redesign/온보딩_1815.html): 단일 dropdown 16~50세+ */}
        <section style={{ marginTop: 22 }}>
          <Label>AGE</Label>
          <div
            style={{
              position: "relative",
              marginTop: 8,
              border: "1px solid var(--color-line-strong)",
              borderRadius: 12,
              overflow: "hidden",
              background: "rgba(0, 0, 0, 0.04)",
              transition: "border-color 0.2s ease",
            }}
          >
            <select
              value={age}
              onChange={(e) => setAge(e.target.value)}
              aria-label="나이"
              className="font-sans"
              style={{
                width: "100%",
                padding: "14px 44px 14px 16px",
                background: "transparent",
                border: "none",
                outline: "none",
                fontSize: 15,
                color: age ? "var(--color-ink)" : "var(--color-mute-2)",
                appearance: "none",
                WebkitAppearance: "none",
                cursor: "pointer",
              }}
            >
              <option value="" disabled>
                나이를 선택해 주세요
              </option>
              {Array.from({ length: MAX_AGE_EXACT - MIN_AGE + 1 }, (_, i) => MIN_AGE + i).map(
                (a) => (
                  <option key={a} value={String(a)}>
                    {a}세
                  </option>
                ),
              )}
              <option value="50+">50세 이상</option>
            </select>
            {/* chevron — 마케터 css ::after 정합 (10x10 border-bottom + border-right rotate 45) */}
            <span
              aria-hidden
              style={{
                position: "absolute",
                right: 18,
                top: "50%",
                width: 8,
                height: 8,
                borderRight: "1.5px solid var(--color-mute)",
                borderBottom: "1.5px solid var(--color-mute)",
                transform: "translateY(-65%) rotate(45deg)",
                pointerEvents: "none",
              }}
            />
          </div>
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

        {/* CTA — 마케터 pill (radius 100) */}
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            width: "100%",
            padding: "17px 24px",
            background: canSubmit ? "var(--color-ink)" : "var(--color-line-strong)",
            color: canSubmit ? "var(--color-paper)" : "#fff",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor: canSubmit ? "pointer" : "not-allowed",
            transition: "all 0.2s ease",
            marginTop: 40,
          }}
        >
          {submitting ? "저장 중..." : !canSubmit ? "항목을 채워주세요" : "다음 →"}
        </button>
      </main>

      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Subcomponents
// ─────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="uppercase"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10,
        letterSpacing: "0.12em",
        color: "var(--color-mute)",
      }}
    >
      {children}
    </span>
  );
}
