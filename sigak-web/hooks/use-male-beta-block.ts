// 남성 v1.1 베타 차단 hook (2026-04-27)
//
// /me API 의 gender 필드 (vault 권위 = user_profiles.gender) 를 확인.
// male 이면 blocked=true 반환 — 호출 페이지가 차단 UI 렌더.
//
// 정합 정책:
//   - gender === "male" 만 차단. female / null / 비표준 = 통과 (보수).
//   - fetch 실패 시 통과 (네트워크 일시 장애가 사용자 경험 깨지 않도록).
//   - backend 가드가 안전망 — frontend 가 누락해도 409 반환.
//
// v1.1 마일스톤에서 male 풀 정합 완료 시 hook 제거.

"use client";

import { useEffect, useState } from "react";
import { getMe } from "@/lib/api/onboarding";

export interface MaleBetaBlockState {
  checking: boolean;
  blocked: boolean;
}

export function useMaleBetaBlock(): MaleBetaBlockState {
  const [state, setState] = useState<MaleBetaBlockState>({
    checking: true,
    blocked: false,
  });

  useEffect(() => {
    let cancelled = false;
    getMe()
      .then((me) => {
        if (cancelled) return;
        setState({ checking: false, blocked: me.gender === "male" });
      })
      .catch(() => {
        if (cancelled) return;
        // fetch 실패 — 보수적 통과 (backend 가드가 안전망)
        setState({ checking: false, blocked: false });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
