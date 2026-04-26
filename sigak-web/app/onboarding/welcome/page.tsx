// SIGAK MVP v1.2 (Rebrand) — /onboarding/welcome
//
// 로그인 후 첫 게이트. v2.0 약관 필수 5 + 선택 1 동의 수집 → POST /auth/consent.
// 기능은 그대로, 브랜딩만 새 체계 (TopBar 검정바, serif 헤드라인, Rule 구분선).
"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getToken, logout } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe, saveConsent } from "@/lib/api/onboarding";
import { ONBOARDING_STEPS } from "@/lib/constants/onboarding-steps";
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

type ConsentKey =
  | "age_confirmed"
  | "terms"
  | "privacy"
  | "sensitive"
  | "overseas_transfer"
  | "marketing";

interface ConsentItem {
  key: ConsentKey;
  required: boolean;
  label: string;
  termsAnchor?: string;
}

const CONSENT_ITEMS: ConsentItem[] = [
  { key: "age_confirmed",     required: true, label: "만 14세 이상입니다" },
  { key: "terms",             required: true, label: "서비스 이용약관 동의", termsAnchor: "#tos" },
  { key: "privacy",           required: true, label: "개인정보 수집·이용 동의", termsAnchor: "#privacy" },
  { key: "sensitive",         required: true, label: "민감정보 수집·이용 동의", termsAnchor: "#privacy" },
  { key: "overseas_transfer", required: true, label: "개인정보 국외 이전 동의", termsAnchor: "#privacy" },
  { key: "marketing",         required: false, label: "마케팅 정보 수신 동의" },
];

const REQUIRED_KEYS: ConsentKey[] = CONSENT_ITEMS
  .filter((it) => it.required)
  .map((it) => it.key);

type ConsentState = Record<ConsentKey, boolean>;

const INITIAL_STATE: ConsentState = {
  age_confirmed: false,
  terms: false,
  privacy: false,
  sensitive: false,
  overseas_transfer: false,
  marketing: false,
};

export default function OnboardingWelcomePage() {
  const router = useRouter();
  const [consents, setConsents] = useState<ConsentState>(INITIAL_STATE);
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
        if (me.consent_completed) {
          // 이미 동의 완료 — 다음 게이트 단계로
          if (!me.essentials_completed) {
            router.replace("/onboarding/essentials");
          } else if (!me.onboarding_completed) {
            router.replace("/sia");
          } else {
            router.replace("/");
          }
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

  const allRequiredChecked = useMemo(
    () => REQUIRED_KEYS.every((k) => consents[k]),
    [consents],
  );

  const allChecked = useMemo(
    () => CONSENT_ITEMS.every((it) => consents[it.key]),
    [consents],
  );

  function toggle(key: ConsentKey) {
    setConsents((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function toggleAll() {
    const next = !allChecked;
    const updated: ConsentState = { ...consents };
    for (const it of CONSENT_ITEMS) {
      updated[it.key] = next;
    }
    setConsents(updated);
  }

  async function handleSubmit() {
    if (!allRequiredChecked || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await saveConsent({
        terms: consents.terms,
        privacy: consents.privacy,
        sensitive: consents.sensitive,
        overseas_transfer: consents.overseas_transfer,
        age_confirmed: consents.age_confirmed,
        marketing: consents.marketing,
      });
      router.replace("/onboarding/essentials");
    } catch (e) {
      setSubmitting(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      setError(
        e instanceof Error ? e.message : "동의 저장에 실패했습니다. 다시 시도해주세요.",
      );
    }
  }

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
          // 뒤로 가기 = 로그아웃. 이 화면에서 consent 미완이라 / 로 돌려보내도
          // 가드가 welcome으로 튕김 → 순환 방지 차원에서 logout().
          if (
            typeof window !== "undefined" &&
            !window.confirm("뒤로 가면 로그아웃됩니다. 진행할까요?")
          ) {
            return;
          }
          logout();
        }}
      />

      <main style={{ padding: "48px 24px 24px", flex: 1, maxWidth: 480, margin: "0 auto", width: "100%" }}>
        {/* 헤드라인 — 마케터 정합 (24-26px 700 + period accent) */}
        <h1
          className="font-serif"
          style={{
            fontSize: 28,
            fontWeight: 700,
            lineHeight: 1.35,
            letterSpacing: "-0.025em",
            margin: 0,
            color: "var(--color-ink)",
            wordBreak: "keep-all",
          }}
        >
          시작 전에
          <span style={{ color: "var(--color-danger)" }}>.</span>
        </h1>
        <p
          className="font-sans"
          style={{
            marginTop: 12,
            fontSize: 14,
            color: "var(--color-mute)",
            lineHeight: 1.65,
            letterSpacing: "-0.005em",
          }}
        >
          네 걸음으로 기준을 설정합니다.
        </p>

        {/* 4스텝 프리뷰 */}
        <div style={{ marginTop: 40 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
            <Label>네 걸음</Label>
            <LabelRight>04</LabelRight>
          </div>
          <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {ONBOARDING_STEPS.map((s, i) => (
              <li
                key={s.step}
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: 14,
                  padding: "12px 0",
                  borderBottom: i === ONBOARDING_STEPS.length - 1 ? "none" : "1px solid rgba(0, 0, 0, 0.1)",
                }}
              >
                <span
                  className="font-serif tabular-nums"
                  style={{
                    fontSize: 14,
                    fontWeight: 400,
                    opacity: 0.4,
                    color: "var(--color-ink)",
                  }}
                >
                  {String(s.step).padStart(2, "0")}
                </span>
                <span
                  className="font-sans"
                  style={{
                    fontSize: 14,
                    fontWeight: 400,
                    letterSpacing: "-0.005em",
                    color: "var(--color-ink)",
                  }}
                >
                  {s.shortLabel}
                </span>
              </li>
            ))}
          </ol>
        </div>

        {/* 동의 섹션 */}
        <div style={{ marginTop: 48 }}>
          <Label>동의</Label>

          {/* 전체 동의 */}
          <div style={{ marginTop: 16, paddingBottom: 14, borderBottom: "1px solid rgba(0, 0, 0, 0.15)" }}>
            <ConsentRow
              checked={allChecked}
              onToggle={toggleAll}
              label="전체 동의 (선택 포함)"
              strong
            />
          </div>

          {/* 개별 */}
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {CONSENT_ITEMS.map((item) => (
              <li
                key={item.key}
                style={{ padding: "14px 0", borderBottom: "1px solid rgba(0, 0, 0, 0.1)" }}
              >
                <ConsentRow
                  checked={consents[item.key]}
                  onToggle={() => toggle(item.key)}
                  label={`[${item.required ? "필수" : "선택"}] ${item.label}`}
                  termsAnchor={item.termsAnchor}
                />
              </li>
            ))}
          </ul>
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

      <div style={{ padding: "20px 24px 24px", maxWidth: 480, margin: "0 auto", width: "100%" }}>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!allRequiredChecked || submitting}
          className="font-sans"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            width: "100%",
            padding: "17px 24px",
            background: !allRequiredChecked || submitting
              ? "var(--color-line-strong)"
              : "var(--color-ink)",
            color: !allRequiredChecked || submitting ? "#fff" : "var(--color-paper)",
            border: "none",
            borderRadius: 100,
            fontSize: 15,
            fontWeight: 600,
            letterSpacing: "-0.012em",
            cursor: !allRequiredChecked || submitting ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {submitting
            ? "저장 중..."
            : !allRequiredChecked
              ? "필수 항목에 모두 동의해주세요"
              : "시작하기 →"}
        </button>
      </div>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  ConsentRow
// ─────────────────────────────────────────────

interface ConsentRowProps {
  checked: boolean;
  onToggle: () => void;
  label: string;
  strong?: boolean;
  termsAnchor?: string;
}

function ConsentRow({ checked, onToggle, label, strong = false, termsAnchor }: ConsentRowProps) {
  // [필수] / [선택] 접두어 분리해서 ember 색 적용
  const requiredMatch = label.match(/^\[필수\]\s*(.+)$/);
  const optionalMatch = label.match(/^\[선택\]\s*(.+)$/);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        onClick={onToggle}
        style={{
          width: 18,
          height: 18,
          flexShrink: 0,
          border: checked ? "1.5px solid var(--color-ink)" : "1.5px solid var(--color-line-strong)",
          background: checked ? "var(--color-ink)" : "transparent",
          borderRadius: 4,
          cursor: "pointer",
          padding: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transition: "border-color 0.2s ease, background 0.2s ease",
        }}
      >
        {checked && (
          <svg width="10" height="8" viewBox="0 0 10 8" aria-hidden>
            <path
              d="M1 4L3.5 6.5L9 1"
              stroke="var(--color-paper)"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
        )}
      </button>

      <label
        onClick={onToggle}
        className="font-sans"
        style={{
          fontSize: strong ? 14 : 13.5,
          fontWeight: strong ? 600 : 400,
          letterSpacing: "-0.008em",
          lineHeight: 1.5,
          cursor: "pointer",
          flex: 1,
          color: "var(--color-ink)",
          opacity: strong ? 1 : 0.85,
          wordBreak: "keep-all",
        }}
      >
        {requiredMatch ? (
          <>
            <span style={{ color: "var(--color-danger)", fontWeight: 500, marginRight: 2 }}>
              [필수]
            </span>{" "}
            {requiredMatch[1]}
          </>
        ) : optionalMatch ? (
          <>
            <span style={{ color: "var(--color-mute)", marginRight: 2 }}>[선택]</span>{" "}
            {optionalMatch[1]}
          </>
        ) : (
          label
        )}
      </label>

      {termsAnchor && (
        <Link
          href={`/terms${termsAnchor}`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 10,
            letterSpacing: "0.06em",
            color: "var(--color-mute)",
            textDecoration: "underline",
            textUnderlineOffset: 2,
            flexShrink: 0,
          }}
        >
          전문
        </Link>
      )}
    </div>
  );
}

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

function LabelRight({ children }: { children: React.ReactNode }) {
  return (
    <span
      className="tabular-nums"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 11,
        color: "var(--color-mute-2)",
        letterSpacing: "0.04em",
      }}
    >
      {children}
    </span>
  );
}
