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
  user_sia_comment: string;
  target_photo_url: string;
  target_sia_comment: string;
  pair_axis_hint: string | null;
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

  sia_overall_message: string;
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
