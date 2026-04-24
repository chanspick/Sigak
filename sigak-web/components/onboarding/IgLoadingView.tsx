"use client";

/**
 * IgLoadingView — IG 분석 대기 화면.
 *
 * 상태별 렌더:
 *   pending        — "@{username}님 피드 찾고 있어요" + 스켈레톤
 *   pending_vision — "@{username}님 피드를 살피고 있어요" + preview 그리드
 *   success        — "준비됐어요" + preview + "잠시 후 Sia 가 말을 걸어요"
 *   private        — "비공개 계정이라 피드는 못 봤어요" + 괜찮다는 안내
 *   failed         — "피드를 못 가져왔어요" + 괜찮다는 안내
 *   skipped        — "IG 없이 진행할게요"
 *   error          — 폴링 실패 배너 + 재시도 CTA
 *
 * 360px 제약 — 가로 스크롤 0. 그리드는 3열 (작은 썸네일) or 2열 (큰 썸네일).
 */

import Image from "next/image";
import { useMemo } from "react";

import type { IgFetchStatus } from "@/lib/types/mvp";

import type { IgPollError, UseIgStatusResult } from "@/hooks/useIgStatus";


export interface IgLoadingViewProps {
  result: UseIgStatusResult;
  /** 폴링 에러 발생 시 재시도 콜백. (상위 페이지에서 재마운트 or refetch 유도) */
  onRetry?: () => void;
  /** 수동으로 Sia 진입 (최종 상태 도달 시 상위 페이지가 자동 라우팅 — 폴백용). */
  onContinue?: () => void;
}


export function IgLoadingView({
  result,
  onRetry,
  onContinue,
}: IgLoadingViewProps) {
  const { status, previewUrls, username, analyzed, error, elapsedSeconds } = result;

  const handleLabel = username ? `@${username}` : "피드";

  const heading = useMemo(
    () => _headingFor(status, handleLabel, analyzed),
    [status, handleLabel, analyzed],
  );
  const subcopy = useMemo(
    () => _subcopyFor(status, elapsedSeconds),
    [status, elapsedSeconds],
  );

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: "var(--color-paper)" }}
    >
      <main
        className="flex-1 overflow-hidden min-h-0"
        style={{
          paddingLeft: 20,
          paddingRight: 20,
          paddingTop: 80,
          paddingBottom: 40,
        }}
      >
        {/* 본문 상단 카피 */}
        <h1
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 400,
            lineHeight: 1.35,
            letterSpacing: "-0.01em",
            color: "var(--color-ink)",
          }}
          data-testid="ig-loading-heading"
        >
          {heading}
        </h1>
        <p
          className="font-sans"
          style={{
            margin: "12px 0 0",
            fontSize: 13,
            lineHeight: 1.6,
            letterSpacing: "-0.005em",
            color: "var(--color-mute)",
          }}
          data-testid="ig-loading-subcopy"
        >
          {subcopy}
        </p>

        {/* preview 그리드 or 스켈레톤 */}
        <div style={{ marginTop: 32 }}>
          {previewUrls.length > 0 ? (
            <PreviewGrid urls={previewUrls} />
          ) : (
            <SkeletonGrid />
          )}
        </div>

        {/* 진행 바 — pending / pending_vision 단계에서만 */}
        {(status === "pending" || status === "pending_vision") && !error && (
          <ProgressHint elapsedSeconds={elapsedSeconds} />
        )}

        {/* 에러 배너 */}
        {error && (
          <ErrorBanner error={error} onRetry={onRetry} />
        )}

        {/* 최종 상태 진입 안내 (상위 페이지가 자동 라우팅. 수동 폴백 버튼) */}
        {!error && _isTerminal(status) && onContinue && (
          <ContinueCTA onContinue={onContinue} status={status} />
        )}
      </main>
    </div>
  );
}


// ─────────────────────────────────────────────
//  Subcomponents
// ─────────────────────────────────────────────

function PreviewGrid({ urls }: { urls: string[] }) {
  // 360px 모바일 기준 3 columns × 4px gap = thumbnail ~108px
  const gridUrls = urls.slice(0, 6);
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 4,
      }}
      data-testid="ig-preview-grid"
    >
      {gridUrls.map((url, idx) => (
        <div
          key={`${url.slice(0, 40)}-${idx}`}
          style={{
            aspectRatio: "1 / 1",
            position: "relative",
            overflow: "hidden",
            background: "var(--color-line)",
          }}
        >
          {/* Instagram CDN URL — Next.js Image next.config 외부 도메인 필요 */}
          {/* safer: plain img 로 domain 제한 우회 */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt=""
            loading="lazy"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              display: "block",
            }}
          />
        </div>
      ))}
    </div>
  );
}


function SkeletonGrid() {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(3, 1fr)",
        gap: 4,
      }}
      data-testid="ig-skeleton-grid"
    >
      {Array.from({ length: 6 }).map((_, idx) => (
        <div
          key={idx}
          className="animate-pulse-opacity"
          style={{
            aspectRatio: "1 / 1",
            background: "var(--color-line)",
          }}
        />
      ))}
    </div>
  );
}


function ProgressHint({ elapsedSeconds }: { elapsedSeconds: number }) {
  // 15s 미만: 아무 텍스트 없음. 15-45s: "곧 끝나요". 45s+: "조금만 더요".
  let hint = "";
  if (elapsedSeconds >= 45) {
    hint = "조금만 더요";
  } else if (elapsedSeconds >= 15) {
    hint = "곧 끝나요";
  }
  if (!hint) return null;

  return (
    <p
      className="font-sans"
      style={{
        margin: "24px 0 0",
        fontSize: 12,
        letterSpacing: "-0.005em",
        color: "var(--color-mute-2)",
      }}
      data-testid="ig-progress-hint"
    >
      {hint}
    </p>
  );
}


function ErrorBanner({
  error,
  onRetry,
}: {
  error: IgPollError;
  onRetry?: () => void;
}) {
  const message = _errorMessage(error);
  return (
    <div
      style={{
        marginTop: 32,
        padding: "14px 16px",
        background: "rgba(163, 45, 45, 0.08)",
        border: "1px solid rgba(163, 45, 45, 0.25)",
      }}
      data-testid="ig-error-banner"
    >
      <p
        className="font-sans"
        style={{
          margin: 0,
          fontSize: 13,
          lineHeight: 1.5,
          letterSpacing: "-0.005em",
          color: "var(--color-danger)",
        }}
      >
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="font-sans"
          style={{
            marginTop: 12,
            background: "transparent",
            color: "var(--color-danger)",
            border: "1px solid var(--color-danger)",
            padding: "8px 16px",
            fontSize: 12,
            fontWeight: 600,
            letterSpacing: "0.3px",
            cursor: "pointer",
            borderRadius: 0,
          }}
        >
          다시 시도
        </button>
      )}
    </div>
  );
}


function ContinueCTA({
  onContinue,
  status,
}: {
  onContinue: () => void;
  status: IgFetchStatus;
}) {
  const label =
    status === "success"
      ? "Sia 대화 시작하기"
      : "Sia 대화로 바로 가기";
  return (
    <div style={{ marginTop: 40, textAlign: "center" }}>
      <button
        type="button"
        onClick={onContinue}
        className="font-sans"
        style={{
          width: "100%",
          height: 48,
          background: "var(--color-ink)",
          color: "var(--color-paper)",
          border: "none",
          borderRadius: 0,
          fontSize: 14,
          fontWeight: 600,
          letterSpacing: "0.3px",
          cursor: "pointer",
        }}
        data-testid="ig-continue-cta"
      >
        {label}
      </button>
    </div>
  );
}


// ─────────────────────────────────────────────
//  Copy resolvers — 페르소나 B 친밀체
// ─────────────────────────────────────────────

function _headingFor(
  status: IgFetchStatus,
  handleLabel: string,
  analyzed: boolean,
): string {
  switch (status) {
    case "pending":
      return `${handleLabel}님 피드 찾고 있어요`;
    case "pending_vision":
      return `${handleLabel}님 피드를 살피고 있어요`;
    case "success":
      return analyzed
        ? "다 봤어요"
        : `${handleLabel}님 피드 읽었어요`;
    case "private":
      return "비공개 계정이네요";
    case "failed":
      return "피드를 못 가져왔어요";
    case "skipped":
      return "IG 없이 진행할게요";
    default:
      return "준비 중이에요";
  }
}


function _subcopyFor(
  status: IgFetchStatus,
  elapsedSeconds: number,
): string {
  switch (status) {
    case "pending":
      return "인스타그램에서 피드를 찾아볼게요. 잠깐이면 돼요.";
    case "pending_vision":
      return "이제 사진들을 같이 보는 중이에요.";
    case "success":
      return "잠시 후 Sia 가 말을 걸어요.";
    case "private":
      return "공개 계정만 자동으로 읽을 수 있어요. 괜찮아요, 대화에서 더 정확해져요.";
    case "failed":
      return "네트워크 오류거나 계정을 못 찾았어요. 괜찮아요, 대화로 바로 넘어갈게요.";
    case "skipped":
      return "지금은 대화부터 시작할게요.";
    default:
      return "";
  }
}


function _errorMessage(error: IgPollError): string {
  switch (error) {
    case "auth":
      return "로그인이 만료됐어요. 다시 로그인해 주세요.";
    case "network":
      return "인터넷 연결을 확인해 주세요.";
    case "timeout":
      // 자동 폴백 예정 — 유저는 Sia 로 넘어가는 걸 인지만 하면 됨.
      return "잠깐 연결이 늦어지네요. Sia 로 넘어갈게요.";
    case "server":
    default:
      return "분석 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.";
  }
}


function _isTerminal(status: IgFetchStatus): boolean {
  return (
    status === "success" ||
    status === "private" ||
    status === "failed" ||
    status === "skipped"
  );
}
