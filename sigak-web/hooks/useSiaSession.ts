/**
 * useSiaSession — Sia 대화 세션 오케스트레이션 훅.
 *
 * 책임:
 *   - 마운트 시 /chat/start 호출 (세션 생성 + 오프닝 수신)
 *   - 카운트다운 1초 tick (5분 시작, 로컬 감산 — 서버 미지원)
 *   - 만료 시 /chat/end 자동 호출 (reason="timeout")
 *   - 유저 메시지 송신 + Sia 응답 수신 (optimistic append)
 *   - 에러 4종 분류 (network/timeout/server/auth/expired)
 *   - 세션 종료 시 report_id 반환 (Phase H5 완료 전까지 sessionId 로 fallback)
 *
 * 설계 주석:
 *   - 세션 resume 불가 (백엔드 /active 엔드포인트 미존재). 새로고침 = 새 세션.
 *   - progress_percent 백엔드 미지원 — 로컬 계산 (turnCount / MAX_TURNS * 100).
 *   - M1 결합 출력 = useState 에 single SiaMessage (content 전체 문자열).
 *     SiaStream 내부 parseSiaMessage 가 마침표 기준 split 하여 렌더.
 *
 * Phase H5 완료 시 교체 지점:
 *   - MAX_TURNS 기반 progress → server 의 progress_percent 직접 사용
 *   - countdown 로컬 감산 → server countdown_seconds 동기화
 *   - report_id = 마지막 SiaSendResult 응답의 report_id 직접 사용
 */

"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import {
  SiaApiError,
  type SiaEndReason,
  type SiaErrorCode,
  endSiaChat,
  sendSiaMessage,
  startSiaChat,
} from "@/lib/api/sia";
import type { SiaMessage } from "@/lib/types/sia";

// ─────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────

const INITIAL_COUNTDOWN_SECONDS = 300;

/** Phase H5 완료 전 임시 — 14 턴을 100%로 간주하여 progress 계산. */
const MAX_TURNS_FOR_PROGRESS = 14;

// ─────────────────────────────────────────────
//  State
// ─────────────────────────────────────────────

export type SiaSessionStatus =
  | "idle"
  | "booting"
  | "ready"
  | "sending"
  | "completed"
  | "error";

export interface SiaSessionState {
  status: SiaSessionStatus;
  sessionId: string | null;
  messages: SiaMessage[];
  countdownSeconds: number;
  progressPercent: number;
  turnCount: number;
  errorCode: SiaErrorCode | null;
  reportId: string | null;
}

type SiaAction =
  | { type: "BOOT" }
  | {
      type: "BOOT_DONE";
      sessionId: string;
      openingMessage: string;
      turnCount: number;
    }
  | { type: "SEND_START"; userMessage: SiaMessage }
  | {
      type: "SEND_DONE";
      assistantMessage: string;
      turnCount: number;
      isComplete: boolean;
    }
  | { type: "END_DONE"; reportId: string | null }
  | { type: "ERROR"; code: SiaErrorCode }
  | { type: "RESET_ERROR" }
  | { type: "COUNTDOWN_TICK" };

const INITIAL: SiaSessionState = {
  status: "idle",
  sessionId: null,
  messages: [],
  countdownSeconds: INITIAL_COUNTDOWN_SECONDS,
  progressPercent: 0,
  turnCount: 0,
  errorCode: null,
  reportId: null,
};

function progressFromTurns(turns: number): number {
  if (turns <= 0) return 0;
  if (turns >= MAX_TURNS_FOR_PROGRESS) return 100;
  return Math.round((turns / MAX_TURNS_FOR_PROGRESS) * 100);
}

function makeMessage(
  role: "sia" | "user",
  content: string,
  suffix: string,
): SiaMessage {
  return {
    id: `${role}-${Date.now()}-${suffix}`,
    role,
    content,
    msg_type: null,
    created_at: new Date().toISOString(),
  };
}

function reducer(state: SiaSessionState, action: SiaAction): SiaSessionState {
  switch (action.type) {
    case "BOOT":
      return { ...INITIAL, status: "booting" };

    case "BOOT_DONE": {
      const opening = makeMessage("sia", action.openingMessage, "open");
      return {
        ...state,
        status: "ready",
        sessionId: action.sessionId,
        messages: [opening],
        turnCount: action.turnCount,
        progressPercent: progressFromTurns(action.turnCount),
        errorCode: null,
      };
    }

    case "SEND_START":
      return {
        ...state,
        status: "sending",
        messages: [...state.messages, action.userMessage],
        errorCode: null,
      };

    case "SEND_DONE": {
      const assistant = makeMessage(
        "sia",
        action.assistantMessage,
        `t${action.turnCount}`,
      );
      return {
        ...state,
        status: action.isComplete ? "completed" : "ready",
        messages: [...state.messages, assistant],
        turnCount: action.turnCount,
        progressPercent: progressFromTurns(action.turnCount),
      };
    }

    case "END_DONE":
      return {
        ...state,
        status: "completed",
        reportId: action.reportId,
        countdownSeconds: 0,
      };

    case "ERROR":
      return { ...state, status: "error", errorCode: action.code };

    case "RESET_ERROR":
      // error 전 status 로 자동 복원하지 않고 ready 로. send 재시도는 호출부가 결정.
      return state.sessionId
        ? { ...state, status: "ready", errorCode: null }
        : { ...state, errorCode: null };

    case "COUNTDOWN_TICK":
      if (state.countdownSeconds <= 0) return state;
      return { ...state, countdownSeconds: state.countdownSeconds - 1 };

    default:
      return state;
  }
}

// ─────────────────────────────────────────────
//  Hook
// ─────────────────────────────────────────────

export interface UseSiaSessionResult extends SiaSessionState {
  send: (text: string) => Promise<void>;
  /** 유저 명시 종료 (reason="exit") 또는 호출부 커스텀 사유. 중복 호출 방지. */
  endChat: (reason?: SiaEndReason) => Promise<void>;
  resetError: () => void;
}

export function useSiaSession(): UseSiaSessionResult {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const bootedRef = useRef(false);
  const endFiredRef = useRef(false);

  // ── 마운트 시 /start 호출 (한 번만) ──
  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;

    let cancelled = false;
    dispatch({ type: "BOOT" });

    startSiaChat()
      .then((res) => {
        if (cancelled) return;
        dispatch({
          type: "BOOT_DONE",
          sessionId: res.sessionId,
          openingMessage: res.openingMessage,
          turnCount: res.turnCount,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        const code: SiaErrorCode =
          err instanceof SiaApiError ? err.code : "server";
        dispatch({ type: "ERROR", code });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // ── 카운트다운 1초 tick (ready / sending 상태에서만) ──
  useEffect(() => {
    if (state.status !== "ready" && state.status !== "sending") return;
    const id = setInterval(() => dispatch({ type: "COUNTDOWN_TICK" }), 1000);
    return () => clearInterval(id);
  }, [state.status]);

  // ── 만료 시 자동 /end (reason="timeout") ──
  useEffect(() => {
    if (state.countdownSeconds > 0) return;
    if (!state.sessionId) return;
    if (endFiredRef.current) return;
    if (state.status === "completed" || state.status === "error") return;

    endFiredRef.current = true;
    endSiaChat({ sessionId: state.sessionId, reason: "timeout" })
      .then((res) => {
        // 백엔드가 현재 report_id 반환하지 않으므로 sessionId 를 임시 reportId 로 사용.
        // Phase H5 완료 시 res 에서 실 report_id 수신 예정.
        dispatch({
          type: "END_DONE",
          reportId: res.sessionId,
        });
      })
      .catch((err) => {
        const code: SiaErrorCode =
          err instanceof SiaApiError ? err.code : "server";
        // expired 는 이미 종료 상태이므로 completed 로 처리
        if (code === "expired") {
          dispatch({ type: "END_DONE", reportId: state.sessionId });
        } else {
          dispatch({ type: "ERROR", code });
        }
      });
  }, [
    state.countdownSeconds,
    state.sessionId,
    state.status,
  ]);

  // ── 유저 메시지 전송 ──
  const send = useCallback(
    async (text: string) => {
      if (!state.sessionId) return;
      if (state.status === "sending" || state.status === "completed") return;
      if (state.status === "error") return;

      const trimmed = text.trim();
      if (!trimmed) return;

      const userMsg = makeMessage("user", trimmed, `u${state.turnCount}`);
      dispatch({ type: "SEND_START", userMessage: userMsg });

      try {
        const res = await sendSiaMessage({
          sessionId: state.sessionId,
          text: trimmed,
        });
        dispatch({
          type: "SEND_DONE",
          assistantMessage: res.assistantMessage,
          turnCount: res.turnCount,
          isComplete: res.isComplete,
        });

        // 세션 종료 시 reportId 세팅 (현재는 sessionId fallback)
        if (res.isComplete && state.sessionId) {
          dispatch({ type: "END_DONE", reportId: state.sessionId });
        }
      } catch (err) {
        const code: SiaErrorCode =
          err instanceof SiaApiError ? err.code : "server";
        // expired 시 완료 상태로 전환 (TTL 만료 = 서버가 이미 세션 종료)
        if (code === "expired" && state.sessionId) {
          dispatch({ type: "END_DONE", reportId: state.sessionId });
        } else {
          dispatch({ type: "ERROR", code });
        }
      }
    },
    [state.sessionId, state.status, state.turnCount],
  );

  const resetError = useCallback(() => {
    dispatch({ type: "RESET_ERROR" });
  }, []);

  // ── 유저 명시 종료 (reason="exit" 기본) ──
  const endChat = useCallback(
    async (reason: SiaEndReason = "exit") => {
      if (!state.sessionId) return;
      if (state.status === "completed" || state.status === "error") return;
      if (endFiredRef.current) return;

      endFiredRef.current = true;
      try {
        const res = await endSiaChat({
          sessionId: state.sessionId,
          reason,
        });
        dispatch({ type: "END_DONE", reportId: res.sessionId });
      } catch (err) {
        const code: SiaErrorCode =
          err instanceof SiaApiError ? err.code : "server";
        if (code === "expired") {
          // 이미 서버가 세션 종료했으면 completed 로 취급
          dispatch({ type: "END_DONE", reportId: state.sessionId });
        } else {
          // 재시도 가능하도록 ref 되돌림
          endFiredRef.current = false;
          dispatch({ type: "ERROR", code });
        }
      }
    },
    [state.sessionId, state.status],
  );

  return {
    ...state,
    send,
    endChat,
    resetError,
  };
}
