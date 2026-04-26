// SIGAK MVP v2 BM — VisionView v3 (Phase I PI-D, 본인 결정 2026-04-25).
//
// /vision 탭 컨텐츠. PI v3 status 분기:
//
//   1) !has_baseline                       → 정면 사진 보여드리기 CTA → /pi/upload
//   2) has_baseline && !has_current_report → PI 풀어드리기 CTA → /pi/preview
//   3) has_current_report                  → 시각이 본 당신 v{N} 카드 → /pi/{report_id}

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/api/fetch";
import { deletePIv3, getPIv3Status } from "@/lib/api/pi";
import type { PIv3Status } from "@/lib/api/pi";

export function VisionView() {
  const router = useRouter();

  const [state, setState] = useState<{
    loading: boolean;
    status: PIv3Status | null;
    error: string | null;
  }>({ loading: true, status: null, error: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getPIv3Status();
        if (!cancelled) setState({ loading: false, status: data, error: null });
      } catch (e) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          router.replace("/");
          return;
        }
        setState({
          loading: false,
          status: null,
          error: e instanceof Error ? e.message : "PI 상태 로드 실패",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state.loading) return <LoadingPlaceholder />;
  if (state.error || !state.status)
    return <ErrorBlock message={state.error ?? "알 수 없는 오류"} />;

  const status = state.status;

  // 1) baseline 미업로드 — 정면 사진 보여드리기
  if (!status.has_baseline) {
    return <BaselineNeededBlock />;
  }

  // 2) baseline 있지만 PI 미생성 — preview 진입 (50토큰 paywall 은 PIv3Screen 안에서)
  if (!status.has_current_report) {
    return (
      <PIPendingBlock
        cost={status.unlock_cost_tokens}
        balance={status.token_balance}
        needs={status.needs_payment_tokens}
      />
    );
  }

  // 3) PI 풀 — 시각이 본 당신 v{N} 카드
  return (
    <PIUnlockedBlock
      reportId={status.current_report_id!}
      version={status.current_version}
      unlockedAt={status.unlocked_at}
    />
  );
}

// ─────────────────────────────────────────────
//  Blocks
// ─────────────────────────────────────────────

function LoadingPlaceholder() {
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
      aria-busy
    >
      불러오는 중...
    </div>
  );
}

function ErrorBlock({ message }: { message: string }) {
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
        {message}
      </p>
    </div>
  );
}

// 1) baseline 없음 — 정면 사진 한 컷 안내 (transition 카피 재노출)
function BaselineNeededBlock() {
  return (
    <section style={{ padding: "32px 28px 60px" }}>
      <div
        style={{
          padding: "20px 22px",
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
            marginBottom: 10,
          }}
        >
          PI — Personal Image
        </div>
        <p
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 18,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
          }}
        >
          시각이 본 나, 완성하려면<br />정면 사진 한 장이 필요해요.
        </p>
        <p
          className="font-sans"
          style={{
            margin: "12px 0 0",
            fontSize: 12,
            lineHeight: 1.7,
            opacity: 0.6,
            letterSpacing: "-0.005em",
          }}
        >
          얼굴이 또렷하게 잡히는 정면 한 컷이면 돼요. 화장은 안 하셔도 분석 가능해요.
        </p>
      </div>

      <Link
        href="/pi/upload?next=preview"
        className="font-sans"
        style={{
          marginTop: 18,
          width: "100%",
          height: 54,
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          border: "none",
          borderRadius: 0,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "0.5px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          textDecoration: "none",
        }}
      >
        📷 사진 한 장 보여드리기
      </Link>
    </section>
  );
}

// 2) baseline 있음, PI 미생성 — preview 진입
function PIPendingBlock({
  cost,
  balance,
  needs,
}: {
  cost: number;
  balance: number;
  needs: number;
}) {
  const insufficient = needs > 0;

  return (
    <section style={{ padding: "32px 28px 60px" }}>
      <div
        style={{
          padding: "20px 22px",
          border: "1px solid rgba(0,0,0,0.12)",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.5,
            marginBottom: 10,
          }}
        >
          READY
        </div>
        <p
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 18,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
          }}
        >
          정면 사진 받았어요.<br />이제 풀어드릴 수 있어요.
        </p>
        <div
          className="font-sans"
          style={{
            marginTop: 14,
            fontSize: 12,
            lineHeight: 1.7,
            opacity: 0.6,
            letterSpacing: "-0.005em",
          }}
        >
          보유 {balance}토큰 · 필요 {cost}토큰
          {insufficient && <> · 부족 {needs}토큰 (₩{(needs * 100).toLocaleString()})</>}
        </div>
      </div>

      <Link
        href="/pi/preview"
        className="font-sans"
        style={{
          marginTop: 18,
          width: "100%",
          height: 54,
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          border: "none",
          borderRadius: 0,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "0.5px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          textDecoration: "none",
        }}
      >
        먼저 미리보기 (무료)
      </Link>
    </section>
  );
}

// 3) PI 풀 — v{N} 카드 + 풀 화면 link + 다시 받기 / 삭제 (PI-REVIVE 2026-04-26)
function PIUnlockedBlock({
  reportId,
  version,
  unlockedAt,
}: {
  reportId: string;
  version: number | null;
  unlockedAt: string | null;
}) {
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const dateLabel = unlockedAt
    ? new Date(unlockedAt).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  async function handleDelete() {
    if (deleting) return;
    const ok = window.confirm(
      "이 리포트와 사진을 삭제하면 처음부터 다시 시작해야 해요. 정말 삭제할까요?",
    );
    if (!ok) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await deletePIv3();
      // status refetch — 가장 단순. /vision 그대로 reload.
      window.location.reload();
    } catch (e) {
      setDeleting(false);
      setDeleteError(
        e instanceof Error ? e.message : "삭제에 실패했어요. 잠시 후 다시 시도.",
      );
    }
  }

  return (
    <section style={{ padding: "32px 28px 60px" }}>
      <Link
        href={`/pi/${encodeURIComponent(reportId)}`}
        className="font-sans"
        style={{
          display: "block",
          padding: "24px 22px",
          border: "1px solid rgba(0,0,0,0.15)",
          color: "var(--color-ink)",
          textDecoration: "none",
          background: "var(--color-paper)",
        }}
      >
        <div
          className="font-sans uppercase"
          style={{
            fontSize: 10,
            fontWeight: 600,
            letterSpacing: "1.5px",
            opacity: 0.4,
          }}
        >
          시각이 본 당신{version != null && <> · v{version}</>}
        </div>
        <p
          className="font-serif"
          style={{
            margin: "10px 0 0",
            fontSize: 18,
            lineHeight: 1.55,
            letterSpacing: "-0.01em",
          }}
        >
          현재 리포트 열기 →
        </p>
        {dateLabel && (
          <p
            className="font-sans"
            style={{
              margin: "8px 0 0",
              fontSize: 11,
              opacity: 0.5,
              letterSpacing: "-0.005em",
            }}
          >
            {dateLabel} 분석
          </p>
        )}
      </Link>

      <div
        style={{
          marginTop: 18,
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <Link
          href="/pi/upload?next=preview"
          className="font-sans"
          style={{
            display: "flex",
            width: "100%",
            height: 48,
            alignItems: "center",
            justifyContent: "center",
            background: "transparent",
            color: "var(--color-ink)",
            border: "1px solid rgba(0,0,0,0.15)",
            fontSize: 13,
            fontWeight: 500,
            letterSpacing: "-0.005em",
            textDecoration: "none",
            borderRadius: 0,
          }}
        >
          📷 사진 다시 올려서 새로 받기
        </Link>
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="font-sans"
          style={{
            width: "100%",
            height: 36,
            background: "transparent",
            color: "var(--color-mute)",
            border: "none",
            padding: 0,
            fontSize: 12,
            letterSpacing: "-0.005em",
            cursor: deleting ? "default" : "pointer",
            textDecoration: "underline",
            opacity: deleting ? 0.55 : 1,
          }}
        >
          {deleting ? "삭제 중..." : "이 리포트 삭제"}
        </button>
        {deleteError && (
          <p
            className="font-sans"
            role="alert"
            style={{
              margin: 0,
              fontSize: 11,
              color: "var(--color-danger)",
              letterSpacing: "-0.005em",
              textAlign: "center",
            }}
          >
            {deleteError}
          </p>
        )}
      </div>
    </section>
  );
}
