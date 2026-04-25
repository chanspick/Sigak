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
import { PrimaryButton, TopBar } from "@/components/ui/sigak";
import { SiteFooter } from "@/components/sigak/site-footer";

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

  const [tab, setTab] = useState<Tab>("ig");
  const [igInput, setIgInput] = useState("");
  const [pinterestInput, setPinterestInput] = useState("");
  const [stage, setStage] = useState<Stage>("form");
  const [balance, setBalance] = useState<number | null>(null);
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
  const canStart =
    stage === "form"
    && balance !== null
    && balance >= COST_ASPIRATION
    && (tab === "ig" ? igValid : pinterestValid);

  async function handleStart(): Promise<void> {
    if (!canStart) return;
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
        setErrorBlock({
          title: "토큰이 부족해요",
          body: "추구미 분석은 한 번에 20개가 필요해요.",
          action: { label: "토큰 충전하기", href: "/tokens/purchase" },
        });
        setStage("error");
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

  // ── 가드 대기
  if (guardStatus !== "ready") {
    return (
      <div
        style={{ minHeight: "100vh", background: "var(--color-paper)" }}
        aria-hidden
      />
    );
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
    <header style={{ marginBottom: 24 }}>
      <h1
        className="font-serif"
        style={{
          margin: 0,
          fontSize: 28,
          fontWeight: 400,
          letterSpacing: "-0.01em",
          lineHeight: 1.25,
        }}
      >
        추구미 분석
      </h1>
      <p
        className="font-sans"
        style={{
          margin: "10px 0 0",
          fontSize: 13,
          lineHeight: 1.6,
          color: "var(--color-mute)",
          letterSpacing: "-0.005em",
        }}
      >
        따라가고 싶은 결을 놓고, 지금의 본인과 어떻게 다른지 짚어드릴게요.
      </p>
      {balance !== null && (
        <div
          className="font-sans tabular-nums"
          style={{
            marginTop: 16,
            fontSize: 11,
            letterSpacing: "0.05em",
            color: "var(--color-mute-2)",
          }}
        >
          토큰 {balance}개 보유  ·  1회 20 토큰
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
        borderBottom: "1px solid rgba(0, 0, 0, 0.12)",
        marginBottom: 24,
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
              padding: "12px 0 14px",
              background: "transparent",
              border: "none",
              borderBottom: active
                ? "2px solid var(--color-ink)"
                : "2px solid transparent",
              fontSize: 13,
              fontWeight: active ? 600 : 500,
              letterSpacing: "0.3px",
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
        className="font-sans"
        style={{
          display: "block",
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: "0.05em",
          color: "var(--color-mute)",
          marginBottom: 10,
        }}
      >
        INSTAGRAM 핸들
      </label>
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
          width: "100%",
          padding: "14px 14px",
          fontSize: 15,
          background: "transparent",
          border: "1px solid rgba(0, 0, 0, 0.25)",
          borderRadius: 0,
          color: "var(--color-ink)",
          letterSpacing: "-0.005em",
        }}
      />
      {normalized && (
        <p
          className="font-sans tabular-nums"
          style={{
            margin: "8px 0 0",
            fontSize: 11,
            color: "var(--color-mute-2)",
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
        className="font-sans"
        style={{
          display: "block",
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: "0.05em",
          color: "var(--color-mute)",
          marginBottom: 10,
        }}
      >
        PINTEREST 보드 URL
      </label>
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
          width: "100%",
          padding: "14px 14px",
          fontSize: 15,
          background: "transparent",
          border: "1px solid rgba(0, 0, 0, 0.25)",
          borderRadius: 0,
          color: "var(--color-ink)",
          letterSpacing: "-0.005em",
        }}
      />
      {value.trim() && !valid && (
        <p
          className="font-sans"
          style={{
            margin: "8px 0 0",
            fontSize: 11,
            color: "var(--color-danger)",
          }}
        >
          Pinterest 보드 URL 형식으로 입력해 주세요.
        </p>
      )}
      <p
        className="font-sans"
        style={{
          margin: "12px 0 0",
          fontSize: 11,
          color: "var(--color-mute-2)",
          lineHeight: 1.6,
        }}
      >
        Pinterest 채널은 곧 열어둘 예정이에요. 지금은 Instagram이 정확도가 더 높아요.
      </p>
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
      className="font-sans"
      style={{
        marginTop: 28,
        padding: "16px 18px",
        background: "rgba(0, 0, 0, 0.03)",
        fontSize: 12,
        lineHeight: 1.7,
        color: "var(--color-mute)",
        letterSpacing: "-0.005em",
      }}
    >
      <div>공개 계정만 분석할 수 있어요. 비공개나 차단 대상은 토큰이 환불됩니다.</div>
      <div>한 번 분석한 대상도 시점이 다르면 결과가 달라질 수 있어요.</div>
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
  const labelMain = "분석 시작 (20 토큰)";
  const labelDisabled =
    !inputValid
      ? tab === "ig"
        ? "Instagram 핸들을 입력해 주세요"
        : "Pinterest 보드 URL을 입력해 주세요"
      : balance === null
        ? "잔액 확인 중"
        : lowBalance
          ? "토큰이 부족해요"
          : labelMain;

  return (
    <div
      style={{
        position: "sticky",
        bottom: 0,
        left: 0,
        right: 0,
        background: "var(--color-paper)",
        padding: "12px 24px 24px",
        borderTop: "1px solid rgba(0, 0, 0, 0.08)",
      }}
    >
      {lowBalance && (
        <Link
          href="/tokens/purchase"
          className="font-sans"
          style={{
            display: "block",
            textAlign: "center",
            fontSize: 12,
            color: "var(--color-ink)",
            textDecoration: "underline",
            marginBottom: 12,
          }}
        >
          토큰 충전하러 가기
        </Link>
      )}
      <PrimaryButton
        type="button"
        onClick={onStart}
        disabled={!canStart}
        disabledLabel={labelDisabled}
      >
        {labelMain}
      </PrimaryButton>
    </div>
  );
}
