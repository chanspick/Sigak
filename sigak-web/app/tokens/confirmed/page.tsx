// SIGAK MVP v1.2 — /tokens/confirmed
//
// Toss 결제 성공 시 returnUrl. 쿼리:
//   - Toss 자동 추가: paymentKey, orderId, amount
//   - 우리가 보존: intent, verdict_id
//
// 흐름:
//   1. POST /api/v1/payments/confirm/{order_id} (payment_key, amount)
//   2. 성공 시 잔액 갱신 표시
//   3. intent=blur_release 이면 자동 POST /verdicts/{id}/release-blur
//      - 성공 → "결과 보러 가기" (→ /verdict/{id})
//      - 실패 → 토큰은 이미 적립됐으니 수동 안내
//   4. intent 없으면 "홈으로" CTA
//
// 방어: payment confirm은 idempotent (backend). 페이지 재방문해도 안전.
//       release-blur도 idempotent (`blur:{verdict_id}` 키).
"use client";

import Link from "next/link";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { getToken } from "@/lib/auth";
import { ApiError } from "@/lib/api/fetch";
import { api } from "@/lib/api/fetch";
import { releaseBlur, unlockDiagnosis } from "@/lib/api/verdicts";
import { releaseSigakReport } from "@/lib/api/sigak-report";
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

type Phase =
  | "confirming"              // payment confirm 호출 중
  | "released"                // intent=blur_release + release-blur 성공 (legacy)
  | "release_failed"          // intent=blur_release + release-blur 실패 (legacy)
  | "sigak_released"          // intent=sigak_report (deprecated)
  | "sigak_release_failed"    // intent=sigak_report 실패 (deprecated)
  | "diagnosis_unlocked"      // v2 intent=unlock_diagnosis 성공
  | "diagnosis_unlock_failed" // v2 intent=unlock_diagnosis 실패 (토큰 적립됨)
  | "charged"                 // 일반 충전 완료
  | "failed";                 // payment confirm 자체 실패

function ConfirmedContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [phase, setPhase] = useState<Phase>("confirming");
  const [balance, setBalance] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const executedRef = useRef(false);

  // Toss 쿼리
  const paymentKey = searchParams.get("paymentKey");
  const orderId = searchParams.get("orderId");
  const amountStr = searchParams.get("amount");

  // 우리 쿼리 (successUrl로 보존된 것)
  const intent = searchParams.get("intent") || "";
  const verdictId = searchParams.get("verdict_id") || "";

  useEffect(() => {
    if (executedRef.current) return;

    // 로그인 체크
    if (!getToken()) {
      router.replace("/auth/login");
      return;
    }

    if (!paymentKey || !orderId || !amountStr) {
      setPhase("failed");
      setErrorMessage("결제 정보가 없습니다. 결제를 다시 시도해 주세요.");
      return;
    }
    const amount = Number(amountStr);
    if (!Number.isFinite(amount) || amount <= 0) {
      setPhase("failed");
      setErrorMessage("결제 금액 파싱 실패");
      return;
    }

    executedRef.current = true;

    (async () => {
      // 1. Payment confirm
      try {
        const res = await api.confirmPayment(orderId, {
          payment_key: paymentKey,
          amount,
        });
        setBalance(res.balance_after);
        if (res.status !== "paid") {
          setPhase("failed");
          setErrorMessage("결제가 완료되지 않았습니다.");
          return;
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/auth/login");
          return;
        }
        setPhase("failed");
        setErrorMessage(
          e instanceof Error ? e.message : "결제 확인에 실패했습니다.",
        );
        return;
      }

      // 2-a. intent=blur_release 면 자동 release-blur
      if (intent === "blur_release" && verdictId) {
        try {
          const rel = await releaseBlur(verdictId);
          setBalance(rel.balance_after);
          setPhase("released");
        } catch (e) {
          setPhase("release_failed");
          setErrorMessage(
            e instanceof Error
              ? e.message
              : "블러 해제에 실패했습니다. 판정 페이지에서 다시 시도해 주세요.",
          );
        }
        return;
      }

      // 2-b. intent=sigak_report (deprecated — legacy 30토큰. 현재 유저가 도달하지 않음)
      if (intent === "sigak_report") {
        try {
          const rel = await releaseSigakReport();
          setBalance(rel.balance_after);
          setPhase("sigak_released");
        } catch (e) {
          setPhase("sigak_release_failed");
          setErrorMessage(
            e instanceof Error
              ? e.message
              : "시각 리포트 해제에 실패했습니다. 시각 탭에서 다시 시도해 주세요.",
          );
        }
        return;
      }

      // 2-c. v2 BM: intent=unlock_diagnosis — 10토큰 진단 해제
      if (intent === "unlock_diagnosis" && verdictId) {
        try {
          const rel = await unlockDiagnosis(verdictId);
          setBalance(rel.token_balance);
          setPhase("diagnosis_unlocked");
        } catch (e) {
          if (e instanceof ApiError && e.status === 409) {
            // 이미 해제된 경우 (재진입) — 성공으로 취급
            setPhase("diagnosis_unlocked");
            return;
          }
          setPhase("diagnosis_unlock_failed");
          setErrorMessage(
            e instanceof Error
              ? e.message
              : "진단 해제에 실패했습니다. 판정 페이지에서 다시 시도해 주세요.",
          );
        }
        return;
      }

      // 3. 일반 충전
      setPhase("charged");
    })();
  }, [router, paymentKey, orderId, amountStr, intent, verdictId]);

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
      <TopBar backTarget="/" />

      <main
        style={{
          flex: 1,
          padding: "48px 28px 24px",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {phase === "confirming" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              확인하고 있습니다.
            </h1>
            <p
              className="font-sans"
              style={{
                marginTop: 16,
                fontSize: 13,
                opacity: 0.5,
                lineHeight: 1.6,
              }}
            >
              잠시만.
            </p>
          </>
        )}

        {phase === "released" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              해제되었습니다.
            </h1>
            <p
              className="font-sans"
              style={{ marginTop: 16, fontSize: 13, opacity: 0.5, lineHeight: 1.6 }}
            >
              결제 완료 · 블러 해제 완료.
            </p>
            <BalanceRow balance={balance} />
          </>
        )}

        {phase === "release_failed" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              결제는 완료됐어요.
            </h1>
            <p
              className="font-sans"
              style={{ marginTop: 16, fontSize: 13, opacity: 0.55, lineHeight: 1.7, letterSpacing: "-0.005em" }}
            >
              토큰은 적립됐지만 블러 해제 중 오류가 있었어요.
              <br />
              판정 페이지로 돌아가 다시 시도해 주세요.
            </p>
            <BalanceRow balance={balance} />
            {errorMessage && (
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
                {errorMessage}
              </p>
            )}
          </>
        )}

        {phase === "sigak_released" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              해제되었습니다.
            </h1>
            <p
              className="font-sans"
              style={{ marginTop: 16, fontSize: 13, opacity: 0.5, lineHeight: 1.6 }}
            >
              결제 완료 · 시각 리포트 해제 완료.
            </p>
            <BalanceRow balance={balance} />
          </>
        )}

        {phase === "diagnosis_unlocked" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              진단이 열렸습니다.
            </h1>
            <p
              className="font-sans"
              style={{ marginTop: 16, fontSize: 13, opacity: 0.5, lineHeight: 1.6 }}
            >
              결제 완료 · 진단 해제 완료.
            </p>
            <BalanceRow balance={balance} />
          </>
        )}

        {phase === "diagnosis_unlock_failed" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              결제는 완료됐어요.
            </h1>
            <p
              className="font-sans"
              style={{ marginTop: 16, fontSize: 13, opacity: 0.55, lineHeight: 1.7, letterSpacing: "-0.005em" }}
            >
              토큰은 적립됐지만 진단 해제 중 오류가 있었어요.
              <br />
              판정 페이지로 돌아가 다시 시도해 주세요.
            </p>
            <BalanceRow balance={balance} />
            {errorMessage && (
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
                {errorMessage}
              </p>
            )}
          </>
        )}

        {phase === "sigak_release_failed" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              결제는 완료됐어요.
            </h1>
            <p
              className="font-sans"
              style={{ marginTop: 16, fontSize: 13, opacity: 0.55, lineHeight: 1.7, letterSpacing: "-0.005em" }}
            >
              토큰은 적립됐지만 시각 리포트 해제 중 오류가 있었어요.
              <br />
              시각 탭에서 다시 시도해 주세요.
            </p>
            <BalanceRow balance={balance} />
            {errorMessage && (
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
                {errorMessage}
              </p>
            )}
          </>
        )}

        {phase === "charged" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              충전 완료.
            </h1>
            <BalanceRow balance={balance} />
          </>
        )}

        {phase === "failed" && (
          <>
            <h1
              className="font-serif"
              style={{ fontSize: 32, fontWeight: 700, lineHeight: 1.25, margin: 0, letterSpacing: "-0.025em" }}
            >
              결제 확인 실패.
            </h1>
            <p
              className="font-sans"
              role="alert"
              style={{
                marginTop: 16,
                fontSize: 13,
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
                lineHeight: 1.6,
              }}
            >
              {errorMessage || "알 수 없는 오류가 발생했습니다."}
            </p>
            <p
              className="font-sans"
              style={{
                marginTop: 20,
                fontSize: 12,
                opacity: 0.5,
                lineHeight: 1.7,
                letterSpacing: "-0.005em",
              }}
            >
              문의: <a href="mailto:partner@sigak.asia" style={{ textDecoration: "underline", textUnderlineOffset: 2 }}>partner@sigak.asia</a>
              <br />
              주문번호: <span className="font-mono tabular-nums">{orderId || "-"}</span>
            </p>
          </>
        )}
      </main>

      {/* CTA */}
      <div style={{ padding: "20px 28px 32px" }}>
        {phase === "released" && verdictId && (
          <PillCta onClick={() => router.replace(`/verdict/${verdictId}`)}>
            결과 보러 가기
          </PillCta>
        )}
        {phase === "release_failed" && verdictId && (
          <PillCta onClick={() => router.replace(`/verdict/${verdictId}`)}>
            판정 페이지로
          </PillCta>
        )}
        {phase === "sigak_released" && (
          <PillCta onClick={() => router.replace("/")}>
            시각 리포트 보러 가기
          </PillCta>
        )}
        {phase === "sigak_release_failed" && (
          <PillCta onClick={() => router.replace("/")}>
            홈으로
          </PillCta>
        )}
        {phase === "diagnosis_unlocked" && verdictId && (
          <PillCta onClick={() => router.replace(`/verdict/${verdictId}`)}>
            진단 보러 가기
          </PillCta>
        )}
        {phase === "diagnosis_unlock_failed" && verdictId && (
          <PillCta onClick={() => router.replace(`/verdict/${verdictId}`)}>
            판정 페이지로
          </PillCta>
        )}
        {phase === "charged" && (
          <PillCta onClick={() => router.replace("/")}>홈으로</PillCta>
        )}
        {phase === "failed" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <PillCta onClick={() => router.replace("/tokens/purchase")}>
              다시 시도
            </PillCta>
            <Link
              href="/"
              className="font-sans"
              style={{
                textAlign: "center",
                fontSize: 13,
                opacity: 0.55,
                letterSpacing: "-0.005em",
                color: "var(--color-ink)",
                textDecoration: "none",
              }}
            >
              홈으로
            </Link>
          </div>
        )}
      </div>

      {/* 사업자 정보 (PG 심사 필수) */}
      <SiteFooter />
    </div>
  );
}

// ─────────────────────────────────────────────
//  BalanceRow — 마케터 결제완료_모달의 token-change 카드 시각 정합
//  radius 14 + soft bg + mono BALANCE label + Noto Serif 잔액
// ─────────────────────────────────────────────

function BalanceRow({ balance }: { balance: number | null }) {
  return (
    <div
      style={{
        marginTop: 28,
        background: "rgba(0, 0, 0, 0.04)",
        border: "1px solid var(--color-line)",
        borderRadius: 14,
        padding: "16px 22px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "var(--color-mute)",
        }}
      >
        BALANCE
      </span>
      <span
        className="font-serif tabular-nums"
        style={{
          fontSize: 20,
          fontWeight: 500,
          color: "var(--color-ink)",
          letterSpacing: "-0.018em",
          display: "flex",
          alignItems: "baseline",
          gap: 5,
        }}
      >
        {balance == null ? "—" : balance.toLocaleString()}
        <span
          className="font-sans"
          style={{ fontSize: 13, color: "var(--color-mute)" }}
        >
          토큰
        </span>
      </span>
    </div>
  );
}

// ─────────────────────────────────────────────
//  PillCta — 마케터 pill CTA (radius 100, ink bg, paper text)
//  PillCta 의 마케터 정합 대체
// ─────────────────────────────────────────────

function PillCta({
  onClick,
  children,
}: {
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="font-sans"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        padding: "17px 24px",
        background: "var(--color-ink)",
        color: "var(--color-paper)",
        border: "none",
        borderRadius: 100,
        fontSize: 15,
        fontWeight: 600,
        letterSpacing: "-0.012em",
        cursor: "pointer",
        transition: "all 0.2s ease",
      }}
    >
      {children}
    </button>
  );
}

export default function ConfirmedPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: "100vh", background: "var(--color-paper)" }} />}>
      <ConfirmedContent />
    </Suspense>
  );
}
