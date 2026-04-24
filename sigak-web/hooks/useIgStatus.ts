"use client";

/**
 * useIgStatus — IG 분석 진행 상태 폴링 훅.
 *
 * 2.5초 간격 `/api/v1/onboarding/ig-status` 폴링. 최종 상태 (success / private /
 * failed / skipped) 도달 시 자동 중단. 최대 N회 초과 시 에러 상태.
 *
 * 사용처: /onboarding/ig-loading 페이지.
 *
 * 반환:
 *   status          — 최신 서버 status (없으면 "pending")
 *   previewUrls     — 최대 6장
 *   username        — 프로필 username
 *   analyzed        — Vision 분석 완료 여부
 *   isTerminal      — success/private/failed/skipped 중 하나 도달
 *   error           — 폴링 실패 / 타임아웃
 *   elapsedSeconds  — 폴링 경과 시간 (UX copy 용)
 */

import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api/fetch";
import { getIgStatus } from "@/lib/api/onboarding";
import { isIgTerminal } from "@/lib/types/mvp";
import type { IgFetchStatus } from "@/lib/types/mvp";

export type IgPollError = "network" | "auth" | "timeout" | "server";

export interface UseIgStatusOptions {
  /** 폴링 간격 ms. 기본 2500. */
  intervalMs?: number;
  /** 최대 폴링 시도 횟수. 기본 40 (100초). Apify 평균 15s + Vision 10s + 여유. */
  maxAttempts?: number;
  /** 훅 활성화. false 이면 폴링 안 함 (컴포넌트 unmount 방어 or lazy mount). */
  enabled?: boolean;
}

export interface UseIgStatusResult {
  status: IgFetchStatus;
  previewUrls: string[];
  username: string | null;
  analyzed: boolean;
  isTerminal: boolean;
  error: IgPollError | null;
  elapsedSeconds: number;
  /** 현재까지 시도한 폴링 횟수. UX 경고용 (너무 느린 경우). */
  attempts: number;
}

const DEFAULT_INTERVAL = 2500;
const DEFAULT_MAX_ATTEMPTS = 40;


function classifyPollError(err: unknown): IgPollError {
  if (err instanceof ApiError) {
    if (err.status === 401) return "auth";
    return "server";
  }
  if (err instanceof TypeError) return "network";
  return "server";
}


export function useIgStatus(
  options: UseIgStatusOptions = {},
): UseIgStatusResult {
  const {
    intervalMs = DEFAULT_INTERVAL,
    maxAttempts = DEFAULT_MAX_ATTEMPTS,
    enabled = true,
  } = options;

  const [status, setStatus] = useState<IgFetchStatus>("pending");
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [username, setUsername] = useState<string | null>(null);
  const [analyzed, setAnalyzed] = useState(false);
  const [error, setError] = useState<IgPollError | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const startTimeRef = useRef<number>(Date.now());
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    stoppedRef.current = false;
    startTimeRef.current = Date.now();

    let timer: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    const tick = async () => {
      if (stoppedRef.current) return;
      attempt += 1;
      setAttempts(attempt);
      setElapsedSeconds(
        Math.floor((Date.now() - startTimeRef.current) / 1000),
      );

      if (attempt > maxAttempts) {
        setError("timeout");
        return;
      }

      try {
        const resp = await getIgStatus();
        if (stoppedRef.current) return;

        setStatus(resp.status);
        setPreviewUrls(resp.preview_urls);
        setUsername(resp.username);
        setAnalyzed(resp.analyzed);

        if (isIgTerminal(resp.status)) {
          // 최종 상태 — 폴링 중단
          stoppedRef.current = true;
          return;
        }
      } catch (err) {
        if (stoppedRef.current) return;
        setError(classifyPollError(err));
        return;
      }

      // 다음 tick 예약
      if (!stoppedRef.current) {
        timer = setTimeout(tick, intervalMs);
      }
    };

    // 첫 tick 즉시 실행 (지연 없이)
    tick();

    return () => {
      stoppedRef.current = true;
      if (timer) clearTimeout(timer);
    };
  }, [enabled, intervalMs, maxAttempts]);

  return {
    status,
    previewUrls,
    username,
    analyzed,
    isTerminal: isIgTerminal(status),
    error,
    elapsedSeconds,
    attempts,
  };
}
