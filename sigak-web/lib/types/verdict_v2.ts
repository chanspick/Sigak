// SIGAK — Verdict 2.0 types (backend: sigak/schemas/verdict_v2.py).
//
// preview_content 는 무료 공개(결제 전), full_content 는 10 토큰 unlock 후 공개.
// cta_pi 는 PI 엔진 미완으로 백엔드에서 None 강제 주입 중 (services/verdict_v2.py).

export interface PreviewContent {
  /** ≤50자 훅 문구. */
  hook_line: string;
  /** 2-3문장 근거 요약 (결제 전 30% hook). */
  reason_summary: string;
  /** WTP 가설 — best_fit 사진 인덱스 (Optional, backward compat).
   *  null = best_fit 미선정. */
  best_fit_photo_index?: number | null;
  /** best_fit 1장의 insight 풀 노출 텍스트 (결제 전 공개).
   *  full_content.photo_insights[best_fit_photo_index].insight 와 동일. */
  best_fit_insight?: string | null;
  /** best_fit 1장의 improvement 풀 노출 텍스트.
   *  full_content.photo_insights[best_fit_photo_index].improvement 와 동일. */
  best_fit_improvement?: string | null;
}

export interface PhotoInsight {
  /** 업로드 사진 0-based 순번. */
  photo_index: number;
  /** 사진별 구조/배경/구도 해석. */
  insight: string;
  /** 사진별 개선 방향. */
  improvement: string;
}

export interface Recommendation {
  /** 전체 스타일 방향. */
  style_direction: string;
  /** 실행 가능한 다음 액션. */
  next_action: string;
  /** 방향 제시 이유. */
  why: string;
}

export interface VerdictNumbers {
  photo_count: number | null;
  dominant_tone: string | null;
  dominant_tone_pct: number | null;
  chroma_multiplier: number | null;
  /** "일치" | "부분 일치" | "상충" */
  alignment_with_profile: string | null;
}

export interface FullContent {
  /** 전체 판정 서사 (≤1500자). */
  verdict: string;
  photo_insights: PhotoInsight[];
  recommendation: Recommendation;
  numbers: VerdictNumbers;
  /** PI 엔진 미완으로 백엔드에서 None 주입. UI 무시. */
  cta_pi: null;
  /** WTP 가설 — best_fit 사진 인덱스 (Optional, backward compat).
   *  preview.best_fit_photo_index 와 동일 값 (백엔드 sync).
   *  null = best_fit 미선정 (정규식 fallback 적용). */
  best_fit_photo_index?: number | null;
}

/** R2 에 저장된 업로드 사진 public URL.
 *  photo_index 0-based 순서. null = 저장 실패 / r2_public_base_url 미설정. */
export type PhotoUrl = string | null;

export interface VerdictV2CreateResponse {
  verdict_id: string;
  version: "v2";
  preview: PreviewContent;
  full_unlocked: boolean;
  photo_count: number;
  photo_urls: PhotoUrl[];
  /** WTP 가설 — best_fit 1장의 R2 public URL (preview 영역에서 사용).
   *  null = best_fit 미선정 또는 R2 저장 실패. */
  best_fit_photo_url?: string | null;
}

export interface VerdictV2GetResponse {
  verdict_id: string;
  version: "v2";
  full_unlocked: boolean;
  preview: PreviewContent;
  /** full_unlocked=true 일 때만 채워짐. */
  full_content: FullContent | null;
  photo_urls: PhotoUrl[];
  best_fit_photo_url?: string | null;
}

export interface VerdictV2UnlockResponse {
  verdict_id: string;
  full_unlocked: boolean;
  full_content: FullContent;
  balance: number;
  photo_urls: PhotoUrl[];
  best_fit_photo_url?: string | null;
}
