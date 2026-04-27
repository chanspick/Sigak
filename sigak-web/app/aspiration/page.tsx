/**
 * /aspiration — 추구미 분석 시작 (Phase J).
 *
 * 두 가지 입력 채널:
 *   - Instagram: @핸들 또는 URL (백엔드가 "@" prefix / URL 정규화)
 *   - Pinterest: 보드 URL (v1.5 정식 활성화. devcake actor + raw R2 보존)
 *
 * 백엔드 동기 호출:
 *   POST /api/v2/aspiration/ig         → response.status 즉시 반환
 *   POST /api/v2/aspiration/pinterest  → 동일
 *
 * 흐름:
 *   1. 가드 + 잔액 조회 (필요: 20 토큰)
 *   2. 탭 선택 + 입력 + 검증
 *   3. 분석 시작 → LoadingSlides 풀스크린
 *   4. response 처리:
 *      - completed         → /aspiration/{id}
 *      - failed_blocked    → 차단 안내
 *      - failed_private    → 비공개 안내
 *      - failed_scrape     → 수집 실패 안내 (토큰 환불됨)
 *      - failed_skipped    → 준비 중 안내 (Pinterest MVP)
 */

"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { useOnboardingGuard } from "@/hooks/use-onboarding-guard";
import { useMaleBetaBlock } from "@/hooks/use-male-beta-block";
import { ApiError, api } from "@/lib/api/fetch";
import {
  createIgAspiration,
  createPinterestAspiration,
} from "@/lib/api/aspiration";
import type {
  AspirationRunStatus,
  AspirationStartResponse,
} from "@/lib/types/aspiration";
import { LoadingSlides } from "@/components/sia/LoadingSlides";
import { TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";
import { TokenInsufficientModal } from "@/components/sigak/token-insufficient-modal";
import { MaleBetaComingSoon } from "@/components/sigak/male-beta-coming-soon";

const COST_ASPIRATION = 20;

type Tab = "ig" | "pinterest";
type Stage = "form" | "pending" | "error";

const FAILURE_COPY: Record<
  Exclude<AspirationRunStatus, "completed">,
  { title: string; body: string }
> = {
  failed_blocked: {
    title: "이 대상은 분석할 수 없어요",
    body: "분석 차단 요청이 들어온 대상이라 진행이 어려워요. 토큰은 환불됐어요.",
  },
  failed_private: {
    title: "비공개 계정이라 들여다볼 수 없었어요",
    body: "공개 상태인 다른 대상으로 다시 시도해 주세요. 토큰은 환불됐어요.",
  },
  failed_scrape: {
    title: "수집을 끝내지 못했어요",
    body: "보드가 비공개거나 핀이 부족할 수 있어요. 다른 대상으로 다시 시도해 주세요. 토큰은 환불됐어요.",
  },
  failed_skipped: {
    title: "입력 형식을 확인해 주세요",
    body: "공개 Pinterest 보드 URL 형식이어야 해요 (https://www.pinterest.com/유저/보드/). Instagram 은 핸들만 입력하시면 돼요.",
  },
};

export default function AspirationPage() {
  const router = useRouter();
  const { status: guardStatus } = useOnboardingGuard();
  // 남성 v1.1 베타 차단 (2026-04-27) — male 풀 미정합 영역
  const { checking: genderChecking, blocked: maleBlocked } = useMaleBetaBlock();

  const [tab, setTab] = useState<Tab>("ig");
  const [igInput, setIgInput] = useState("");
  const [pinterestInput, setPinterestInput] = useState("");
  const [stage, setStage] = useState<Stage>("form");
  const [balance, setBalance] = useState<number | null>(null);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [errorBlock, setErrorBlock] = useState<{
    title: string;
    body: string;
    action?: { label: string; href: string };
  } | null>(null);

  // 잔액 조회
  useEffect(() => {
    if (guardStatus !== "ready") return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.getBalance();
        if (!cancelled) setBalance(res.balance);
      } catch {
        if (!cancelled) setBalance(0);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [guardStatus]);

  // 입력 정제
  const normalizedHandle = useMemo(
    () => normalizeIgHandle(igInput),
    [igInput],
  );
  const normalizedBoard = useMemo(
    () => pinterestInput.trim(),
    [pinterestInput],
  );

  const igValid = normalizedHandle.length > 0;
  const pinterestValid = isPlausiblePinterestUrl(normalizedBoard);

  const lowBalance = balance !== null && balance < COST_ASPIRATION;
  // CTA enabled = input valid 만. 잔액 부족은 모달로 안내 (마케터 패턴).
  const canStart =
    stage === "form" && (tab === "ig" ? igValid : pinterestValid);

  async function handleStart(): Promise<void> {
    if (!canStart) return;
    // client-side 잔액 체크 — 부족 시 모달 노출 (server 호출 회피)
    if (balance !== null && balance < COST_ASPIRATION) {
      setShowTokenModal(true);
      return;
    }
    setErrorBlock(null);
    setStage("pending");

    try {
      let res: AspirationStartResponse;
      if (tab === "ig") {
        res = await createIgAspiration({ target_handle: normalizedHandle });
      } else {
        res = await createPinterestAspiration({ board_url: normalizedBoard });
      }

      if (res.status === "completed" && res.analysis_id) {
        router.replace(`/aspiration/${encodeURIComponent(res.analysis_id)}`);
        return;
      }

      const failure =
        FAILURE_COPY[res.status as Exclude<AspirationRunStatus, "completed">]
        ?? {
          title: "분석을 끝내지 못했어요",
          body: "잠시 후 다시 시도해 주세요. 토큰은 환불됐어요.",
        };
      setErrorBlock(failure);
      setStage("error");
    } catch (err) {
      handleStartError(err);
    }
  }

  function handleStartError(err: unknown): void {
    if (err instanceof ApiError) {
      if (err.status === 401) {
        router.replace("/auth/login");
        return;
      }
      if (err.status === 402) {
        // server-side 잔액 부족 (race condition) → 모달 노출
        setShowTokenModal(true);
        setStage("form");
        return;
      }
      if (err.status === 403) {
        setErrorBlock({
          title: "이 대상은 분석할 수 없어요",
          body: "분석 차단된 대상이에요.",
        });
        setStage("error");
        return;
      }
      if (err.status === 409) {
        setErrorBlock({
          title: "온보딩이 마무리되지 않았어요",
          body: "Sia와 짧게 이야기 나눠주시면 분석을 열어드릴게요.",
          action: { label: "Sia 만나러 가기", href: "/sia" },
        });
        setStage("error");
        return;
      }
      setErrorBlock({
        title: "분석을 시작하지 못했어요",
        body: err.message || "잠시 후 다시 시도해 주세요.",
      });
      setStage("error");
      return;
    }
    setErrorBlock({
      title: "연결이 잠깐 끊겼어요",
      body: "다시 시도해 주세요.",
    });
    setStage("error");
  }

  // ── 가드 대기 (onboarding + gender 체크)
  if (guardStatus !== "ready" || genderChecking) {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-hidden
      />
    );
  }

  // 남성 v1.1 차단 — 추구미 분석 풀 미정합 영역
  if (maleBlocked) {
    return <MaleBetaComingSoon featureName="추구미 분석" />;
  }

  if (stage === "pending") {
    return <LoadingSlides />;
  }

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
    >
      <TopBar backTarget="/" />

      <main className="flex-1" style={{ padding: "24px 24px 120px" }}>
        <Header balance={balance} />

        <TabSwitcher tab={tab} onChange={setTab} />

        {tab === "ig" ? (
          <IgInputSection
            value={igInput}
            onChange={setIgInput}
            normalized={normalizedHandle}
          />
        ) : (
          <PinterestInputSection
            value={pinterestInput}
            onChange={setPinterestInput}
            valid={pinterestValid}
          />
        )}

        {errorBlock && (
          <ErrorPanel
            title={errorBlock.title}
            body={errorBlock.body}
            action={errorBlock.action}
            onDismiss={() => {
              setErrorBlock(null);
              setStage("form");
            }}
          />
        )}

        <NoticeBlock />
      </main>

      <StickyCta
        balance={balance}
        canStart={canStart}
        lowBalance={lowBalance}
        onStart={handleStart}
        tab={tab}
        igValid={igValid}
        pinterestValid={pinterestValid}
      />

      <SiteFooter />

      {/* 토큰 부족 모달 (마케터 redesign/토큰부족_모달_1815.html) */}
      <TokenInsufficientModal
        open={showTokenModal}
        balance={balance ?? 0}
        required={COST_ASPIRATION}
        onCharge={() => router.push("/tokens/purchase?intent=aspiration")}
        onClose={() => setShowTokenModal(false)}
      />
    </div>
  );
}

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

function normalizeIgHandle(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";

  // URL 형태면 path 마지막 segment 추출
  const urlMatch = trimmed.match(/instagram\.com\/(?:p\/)?([^/?#]+)/i);
  if (urlMatch) {
    return urlMatch[1].replace(/^@/, "").toLowerCase();
  }

  // "@yuni" 또는 "yuni"
  return trimmed.replace(/^@/, "").toLowerCase();
}

function isPlausiblePinterestUrl(raw: string): boolean {
  const trimmed = raw.trim();
  if (!trimmed) return false;
  return /pinterest\.[a-z]+\//i.test(trimmed);
}

// ─────────────────────────────────────────────
//  Sub-views
// ─────────────────────────────────────────────

function Header({ balance }: { balance: number | null }) {
  return (
    <header style={{ marginBottom: 32 }}>
      <h1
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 24,
          fontWeight: 700,
          letterSpacing: "-0.022em",
          lineHeight: 1.42,
          color: "var(--color-ink)",
          wordBreak: "keep-all",
        }}
      >
        추구미 살펴보기
      </h1>
      <p
        className="font-sans"
        style={{
          margin: "10px 0 0",
          fontSize: 14,
          lineHeight: 1.65,
          color: "var(--color-mute)",
          letterSpacing: "-0.005em",
          wordBreak: "keep-all",
        }}
      >
        추구미에 부합하는 인스타 계정 및 핀터레스트를 알려주시면 유사도와 개선점을 알려드려요.
      </p>
      {balance !== null && balance < COST_ASPIRATION && (
        <div
          className="font-sans tabular-nums"
          style={{
            marginTop: 14,
            fontSize: 11,
            letterSpacing: "0.05em",
            color: "var(--color-mute-2)",
          }}
        >
          현재 잔액 {balance}토큰 · 1회 {COST_ASPIRATION} 토큰 필요
        </div>
      )}
    </header>
  );
}

// v1.5 — Pinterest 정식 활성화. devcake~pinterest-data-scraper 어댑터 +
// raw R2 보존 + matched_trends 스냅샷 패턴 적용 완료.
const PINTEREST_ENABLED = true;

function TabSwitcher({
  tab,
  onChange,
}: {
  tab: Tab;
  onChange: (t: Tab) => void;
}) {
  const items: { key: Tab; label: string; disabled: boolean }[] = [
    { key: "ig", label: "Instagram", disabled: false },
    { key: "pinterest", label: "Pinterest", disabled: !PINTEREST_ENABLED },
  ];
  return (
    <div
      role="tablist"
      style={{
        display: "flex",
        borderBottom: "1px solid var(--color-line)",
        marginBottom: 32,
      }}
    >
      {items.map((it) => {
        const active = it.key === tab;
        const disabled = it.disabled;
        return (
          <button
            key={it.key}
            type="button"
            role="tab"
            aria-selected={active}
            aria-disabled={disabled}
            disabled={disabled}
            onClick={() => {
              if (disabled) return;
              onChange(it.key);
            }}
            title={disabled ? "Pinterest 곧 만나요" : undefined}
            className="font-sans"
            style={{
              flex: 1,
              padding: "13px 0",
              background: "transparent",
              border: "none",
              borderBottom: active
                ? "1.5px solid var(--color-danger)"
                : "1.5px solid transparent",
              fontSize: 14,
              fontWeight: active ? 600 : 500,
              letterSpacing: "-0.008em",
              color: disabled
                ? "var(--color-mute-2)"
                : active
                  ? "var(--color-ink)"
                  : "var(--color-mute)",
              cursor: disabled ? "not-allowed" : "pointer",
              marginBottom: -1,
              opacity: disabled ? 0.55 : 1,
            }}
          >
            {it.label}
            {disabled && (
              <span
                className="font-sans"
                style={{
                  marginLeft: 6,
                  fontSize: 10,
                  fontWeight: 500,
                  color: "var(--color-mute-2)",
                  letterSpacing: "0.08em",
                }}
              >
                곧 만나요
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function IgInputSection({
  value,
  onChange,
  normalized,
}: {
  value: string;
  onChange: (v: string) => void;
  normalized: string;
}) {
  return (
    <section>
      <label
        htmlFor="ig-input"
        className="uppercase"
        style={{
          display: "block",
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          letterSpacing: "0.12em",
          color: "var(--color-mute)",
          marginBottom: 8,
        }}
      >
        INSTAGRAM 핸들
      </label>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          border: "1px solid var(--color-line-strong)",
          borderRadius: 12,
          overflow: "hidden",
          background: "rgba(0, 0, 0, 0.04)",
          transition: "border-color 0.2s ease",
        }}
      >
        <input
          id="ig-input"
          type="text"
          inputMode="url"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          placeholder="@yuni 또는 instagram.com/yuni"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="font-sans"
          style={{
            flex: 1,
            padding: "14px 16px",
            background: "transparent",
            border: "none",
            outline: "none",
            fontSize: 15,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        />
      </div>
      {normalized && (
        <p
          className="font-sans tabular-nums"
          style={{
            margin: "9px 0 0",
            fontSize: 12,
            color: "var(--color-mute)",
            letterSpacing: "-0.005em",
          }}
        >
          분석 대상: @{normalized}
        </p>
      )}
    </section>
  );
}

function PinterestInputSection({
  value,
  onChange,
  valid,
}: {
  value: string;
  onChange: (v: string) => void;
  valid: boolean;
}) {
  return (
    <section>
      <label
        htmlFor="pin-input"
        className="uppercase"
        style={{
          display: "block",
          fontFamily: "var(--font-mono)",
          fontSize: 10,
          letterSpacing: "0.12em",
          color: "var(--color-mute)",
          marginBottom: 8,
        }}
      >
        PINTEREST 보드 URL
      </label>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          border: "1px solid var(--color-line-strong)",
          borderRadius: 12,
          overflow: "hidden",
          background: "rgba(0, 0, 0, 0.04)",
          transition: "border-color 0.2s ease",
        }}
      >
        <input
          id="pin-input"
          type="url"
          inputMode="url"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck={false}
          placeholder="pinterest.com/your-name/board-name"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="font-sans"
          style={{
            flex: 1,
            padding: "14px 16px",
            background: "transparent",
            border: "none",
            outline: "none",
            fontSize: 15,
            color: "var(--color-ink)",
            letterSpacing: "-0.005em",
          }}
        />
      </div>
      {value.trim() && !valid && (
        <p
          className="font-sans"
          style={{
            margin: "8px 0 0",
            fontSize: 11,
            color: "var(--color-danger)",
            letterSpacing: "-0.005em",
          }}
        >
          Pinterest 보드 URL 형식으로 입력해 주세요.
        </p>
      )}
    </section>
  );
}

function ErrorPanel({
  title,
  body,
  action,
  onDismiss,
}: {
  title: string;
  body: string;
  action?: { label: string; href: string };
  onDismiss: () => void;
}) {
  return (
    <div
      role="alert"
      style={{
        marginTop: 24,
        padding: "16px 18px",
        borderTop: "1px solid var(--color-danger)",
        background: "rgba(163, 45, 45, 0.04)",
      }}
    >
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 13,
          fontWeight: 600,
          color: "var(--color-ink)",
          letterSpacing: "-0.005em",
        }}
      >
        {title}
      </p>
      <p
        className="font-sans"
        style={{
          margin: "6px 0 12px",
          fontSize: 13,
          lineHeight: 1.6,
          color: "var(--color-ink)",
          letterSpacing: "-0.005em",
        }}
      >
        {body}
      </p>
      <div style={{ display: "flex", gap: 14 }}>
        {action && (
          <Link
            href={action.href}
            className="font-sans"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-ink)",
              textDecoration: "underline",
            }}
          >
            {action.label}
          </Link>
        )}
        <button
          type="button"
          onClick={onDismiss}
          className="font-sans"
          style={{
            background: "transparent",
            border: "none",
            padding: 0,
            color: "var(--color-mute)",
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          닫기
        </button>
      </div>
    </div>
  );
}

function NoticeBlock() {
  return (
    <div
      style={{
        marginTop: 28,
        padding: "16px 18px",
        background: "rgba(0, 0, 0, 0.04)",
        border: "1px solid var(--color-line)",
        borderRadius: 14,
      }}
    >
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 12.5,
          color: "var(--color-mute)",
          lineHeight: 1.75,
          letterSpacing: "-0.005em",
          wordBreak: "keep-all",
        }}
      >
        공개 계정만 살펴볼 수 있어요. 비공개나 차단 대상은 토큰이 환불됩니다. 한 번 살펴본 대상도 시점이 다르면 결과가 달라질 수 있어요.
      </p>
    </div>
  );
}

function StickyCta({
  balance,
  canStart,
  lowBalance,
  onStart,
  tab,
  igValid,
  pinterestValid,
}: {
  balance: number | null;
  canStart: boolean;
  lowBalance: boolean;
  onStart: () => void;
  tab: Tab;
  igValid: boolean;
  pinterestValid: boolean;
}) {
  const inputValid = tab === "ig" ? igValid : pinterestValid;
  const labelMain = "추구미 살펴보기 →";
  // CTA disabled 시는 input 만 invalid 케이스. 잔액 부족은 모달이 처리.
  const labelDisabled =
    !inputValid
      ? tab === "ig"
        ? "Instagram 핸들을 입력해 주세요"
        : "Pinterest 보드 URL을 입력해 주세요"
      : labelMain;

  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        left: 0,
        right: 0,
        background: "var(--color-paper)",
        padding: "16px 24px 24px",
        borderTop: "1px solid var(--color-line)",
      }}
    >
      <button
        type="button"
        onClick={onStart}
        disabled={!canStart}
        className="font-sans"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          width: "100%",
          padding: "17px 24px",
          background: canStart ? "var(--color-ink)" : "var(--color-line-strong)",
          color: canStart ? "var(--color-paper)" : "#fff",
          border: "none",
          borderRadius: 100,
          fontSize: 15,
          fontWeight: 600,
          letterSpacing: "-0.012em",
          cursor: canStart ? "pointer" : "not-allowed",
          transition: "all 0.25s ease",
        }}
      >
        {canStart ? labelMain : labelDisabled}
      </button>

      {/* 토큰 비용 표시 (CTA 아래 dot + 라벨) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 5,
          marginTop: 12,
          opacity: canStart ? 1 : 0,
          transition: "opacity 0.25s ease",
        }}
        aria-hidden={!canStart}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: "var(--color-danger)",
          }}
        />
        <span
          className="tabular-nums"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: 11,
            color: "var(--color-mute)",
            letterSpacing: "0.08em",
          }}
        >
          {COST_ASPIRATION}토큰
        </span>
      </div>
    </div>
  );
}
