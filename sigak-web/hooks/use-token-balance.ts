// SIGAK MVP v1.2 — useTokenBalance
//
// TopBar/PRO CTA에서 쓰는 토큰 잔액 조회. authFetch가 JWT 부착.
// 간단한 fire-and-forget hook — 전역 상태 필요하면 나중에 zustand 등으로 교체.
"use client";

import { useCallback, useEffect, useState } from "react";

import { authFetch, ApiError } from "@/lib/api/fetch";
import type { TokenBalanceResponse } from "@/lib/types/mvp";

export interface UseTokenBalanceResult {
  balance: number | null; // null = 로딩 중 or 실패
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useTokenBalance(): UseTokenBalanceResult {
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBalance = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await authFetch<TokenBalanceResponse>("/api/v1/tokens/balance");
      setBalance(r.balance);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError("unauthenticated");
      } else {
        setError(e instanceof Error ? e.message : "unknown");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchBalance();
  }, [fetchBalance]);

  return { balance, loading, error, refetch: fetchBalance };
}
