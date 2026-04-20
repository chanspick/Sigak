// SIGAK MVP v2 BM — VisionView
//
// /vision 탭 컨텐츠. PI 해제 상태 분기:
//   - unlocked=false: 큰 잠금 블록 + "PI 확인 · 50 토큰" CTA
//   - unlocked=true: PI 풀 리포트 섹션들 (stub placeholder 렌더, 실제 데이터는 후속)
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { getPI, unlockPI } from "@/lib/api/pi";
import type { PIReportData, PIStatusResponse } from "@/lib/types/mvp";
import { useTokenBalance } from "@/hooks/use-token-balance";

export function VisionView() {
  const router = useRouter();
  const { balance, refetch: refetchBalance } = useTokenBalance();

  const [state, setState] = useState<{
    loading: boolean;
    data: PIStatusResponse | null;
    error: string | null;
  }>({ loading: true, data: null, error: null });

  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getPI();
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
          error: e instanceof Error ? e.message : "PI 상태 로드 실패",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function handleUnlock() {
    if (!state.data || unlocking) return;
    const cost = state.data.cost;

    if (balance != null && balance < cost) {
      router.push(`/tokens/purchase?intent=unlock_pi`);
      return;
    }

    setUnlocking(true);
    setUnlockError(null);
    try {
      const res = await unlockPI();
      setState((prev) => ({
        ...prev,
        data: {
          unlocked: true,
          cost: prev.data?.cost ?? cost,
          unlocked_at: res.unlocked_at,
          report_data: res.report_data,
        },
      }));
      await refetchBalance();
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        router.push(`/tokens/purchase?intent=unlock_pi`);
        return;
      }
      if (e instanceof ApiError && e.status === 401) {
        router.replace("/");
        return;
      }
      setUnlockError(
        e instanceof Error ? e.message : "PI 해제에 실패했습니다.",
      );
    } finally {
      setUnlocking(false);
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
          role="alert"
          style={{
            fontSize: 13,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
          }}
        >
          {state.error ?? "알 수 없는 오류"}
        </p>
      </div>
    );
  }

  const { data } = state;

  if (!data.unlocked) {
    return (
      <PILocked
        cost={data.cost}
        balance={balance}
        busy={unlocking}
        error={unlockError}
        onUnlock={handleUnlock}
      />
    );
  }

  return <PIUnlocked data={data.report_data ?? null} />;
}

// ─────────────────────────────────────────────
//  PI Locked
// ─────────────────────────────────────────────

function PILocked({
  cost,
  balance,
  busy,
  error,
  onUnlock,
}: {
  cost: number;
  balance: number | null;
  busy: boolean;
  error: string | null;
  onUnlock: () => void;
}) {
  const insufficient = balance != null && balance < cost;

  return (
    <section style={{ padding: "28px 28px 60px" }}>
      {/* 설명 */}
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
          PI — Personal Image
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

      {/* 블러 placeholder 카드 */}
      <div
        style={{
          marginTop: 24,
          position: "relative",
          border: "1px solid rgba(0, 0, 0, 0.12)",
          padding: "28px 22px",
          background: "transparent",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            filter: "blur(6px)",
            pointerEvents: "none",
            userSelect: "none",
            opacity: 0.75,
          }}
        >
          <LockedSection label="얼굴 분석" lines={["3축 좌표 · 얼굴형 · 이목구비 비율"]} />
          <LockedSection label="피부톤" lines={["퍼스널 컬러 · 추천 색상"]} />
          <LockedSection label="갭 분석" lines={["현재 × 추구미 방향성"]} />
          <LockedSection label="헤어 추천" lines={["TOP 3 매칭 · 스타일별 가이드"]} />
          <LockedSection label="메이크업" lines={["단계별 포인트 메이크업"]} last />
        </div>
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

      {/* CTA */}
      <div style={{ marginTop: 20 }}>
        <button
          type="button"
          onClick={onUnlock}
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
          ) : (
            <>
              <span>{insufficient ? "충전하고 PI 확인" : "PI 확인"}</span>
              <span className="font-serif tabular-nums" style={{ fontWeight: 400 }}>
                · {cost} 토큰
              </span>
            </>
          )}
        </button>
        {error && (
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
            {error}
          </p>
        )}
      </div>
    </section>
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
        paddingBottom: 14,
        marginBottom: 14,
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
          marginBottom: 6,
        }}
      >
        {label}
      </div>
      {lines.map((l, i) => (
        <p
          key={i}
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 14,
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
//  PI Unlocked — report_data 렌더
// ─────────────────────────────────────────────

function PIUnlocked({ data }: { data: PIReportData | null }) {
  const isGenerating = !data || data.status === "generating";
  const isMigrated = data?.status === "migrated_from_sigak_report";

  return (
    <section style={{ padding: "28px 28px 60px" }}>
      <div
        style={{
          border: "1px solid rgba(0, 0, 0, 0.15)",
          padding: "28px 22px",
        }}
      >
        {isGenerating ? (
          <GeneratingBlock />
        ) : (
          <ReportBlocks data={data} />
        )}
        {isMigrated && (
          <p
            className="font-sans"
            style={{
              marginTop: 24,
              paddingTop: 16,
              borderTop: "1px solid rgba(0, 0, 0, 0.08)",
              margin: "24px 0 0",
              fontSize: 11,
              lineHeight: 1.7,
              opacity: 0.45,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
            }}
          >
            ✓ 기존 시각 리포트로부터 이관됨 (재결제 면제)
          </p>
        )}
      </div>
    </section>
  );
}

function GeneratingBlock() {
  return (
    <div style={{ padding: "20px 0", textAlign: "center" }}>
      <p
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 18,
          lineHeight: 1.6,
          letterSpacing: "-0.01em",
          color: "var(--color-ink)",
        }}
      >
        리포트를 만들고 있어요.
      </p>
      <p
        className="font-sans"
        style={{
          margin: "12px 0 0",
          fontSize: 12,
          opacity: 0.5,
          lineHeight: 1.7,
          color: "var(--color-ink)",
        }}
      >
        얼굴·피부·갭·헤어·메이크업 전 섹션이 준비되면
        <br />
        자동으로 여기 표시됩니다.
      </p>
    </div>
  );
}

function ReportBlocks({ data }: { data: PIReportData }) {
  // 실제 섹션 렌더는 후속 작업에서 (본인 지시 대기). 지금은 보유 키를 리스트로.
  const sections: { key: string; label: string; value: unknown }[] = [
    { key: "face_analysis", label: "얼굴 분석", value: data.face_analysis },
    { key: "skin_tone", label: "피부톤", value: data.skin_tone },
    { key: "gap_analysis", label: "갭 분석", value: data.gap_analysis },
    { key: "hair_recommendations", label: "헤어 추천", value: data.hair_recommendations },
    { key: "makeup_guide", label: "메이크업", value: data.makeup_guide },
  ];

  return (
    <>
      {sections.map((s, i) => (
        <div
          key={s.key}
          style={{
            paddingBottom: 18,
            marginBottom: 18,
            borderBottom:
              i === sections.length - 1 ? "none" : "1px solid rgba(0, 0, 0, 0.08)",
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
            {s.label}
          </div>
          <p
            className="font-serif"
            style={{
              margin: 0,
              fontSize: 15,
              lineHeight: 1.7,
              opacity: s.value ? 1 : 0.4,
              color: "var(--color-ink)",
              letterSpacing: "-0.005em",
            }}
          >
            {s.value ? JSON.stringify(s.value) : "— 준비 중"}
          </p>
        </div>
      ))}
    </>
  );
}
