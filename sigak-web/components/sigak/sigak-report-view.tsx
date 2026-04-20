// SIGAK MVP v1.2 — SigakReportView
//
// "시각" 탭 컨텐츠. 피드 추천/서비스의 기반이 되는 유저 분석 요약.
// 30 토큰 소비 시 해제.
//
// released=false:
//   - 상단 IntroBox ("피드 추천과 서비스는 모두 시각이 본 당신을 기반으로…")
//   - 블러 처리된 레포트 프리뷰 (4섹션 placeholder: 체형/얼굴/추구미/자기인식)
//   - 하단 PRO CTA "시각 리포트 해제 · 30 토큰"
//     * 잔액 충분 → 인라인 release
//     * 잔액 부족 → /tokens/purchase?intent=sigak_report (intent 신규)
//
// released=true:
//   - 전체 공개 레포트 렌더. 온보딩 값 → 한글 라벨 변환.
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getSigakReport, releaseSigakReport } from "@/lib/api/sigak-report";
import type { OnboardingData, SigakReportResponse } from "@/lib/types/mvp";
import { labelFor, labelsFor } from "@/lib/utils/onboarding-labels";
import { useTokenBalance } from "@/hooks/use-token-balance";

export function SigakReportView() {
  const router = useRouter();
  const { balance, refetch: refetchBalance } = useTokenBalance();

  const [state, setState] = useState<{
    loading: boolean;
    data: SigakReportResponse | null;
    error: string | null;
  }>({ loading: true, data: null, error: null });

  const [releasing, setReleasing] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getSigakReport();
        if (!cancelled) setState({ loading: false, data, error: null });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        setState({
          loading: false,
          data: null,
          error: e instanceof Error ? e.message : "시각 리포트 로드 실패",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function handleRelease() {
    if (!state.data || releasing) return;
    const cost = state.data.cost;

    // 잔액 부족 → purchase 페이지로 intent 전달
    if (balance != null && balance < cost) {
      router.push(
        `/tokens/purchase?intent=sigak_report&cost=${cost}`,
      );
      return;
    }

    setReleasing(true);
    setReleaseError(null);
    try {
      const res = await releaseSigakReport();
      setState((prev) => ({
        ...prev,
        data: {
          released: true,
          cost: prev.data?.cost ?? cost,
          onboarding_data: res.onboarding_data,
        },
      }));
      await refetchBalance();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push(`/tokens/purchase?intent=sigak_report&cost=${cost}`);
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
        return;
      }
      setReleaseError(
        e instanceof Error ? e.message : "해제에 실패했습니다.",
      );
    } finally {
      setReleasing(false);
    }
  }

  if (state.loading) {
    return (
      <div
        style={{
          minHeight: "40vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: 0.3,
          fontSize: 12,
          fontFamily: "var(--font-sans)",
          color: "var(--color-ink)",
        }}
      >
        불러오는 중...
      </div>
    );
  }

  if (state.error || !state.data) {
    return (
      <div style={{ padding: "40px 28px", textAlign: "center" }}>
        <p
          className="font-sans"
          style={{
            fontSize: 13,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
          }}
          role="alert"
        >
          {state.error ?? "알 수 없는 오류"}
        </p>
      </div>
    );
  }

  const { data } = state;
  const released = data.released;
  const cost = data.cost;

  return (
    <section style={{ padding: "24px 28px 60px" }}>
      {/* Intro */}
      <IntroBox />

      {/* Report 카드 */}
      <div style={{ marginTop: 24, position: "relative" }}>
        {released && data.onboarding_data ? (
          <ReportContent data={data.onboarding_data} />
        ) : (
          <ReportLocked />
        )}
      </div>

      {/* Unlock CTA (잠긴 상태에서만) */}
      {!released && (
        <div style={{ marginTop: 20 }}>
          <UnlockButton
            cost={cost}
            busy={releasing}
            balance={balance}
            onClick={handleRelease}
          />
          {releaseError && (
            <p
              className="font-sans"
              role="alert"
              style={{
                marginTop: 10,
                fontSize: 11,
                textAlign: "right",
                color: "var(--color-danger)",
                letterSpacing: "-0.005em",
              }}
            >
              {releaseError}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// ─────────────────────────────────────────────
//  IntroBox
// ─────────────────────────────────────────────

function IntroBox() {
  return (
    <div
      style={{
        padding: "16px 18px",
        border: "1px solid rgba(0, 0, 0, 0.12)",
        background: "rgba(0, 0, 0, 0.02)",
      }}
    >
      <div
        className="font-sans uppercase"
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "1.5px",
          opacity: 0.4,
          color: "var(--color-ink)",
          marginBottom: 8,
        }}
      >
        시각
      </div>
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 13,
          lineHeight: 1.7,
          color: "var(--color-ink)",
          letterSpacing: "-0.005em",
        }}
      >
        피드 추천과 서비스는 모두 시각이 본 당신을
        <br />
        기반으로 만들어집니다.
      </p>
    </div>
  );
}

// ─────────────────────────────────────────────
//  ReportLocked — 블러 placeholder
// ─────────────────────────────────────────────

function ReportLocked() {
  return (
    <div
      style={{
        border: "1px solid rgba(0, 0, 0, 0.12)",
        padding: "28px 22px",
        background: "transparent",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* 블러 처리된 placeholder */}
      <div
        style={{
          filter: "blur(6px)",
          userSelect: "none",
          pointerEvents: "none",
          opacity: 0.8,
        }}
      >
        <LockedSection
          label="체형"
          lines={["키 160~165cm · 체중 50~55kg", "어깨 보통 · 목 보통"]}
        />
        <LockedSection
          label="얼굴"
          lines={["넓은 얼굴 · 짧은 이마 · 광대"]}
        />
        <LockedSection
          label="추구미"
          lines={[
            "내추럴 · 모던 · 우아",
            "깔끔하면서 분위기 있는 도시 여자",
          ]}
        />
        <LockedSection
          label="자기인식"
          lines={["차분해 보인다는 말을 자주 듣습니다"]}
          last
        />
      </div>

      {/* 잠금 아이콘 중앙 */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            background: "rgba(0, 0, 0, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="18" height="20" viewBox="0 0 18 20" aria-hidden>
            <rect
              x="2"
              y="9"
              width="14"
              height="10"
              rx="1.5"
              stroke="#F3F0EB"
              strokeWidth="1.5"
              fill="none"
            />
            <path
              d="M5 9V6a4 4 0 018 0v3"
              stroke="#F3F0EB"
              strokeWidth="1.5"
              strokeLinecap="round"
              fill="none"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}

function LockedSection({
  label,
  lines,
  last = false,
}: {
  label: string;
  lines: string[];
  last?: boolean;
}) {
  return (
    <div
      style={{
        paddingBottom: 16,
        marginBottom: 16,
        borderBottom: last ? "none" : "1px solid rgba(0, 0, 0, 0.08)",
      }}
    >
      <div
        className="font-sans uppercase"
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "1.5px",
          opacity: 0.4,
          color: "var(--color-ink)",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      {lines.map((l, i) => (
        <p
          key={i}
          className="font-serif"
          style={{
            margin: i > 0 ? "4px 0 0" : 0,
            fontSize: 15,
            lineHeight: 1.6,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        >
          {l}
        </p>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
//  ReportContent — 해제 상태, 실제 데이터
// ─────────────────────────────────────────────

function ReportContent({ data }: { data: OnboardingData }) {
  const height = labelFor("height", asString(data.height));
  const weight = labelFor("weight", asString(data.weight));
  const shoulder = labelFor("shoulder_width", asString(data.shoulder_width));
  const neck = labelFor("neck_length", asString(data.neck_length));

  const faceConcerns = labelsFor("face_concerns", asString(data.face_concerns));

  const styleKeywords = labelsFor(
    "style_image_keywords",
    asString(data.style_image_keywords),
  );
  const desiredImage = asString(data.desired_image) ?? "";
  const referenceCelebs = asString(data.reference_celebs) ?? "";
  const makeup = labelFor("makeup_level", asString(data.makeup_level));

  const selfPerception = asString(data.self_perception) ?? "";
  const currentConcerns = asString(data.current_concerns) ?? "";

  return (
    <div
      style={{
        border: "1px solid rgba(0, 0, 0, 0.15)",
        padding: "28px 22px",
      }}
    >
      {/* 체형 */}
      <ReportSection label="체형" last={false}>
        <Line>키 {height || "—"} · 체중 {weight || "—"}</Line>
        <Line>어깨 {shoulder || "—"} · 목 {neck || "—"}</Line>
      </ReportSection>

      {/* 얼굴 */}
      <ReportSection label="얼굴" last={false}>
        <Line>{faceConcerns.length > 0 ? faceConcerns.join(" · ") : "—"}</Line>
      </ReportSection>

      {/* 추구미 */}
      <ReportSection label="추구미" last={false}>
        {styleKeywords.length > 0 && (
          <Line>{styleKeywords.join(" · ")}</Line>
        )}
        {desiredImage && <Line>{desiredImage}</Line>}
        {referenceCelebs && (
          <Line muted>레퍼런스 — {referenceCelebs}</Line>
        )}
        {makeup && <Line muted>메이크업 — {makeup}</Line>}
      </ReportSection>

      {/* 자기인식 */}
      <ReportSection label="자기인식" last>
        {selfPerception && <Line>{selfPerception}</Line>}
        {currentConcerns && <Line muted>{currentConcerns}</Line>}
      </ReportSection>
    </div>
  );
}

function ReportSection({
  label,
  last,
  children,
}: {
  label: string;
  last: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        paddingBottom: 18,
        marginBottom: 18,
        borderBottom: last ? "none" : "1px solid rgba(0, 0, 0, 0.08)",
      }}
    >
      <div
        className="font-sans uppercase"
        style={{
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: "1.5px",
          opacity: 0.4,
          color: "var(--color-ink)",
          marginBottom: 10,
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

function Line({
  children,
  muted = false,
}: {
  children: React.ReactNode;
  muted?: boolean;
}) {
  return (
    <p
      className="font-serif"
      style={{
        margin: "0 0 4px",
        fontSize: 15,
        lineHeight: 1.65,
        color: "var(--color-ink)",
        letterSpacing: "-0.005em",
        opacity: muted ? 0.55 : 1,
      }}
    >
      {children}
    </p>
  );
}

function asString(v: unknown): string | undefined {
  if (typeof v === "string") return v;
  if (v == null) return undefined;
  return String(v);
}

// ─────────────────────────────────────────────
//  UnlockButton
// ─────────────────────────────────────────────

function UnlockButton({
  cost,
  busy,
  balance,
  onClick,
}: {
  cost: number;
  busy: boolean;
  balance: number | null;
  onClick: () => void;
}) {
  const insufficient = balance != null && balance < cost;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="font-sans"
      style={{
        width: "100%",
        height: 54,
        background: busy ? "transparent" : "var(--color-ink)",
        color: busy ? "var(--color-ink)" : "var(--color-paper)",
        border: busy ? "1px solid rgba(0, 0, 0, 0.15)" : "none",
        borderRadius: 0,
        fontSize: 14,
        fontWeight: 600,
        letterSpacing: "0.5px",
        cursor: busy ? "default" : "pointer",
        opacity: busy ? 0.5 : 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 10,
      }}
    >
      {busy ? (
        "해제 중..."
      ) : insufficient ? (
        <>
          <span>충전하고 해제</span>
          <span className="font-serif tabular-nums" style={{ fontWeight: 400 }}>
            · {cost} 토큰
          </span>
        </>
      ) : (
        <>
          <span>시각 리포트 해제</span>
          <span className="font-serif tabular-nums" style={{ fontWeight: 400 }}>
            · {cost} 토큰
          </span>
        </>
      )}
    </button>
  );
}
