// Aspiration (추구미 분석) 타입 — 백엔드 schemas/aspiration.py 동기화 (Phase J).

export type AspirationTargetType = "ig" | "pinterest";

export type AspirationRunStatus =
  | "completed"
  | "failed_blocked"
  | "failed_private"
  | "failed_scrape"
  | "failed_skipped";

export type AxisName = "shape" | "volume" | "age";

export interface VisualCoordinate {
  shape: number;   // 0-1
  volume: number;
  age: number;
}

export interface GapVector {
  primary_axis: AxisName;
  primary_delta: number;
  secondary_axis: AxisName;
  secondary_delta: number;
  tertiary_axis: AxisName;
  tertiary_delta: number;
}

export interface PhotoPair {
  user_photo_url: string;
  // v1.5 호환 (default ""). v2 부터 미사용 — pair_comment 만 사용.
  user_sia_comment: string;
  target_photo_url: string;
  target_sia_comment: string;
  // v2 — 페어 단위 비교 한 줄 (Sonnet cross-analysis 결과). null 이면 미생성.
  pair_comment: string | null;
  pair_axis_hint: string | null;
}

export interface AspirationRecommendation {
  style_direction: string;
  next_action: string;
  why: string;
}

export interface AspirationNumbers {
  primary_axis: AxisName;
  primary_delta: number;     // -1.0 ~ +1.0
  alignment: "근접" | "보통" | "상충";
}

export interface MatchedTrendView {
  trend_id: string;
  title: string;
  category: string;
  detailed_guide: string | null;
  action_hints: string[];
  score: number | null;
}

export interface AspirationAnalysis {
  analysis_id: string;
  user_id: string;
  target_type: AspirationTargetType;
  target_identifier: string;
  target_display_name: string | null;
  created_at: string;

  user_coordinate: VisualCoordinate | null;
  target_coordinate: VisualCoordinate;
  gap_vector: GapVector;
  gap_narrative: string;

  photo_pairs: PhotoPair[];

  // v2 — 가장 의미있는 1쌍 강조. UI 첫 노출/highlight. null 이면 비활성.
  best_fit_pair_index: number | null;

  // v2 — 30자 이내 한 줄 통찰 (gap 직접 명시). null 이면 미생성.
  hook_line: string | null;

  sia_overall_message: string;

  // v2 — 추구미 이동 권장 (트렌드 spirit 흡수). null 이면 fallback.
  recommendation: AspirationRecommendation | null;

  // v2 — 좌표/alignment 메타. UI 칩 보조.
  numbers: AspirationNumbers | null;

  // v1.5 호환 — v2 는 narrative 안에 흡수. UI 노출 X.
  matched_trend_ids: string[];
  matched_trends: MatchedTrendView[];

  target_analysis_snapshot: Record<string, unknown> | null;
  images_captured_count: number;
  r2_target_dir: string | null;
}

// ── Request / Response

export interface AspirationIgRequest {
  target_handle: string;
}

export interface AspirationPinterestRequest {
  board_url: string;
}

export interface AspirationStartResponse {
  analysis_id: string;
  status: AspirationRunStatus;
  analysis: AspirationAnalysis | null;
  token_balance: number;
}

// ─────────────────────────────────────────────
//  List (피드 그리드용) — GET /api/v2/aspiration
// ─────────────────────────────────────────────

/** 1행 요약. cover_photo_url 은 photo_pairs[0].target_photo_url. */
export interface AspirationListItem {
  analysis_id: string;
  target_type: AspirationTargetType;
  target_identifier: string;
  cover_photo_url: string | null;
  created_at: string;
}

export interface AspirationListResponse {
  analyses: AspirationListItem[];
  total: number;
  has_more: boolean;
}
