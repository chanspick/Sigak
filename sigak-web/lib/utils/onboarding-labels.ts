// SIGAK — 온보딩 값 ↔ 한글 라벨 매핑 유틸.
//
// 백엔드는 `height: "160_165"` 같은 raw 값을 저장. 시각 리포트/프로필 등
// 유저에게 보여줄 때 "160~165cm" 한글 라벨로 변환.
//
// onboarding-steps.ts 의 ONBOARDING_STEPS 에서 options 을 뽑아 lookup 테이블 구성.

import { ONBOARDING_STEPS } from "@/lib/constants/onboarding-steps";

type Lookup = Record<string, Record<string, string>>;

function buildLookup(): Lookup {
  const lookup: Lookup = {};
  for (const step of ONBOARDING_STEPS) {
    for (const q of step.questions) {
      if (!q.options) continue;
      const sub: Record<string, string> = {};
      for (const o of q.options) sub[o.value] = o.label;
      lookup[q.key] = sub;
    }
  }
  return lookup;
}

const LOOKUP = buildLookup();

/** single_select 값 → 한글 라벨. 없으면 원래 값 그대로. */
export function labelFor(key: string, value: string | undefined | null): string {
  if (!value) return "";
  const sub = LOOKUP[key];
  return sub?.[value] ?? value;
}

/** multi_select CSV → 한글 라벨 배열. */
export function labelsFor(
  key: string,
  csv: string | undefined | null,
): string[] {
  if (!csv) return [];
  return csv
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean)
    .map((v) => labelFor(key, v));
}
