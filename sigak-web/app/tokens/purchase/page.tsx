// SIGAK MVP v1.2 — /tokens/purchase
//
// 3 팩 카드 + 필수 동의 2개 + Toss SDK requestPayment.
// 쿼리 파라미터 intent, verdict_id 는 successUrl로 보존해서 confirmed 페이지가 소비.
//
// 흐름:
//   1. 팩 선택 → POST /api/v1/tokens/purchase-intent
//   2. 응답의 pg_order_id / pg_amount / pg_order_name 으로 Toss 결제창 호출
//   3. Toss successUrl → /tokens/confirmed?intent=...&verdict_id=...
//      (Toss가 paymentKey, orderId, amount 쿼리 자동 추가)
"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getToken } from "@/lib/auth";
import { authFetch, ApiError } from "@/lib/api/fetch";
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import {
  TOKEN_PACKS,
  type PackCode,
  type PurchaseIntentRequest,
  type PurchaseIntentResponse,
} from "@/lib/types/mvp";

const TOSS_CLIENT_KEY = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY || "";

function PurchaseContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const intent = searchParams.get("intent") || "";
  const verdictId = searchParams.get("verdict_id") || "";

  const [selected, setSelected] = useState<PackCode>("starter");
  const [consents, setConsents] = useState({ refund: false, no_withdrawal: false });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 로그인 체크
  useEffect(() => {
    if (!getToken()) {
      router.replace(`/auth/login?next=${encodeURIComponent("/tokens/purchase")}`);
    }
  }, [router]);

  const allRequiredChecked = consents.refund && consents.no_withdrawal;
  const canSubmit = allRequiredChecked && !submitting && TOSS_CLIENT_KEY.length > 0;

  // successUrl 쿼리 보존
  const successPath = useMemo(() => {
    const params = new URLSearchParams();
    if (intent) params.set("intent", intent);
    if (verdictId) params.set("verdict_id", verdictId);
    const q = params.toString();
    return q ? `/tokens/confirmed?${q}` : "/tokens/confirmed";
  }, [intent, verdictId]);

  async function handlePurchase() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const req: PurchaseIntentRequest = { pack_code: selected };
      const order = await authFetch<PurchaseIntentResponse>(
        "/api/v1/tokens/purchase-intent",
        { method: "POST", json: req },
      );

      // Toss SDK 동적 로드 (SSR 회피)
      const { loadTossPayments } = await import("@tosspayments/payment-sdk");
      const tossPayments = await loadTossPayments(TOSS_CLIENT_KEY);

      const origin =
        typeof window !== "undefined" ? window.location.origin : "";

      await tossPayments.requestPayment("카드", {
        amount: order.pg_amount,
        orderId: order.pg_order_id,
        orderName: order.pg_order_name,
        successUrl: `${origin}${successPath}`,
        failUrl: `${origin}/tokens/fail`,
      });
      // tossPayments.requestPayment는 새 창/페이지 이동이므로 여기 도달 시 취소된 것.
    } catch (e) {
      setSubmitting(false);
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/auth/login");
        return;
      }
      const msg = e instanceof Error ? e.message : "결제 시작에 실패했습니다";
      // Toss가 사용자 취소 시 throw하는 에러는 따로 처리 안함 (그냥 머물게)
      setError(msg);
    }
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
      <TopBar />

      <main style={{ flex: 1, padding: "40px 28px 24px" }}>
        {/* 헤드라인 */}
        {intent === "blur_release" ? (
          <>
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
              가려진 것들을 풀려면.
            </h1>
            <p
              className="font-sans"
              style={{
                marginTop: 14,
                fontSize: 13,
                opacity: 0.5,
                lineHeight: 1.6,
                color: "var(--color-ink)",
              }}
            >
              토큰을 충전하면 바로 이어집니다.
            </p>
          </>
        ) : (
          <>
            <h1
              className="font-serif"
              style={{
                fontSize: 32,
                fontWeight: 400,
                lineHeight: 1.3,
                letterSpacing: "-0.01em",
                margin: 0,
                color: "var(--color-ink)",
              }}
            >
              토큰 충전.
            </h1>
            <p
              className="font-sans"
              style={{
                marginTop: 14,
                fontSize: 13,
                opacity: 0.5,
                lineHeight: 1.6,
                color: "var(--color-ink)",
              }}
            >
              1 토큰 = 100원. 많이 사면 덜 냅니다.
            </p>
          </>
        )}

        {/* 팩 카드 */}
        <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 12 }}>
          {TOKEN_PACKS.map((pack) => (
            <PackCard
              key={pack.code}
              pack={pack}
              selected={selected === pack.code}
              onSelect={() => setSelected(pack.code)}
            />
          ))}
        </div>

        {/* 소비 단가 안내 */}
        <div
          style={{
            marginTop: 32,
            padding: "16px 0",
            borderTop: "1px solid rgba(0, 0, 0, 0.1)",
            borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
          }}
        >
          <div
            className="font-sans uppercase"
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "1.5px",
              opacity: 0.4,
              marginBottom: 10,
              color: "var(--color-ink)",
            }}
          >
            쓰임
          </div>
          <ConsumptionRow label="블러 해제" tokens={50} won={5000} />
          <ConsumptionRow label="추론 언락" tokens={5} won={500} />
          <ConsumptionRow label="월간 리포트" tokens={30} won={3000} />
        </div>

        {/* 동의 */}
        <div style={{ marginTop: 32 }}>
          <ConsentRow
            checked={consents.refund}
            onToggle={() => setConsents((c) => ({ ...c, refund: !c.refund }))}
            label="결제 약관 및 환불 정책 동의"
            termsAnchor="#tos"
          />
          <ConsentRow
            checked={consents.no_withdrawal}
            onToggle={() => setConsents((c) => ({ ...c, no_withdrawal: !c.no_withdrawal }))}
            label="디지털 콘텐츠 청약 철회 제한 사유 확인"
            termsAnchor="#tos"
          />
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

        {!TOSS_CLIENT_KEY && (
          <p
            className="font-sans"
            style={{
              marginTop: 16,
              fontSize: 11,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              opacity: 0.7,
            }}
          >
            결제 시스템이 설정되지 않았습니다. (NEXT_PUBLIC_TOSS_CLIENT_KEY)
          </p>
        )}
      </main>

      {/* CTA */}
      <div style={{ padding: "20px 28px 32px" }}>
        <PrimaryButton
          onClick={handlePurchase}
          disabled={!canSubmit}
          disabledLabel={
            submitting
              ? "이동 중..."
              : !allRequiredChecked
                ? "필수 동의 항목을 확인해주세요"
                : "결제"
          }
        >
          결제하기
        </PrimaryButton>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  PackCard
// ─────────────────────────────────────────────

interface PackMeta {
  code: PackCode;
  name_kr: string;
  amount_krw: number;
  tokens: number;
  perTokenKrw: number;
  badge?: string;
}

function PackCard({
  pack,
  selected,
  onSelect,
}: {
  pack: PackMeta;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      role="radio"
      aria-checked={selected}
      style={{
        width: "100%",
        padding: "20px 20px",
        background: selected ? "var(--color-ink)" : "transparent",
        color: selected ? "var(--color-paper)" : "var(--color-ink)",
        border: selected
          ? "1px solid var(--color-ink)"
          : "1px solid rgba(0, 0, 0, 0.15)",
        borderRadius: 0,
        cursor: "pointer",
        textAlign: "left",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        transition: "background 120ms ease, color 120ms ease",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            className="font-sans uppercase"
            style={{
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: "1.5px",
              opacity: selected ? 0.7 : 0.5,
            }}
          >
            {pack.name_kr}
          </span>
          {pack.badge && (
            <span
              className="font-sans"
              style={{
                fontSize: 10,
                fontWeight: 600,
                letterSpacing: "1px",
                opacity: selected ? 0.7 : 0.45,
                border: `0.5px solid ${selected ? "rgba(243, 240, 235, 0.4)" : "rgba(0, 0, 0, 0.3)"}`,
                padding: "2px 6px",
              }}
            >
              {pack.badge}
            </span>
          )}
        </div>
        <div
          className="font-serif tabular-nums"
          style={{ fontSize: 22, fontWeight: 400, letterSpacing: "-0.01em" }}
        >
          {pack.tokens.toLocaleString()}
          <span
            className="font-sans"
            style={{
              fontSize: 12,
              fontWeight: 400,
              letterSpacing: "-0.005em",
              marginLeft: 6,
              opacity: selected ? 0.7 : 0.55,
            }}
          >
            토큰
          </span>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
        <div
          className="font-serif tabular-nums"
          style={{ fontSize: 18, fontWeight: 400 }}
        >
          ₩{pack.amount_krw.toLocaleString()}
        </div>
        <div
          className="font-sans tabular-nums"
          style={{
            fontSize: 11,
            opacity: selected ? 0.7 : 0.5,
            letterSpacing: "-0.005em",
          }}
        >
          토큰당 ₩{pack.perTokenKrw}
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────
//  ConsumptionRow
// ─────────────────────────────────────────────

function ConsumptionRow({
  label,
  tokens,
  won,
}: {
  label: string;
  tokens: number;
  won: number;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        padding: "8px 0",
      }}
    >
      <span
        className="font-sans"
        style={{ fontSize: 13, letterSpacing: "-0.005em", color: "var(--color-ink)" }}
      >
        {label}
      </span>
      <span
        className="font-serif tabular-nums"
        style={{ fontSize: 13, color: "var(--color-ink)" }}
      >
        {tokens}토큰
        <span className="font-sans" style={{ fontSize: 11, opacity: 0.4, marginLeft: 8 }}>
          ₩{won.toLocaleString()}
        </span>
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────
//  ConsentRow
// ─────────────────────────────────────────────

function ConsentRow({
  checked,
  onToggle,
  label,
  termsAnchor,
}: {
  checked: boolean;
  onToggle: () => void;
  label: string;
  termsAnchor?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "14px 0",
        borderBottom: "1px solid rgba(0, 0, 0, 0.1)",
      }}
    >
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        onClick={onToggle}
        style={{
          width: 18,
          height: 18,
          flexShrink: 0,
          border: checked ? "1px solid var(--color-ink)" : "1px solid rgba(0, 0, 0, 0.25)",
          background: checked ? "var(--color-ink)" : "transparent",
          cursor: "pointer",
          padding: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
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
        className="font-sans"
        style={{
          fontSize: 13,
          fontWeight: 400,
          letterSpacing: "-0.005em",
          lineHeight: 1.5,
          cursor: "pointer",
          flex: 1,
          color: "var(--color-ink)",
        }}
      >
        [필수] {label}
      </label>
      {termsAnchor && (
        <Link
          href={`/terms${termsAnchor}`}
          target="_blank"
          rel="noopener noreferrer"
          className="font-sans"
          style={{
            fontSize: 11,
            letterSpacing: "-0.005em",
            opacity: 0.5,
            textDecoration: "underline",
            textUnderlineOffset: 2,
            color: "var(--color-ink)",
          }}
        >
          전문
        </Link>
      )}
    </div>
  );
}

export default function PurchasePage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", background: "var(--color-paper)" }} />}>
      <PurchaseContent />
    </Suspense>
  );
}
