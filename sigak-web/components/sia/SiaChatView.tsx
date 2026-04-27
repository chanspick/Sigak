/**
 * SiaChatView — Sia 대화 오케스트레이터.
 *
 * 구성:
 *   SiaTopBar (progress 1px hairline + 30초 이하 countdown)
 *   ─────────────────────────────────────────
 *   SiaStream (메시지 리스트 + SiaDots pending)
 *   ─────────────────────────────────────────
 *   SiaErrorBanner (error 발생 시)
 *   SiaInputDock (주관식 입력)
 *
 * 데이터 흐름:
 *   useSiaSession 훅이 state + send/resetError 노출.
 *   SiaMessage (14 타입) → SiaTurn (legacy { role, content }) 매핑하여 SiaStream 전달.
 *   SiaStream 내부 parseSiaMessage 가 content 마침표/하이픈 split (M1 결합 출력 자동 처리).
 *
 * 세션 종료 시:
 *   useSiaSession 의 reportId 세팅 → /sia/done?report={id} replace.
 *   (Phase H5 완료 전까지 reportId = sessionId fallback)
 */

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { SiaTopBar } from "./SiaTopBar";
import { SiaStream, type SiaStreamHandle } from "./SiaStream";
import { SiaInputDock } from "./SiaInputDock";
import { SiaErrorBanner } from "./SiaErrorBanner";
import { useSiaSession } from "@/hooks/useSiaSession";
import type { SiaTurn } from "@/lib/types/sia";

export function SiaChatView() {
  const router = useRouter();
  const {
    status,
    messages,
    countdownSeconds,
    progressPercent,
    errorCode,
    reportId,
    send,
    endChat,
    resetError,
  } = useSiaSession();
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const streamRef = useRef<SiaStreamHandle | null>(null);

  // textarea focus 시 스크롤 컨테이너를 하단으로 보정.
  // visualViewport resize 가 자동으로도 작동하지만, iOS Safari 에서 focus
  // 타이밍이 visualViewport 변화보다 먼저 일어나는 케이스가 있어 이중 보장.
  // 300ms 지연 = 키보드 애니메이션 완료 대기.
  const handleInputFocus = () => {
    window.setTimeout(() => {
      streamRef.current?.scrollToBottom();
    }, 300);
  };

  // SiaMessage[] → SiaTurn[] (SiaStream 의 legacy prop shape)
  const turns: SiaTurn[] = useMemo(
    () => messages.map((m) => ({ role: m.role, content: m.content })),
    [messages],
  );

  // 세션 완료 시 /sia/done 으로 전환
  useEffect(() => {
    if (status !== "completed") return;
    if (!reportId) return;
    router.replace(`/sia/done?report=${encodeURIComponent(reportId)}`);
  }, [status, reportId, router]);

  const pending = status === "sending";
  const inputDisabled =
    pending ||
    status === "booting" ||
    status === "completed" ||
    status === "error";

  const handleSend = async (text: string): Promise<void> => {
    await send(text);
  };

  // 대화 끝내기 버튼 활성화 조건 — 유저가 최소 1턴 발화한 뒤에만 (지시서 A3)
  const hasUserTurn = useMemo(
    () => messages.some((m) => m.role === "user"),
    [messages],
  );
  const canEnd =
    status === "ready" && hasUserTurn && !pending && !errorCode;

  async function handleConfirmEnd() {
    setShowEndConfirm(false);
    await endChat("exit");
  }

  return (
    <div
      className="flex flex-col"
      style={{
        // 100dvh = dynamic viewport height. 키보드 올라올 때 축소되어
        // 스크롤 영역이 정상 계산됨. 100vh 는 모바일에서 주소창 포함 고정치라
        // 키보드가 화면을 덮어도 그대로라 가려지는 문제 발생.
        minHeight: "100dvh",
        background: "var(--color-paper)",
      }}
    >
      {/* TopBar + 끝내기 버튼 overlay — SiaTopBar 자체는 수정 금지 */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 20,
          background: "var(--color-paper)",
        }}
      >
        <div style={{ position: "relative" }}>
          <SiaTopBar
            progressPercent={progressPercent}
            remainingSeconds={countdownSeconds}
          />
          {canEnd && (
            <button
              type="button"
              onClick={() => setShowEndConfirm(true)}
              className="font-sans"
              aria-label="대화 끝내기"
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                height: 52,
                paddingLeft: 20,
                paddingRight: 14,
                background: "transparent",
                color: "var(--color-ink)",
                border: "none",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 500,
                letterSpacing: "-0.005em",
                display: "flex",
                alignItems: "center",
                opacity: 0.55,
                zIndex: 21,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = "1";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = "0.55";
              }}
            >
              끝내기
            </button>
          )}
        </div>
      </div>

      <main className="flex-1 overflow-hidden min-h-0">
        <SiaStream ref={streamRef} messages={turns} pending={pending} />
      </main>

      {errorCode && (
        <SiaErrorBanner code={errorCode} onRetry={resetError} />
      )}

      <SiaInputDock
        onSend={handleSend}
        disabled={inputDisabled}
        onFocus={handleInputFocus}
        placeholder={
          status === "booting"
            ? "Sia가 준비하는 중이에요"
            : status === "sending"
              ? "Sia가 생각하는 중이에요"
              : status === "completed"
                ? "대화가 끝났어요"
                : "Sia에게 답하기"
        }
      />

      {/* 끝내기 확인 모달 */}
      {showEndConfirm && (
        <EndConfirmModal
          onConfirm={handleConfirmEnd}
          onCancel={() => setShowEndConfirm(false)}
        />
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  EndConfirmModal — Sia 대화 끝내기 확인
// ─────────────────────────────────────────────

interface EndConfirmModalProps {
  onConfirm: () => void;
  onCancel: () => void;
}

function EndConfirmModal({ onConfirm, onCancel }: EndConfirmModalProps) {
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onCancel]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="sia-end-confirm-title"
      className="animate-fade-in"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 28px",
        background: "rgba(0, 0, 0, 0.4)",
      }}
    >
      <div
        onClick={onCancel}
        aria-hidden
        style={{ position: "absolute", inset: 0 }}
      />
      <div
        style={{
          position: "relative",
          width: "100%",
          maxWidth: 360,
          background: "var(--color-paper)",
          padding: "28px 24px 22px",
          border: "1px solid var(--color-line)",
          borderRadius: 14,
        }}
      >
        <h2
          id="sia-end-confirm-title"
          className="font-serif"
          style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 700,
            lineHeight: 1.35,
            letterSpacing: "-0.022em",
            color: "var(--color-ink)",
            textAlign: "center",
          }}
        >
          여기까지 할까요
          <span style={{ color: "var(--color-ember)" }}>?</span>
        </h2>
        <p
          className="font-sans"
          style={{
            margin: "10px 0 0",
            fontSize: 13.5,
            lineHeight: 1.6,
            letterSpacing: "-0.005em",
            color: "var(--color-mute)",
            textAlign: "center",
          }}
        >
          지금까지 나눈 얘기로 정리해드릴게요.
        </p>

        <div
          style={{
            marginTop: 24,
            display: "flex",
            gap: 8,
          }}
        >
          <button
            type="button"
            onClick={onCancel}
            className="font-sans"
            style={{
              flex: 1,
              padding: "14px 16px",
              background: "transparent",
              color: "var(--color-mute)",
              border: "1.5px solid var(--color-line)",
              borderRadius: 100,
              fontSize: 14,
              fontWeight: 500,
              letterSpacing: "-0.01em",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            더 얘기할게요
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="font-sans"
            style={{
              flex: 1,
              padding: "14px 16px",
              background: "var(--color-ink)",
              color: "var(--color-paper)",
              border: "none",
              borderRadius: 100,
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: "-0.012em",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            끝낼게요
          </button>
        </div>
      </div>
    </div>
  );
}
