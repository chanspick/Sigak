// SIGAK MVP v1.2 — /onboarding/welcome
//
// 로그인 직후 첫 진입 게이트. 여기서 약관 v2.0 필수 5개 + 선택 1개 동의를 받고
// POST /api/v1/auth/consent 로 저장한다. 성공 시 /onboarding/step/1 이동.
//
// 이미 consent_completed=true 라면 즉시 step으로 보냄(useEffect).
"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { getMe, saveConsent } from "@/lib/api/onboarding";
import { ONBOARDING_STEPS } from "@/lib/constants/onboarding-steps";
import { PrimaryButton } from "@/components/ui/sigak";

// 체크박스 필드 정의 (필수 5 + 선택 1)
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
  termsAnchor?: string; // /terms#... 앵커. 없으면 "전문 보기" 숨김
}

const CONSENT_ITEMS: ConsentItem[] = [
  { key: "age_confirmed",     required: true, label: "만 14세 이상입니다" },
  { key: "terms",             required: true, label: "서비스 이용약관 동의", termsAnchor: "#tos" },
  { key: "privacy",           required: true, label: "개인정보 수집·이용 동의", termsAnchor: "#privacy" },
  { key: "sensitive",         required: true, label: "민감정보(얼굴·생체 특징) 수집·이용 동의", termsAnchor: "#privacy" },
  { key: "overseas_transfer", required: true, label: "개인정보 국외 이전 동의 (Railway·Vercel·Anthropic)", termsAnchor: "#privacy" },
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

  // 인증 + consent 상태 확인. 로그인 안 되어 있으면 /auth/login.
  // 이미 consent 완료면 step으로 바로 보냄.
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
          // 다음 온보딩 스텝 또는 완료 화면 → 가드가 최종 분기 (여기선 단순히 step/1)
          router.replace(me.onboarding_completed ? "/" : "/onboarding/step/1");
          return;
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        // 네트워크 오류: 계속 진행시키되 consent 제출 시 실패하면 알림
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
      router.replace("/onboarding/step/1");
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
    return (
      <div className="min-h-screen bg-paper" aria-hidden />
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-paper text-ink">
      {/* 상단 여백 */}
      <div className="pt-[56px]" />

      <main className="flex-1 px-6 pb-6">
        {/* 헤드라인 */}
        <h1
          className="font-sans font-medium text-ink"
          style={{
            fontSize: 28,
            lineHeight: 1.3,
            letterSpacing: "-0.02em",
          }}
        >
          SIGAK 시작하기
        </h1>
        <p
          className="mt-3 font-sans text-mute"
          style={{ fontSize: 13, lineHeight: 1.7, letterSpacing: "-0.005em" }}
        >
          4단계로 당신의 추구미를 파악합니다.
          <br />
          한 번만 설정하면 판정이 더 정확해집니다.
        </p>

        {/* 4스텝 프리뷰 */}
        <section className="mt-10">
          <div
            className="mb-3 font-display font-medium uppercase text-mute"
            style={{ fontSize: 10, letterSpacing: "0.22em" }}
          >
            § 4 STEPS
          </div>
          <ol className="space-y-2">
            {ONBOARDING_STEPS.map((s) => (
              <li
                key={s.step}
                className="flex items-center gap-3 border-b py-3"
                style={{ borderColor: "var(--color-line)" }}
              >
                <span
                  className="font-mono text-mute tabular-nums"
                  style={{ fontSize: 10, letterSpacing: "0.14em" }}
                >
                  /00{s.step}
                </span>
                <span className="font-sans text-ink" style={{ fontSize: 14, letterSpacing: "-0.01em" }}>
                  {s.shortLabel}
                </span>
                <span
                  className="ml-auto font-sans text-mute"
                  style={{ fontSize: 11, letterSpacing: "-0.005em" }}
                >
                  {s.title.replace(/^SIGAK /, "")}
                </span>
              </li>
            ))}
          </ol>
        </section>

        {/* 동의 체크박스 */}
        <section className="mt-10">
          <div
            className="mb-3 font-display font-medium uppercase text-mute"
            style={{ fontSize: 10, letterSpacing: "0.22em" }}
          >
            § CONSENT
          </div>

          {/* 전체 동의 토글 */}
          <div
            className="mb-2 border-b py-3"
            style={{ borderColor: "var(--color-line)" }}
          >
            <ConsentRow
              checked={allChecked}
              onToggle={toggleAll}
              strong
              label="전체 동의 (선택 포함)"
            />
          </div>

          {/* 개별 체크박스 */}
          <ul className="space-y-0">
            {CONSENT_ITEMS.map((item) => (
              <li
                key={item.key}
                className="border-b py-3"
                style={{ borderColor: "var(--color-line)" }}
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
        </section>

        {/* 에러 */}
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

      {/* 하단 CTA */}
      <div className="px-5 pb-8 pt-4">
        <PrimaryButton
          onClick={handleSubmit}
          disabled={!allRequiredChecked || submitting}
          disabledLabel={
            submitting ? "저장 중..." : "필수 항목에 모두 동의해주세요"
          }
          showArrow={allRequiredChecked && !submitting}
        >
          시작하기
        </PrimaryButton>
      </div>
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

function ConsentRow({
  checked,
  onToggle,
  label,
  strong = false,
  termsAnchor,
}: ConsentRowProps) {
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        onClick={onToggle}
        className="flex items-center justify-center transition-colors"
        style={{
          width: 20,
          height: 20,
          flexShrink: 0,
          borderRadius: 4,
          border: checked
            ? "1px solid var(--color-ink)"
            : "1px solid var(--color-line-strong)",
          background: checked ? "var(--color-ink)" : "transparent",
          cursor: "pointer",
        }}
      >
        {checked && (
          <svg width="10" height="8" viewBox="0 0 10 8" aria-hidden>
            <path
              d="M1 4l3 3 5-6"
              stroke="var(--color-paper)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
            />
          </svg>
        )}
      </button>

      <label
        onClick={onToggle}
        className="font-sans text-ink"
        style={{
          fontSize: strong ? 14 : 13,
          fontWeight: strong ? 500 : 400,
          letterSpacing: "-0.005em",
          lineHeight: 1.5,
          cursor: "pointer",
          flex: 1,
        }}
      >
        {label}
      </label>

      {termsAnchor && (
        <Link
          href={`/terms${termsAnchor}`}
          target="_blank"
          rel="noopener noreferrer"
          className="font-sans text-mute underline underline-offset-2"
          style={{ fontSize: 11, letterSpacing: "-0.005em" }}
        >
          전문 보기
        </Link>
      )}
    </div>
  );
}
