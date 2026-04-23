"""시각이 본 당신 (PI Report) 스키마 — Phase I1.

CLAUDE.md §3.2 / §5.1 / §7.1 / §7.2 / §7.3 확정.

구조:
  - 공개/잠금 사진 (유동 — determine_pi_photo_count 결과에 따름)
  - 사진 카테고리 7종 (signature 가 공개 영역)
  - 아이작 M REPORT 7페이지 패턴 필드 (user_summary / needs_statement /
    user_original_phrases / boundary_message / sia_overall_message)
  - Knowledge Base 매칭 (trends / methodologies / references)
  - data_sources_used — 생성 시점 데이터 풍부도 snapshot

버전 관리:
  - report_id PK (migration 에서 user_id → report_id 전환)
  - version 1-based 증가 (재생성마다 +1)
  - is_current — partial unique index 로 유저당 1개 True
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


PhotoCategory = Literal[
    "signature",          # 공개 영역 (정세현님다움 집약)
    "detail_analysis",    # 세부 관찰
    "aspiration_gap",     # 추구미 비교 근거
    "weaker_angle",       # 거리 있는 방향
    "style_element",      # 색 팔레트 hex 포함
    "trend_match",        # KB 트렌드 매칭
    "methodology",        # 방법론 설명
]


class PhotoInsight(BaseModel):
    """PI 리포트 단일 사진 + Sia 해석 단위."""
    model_config = ConfigDict(extra="ignore")

    photo_id: str
    stored_url: str                       # R2 (영구 보관)
    category: PhotoCategory
    sia_comment: str                      # Phase H concrete 주입 전까지 stub
    rank: int                             # 카테고리 내 순위 (1=최고)
    extracted_colors: Optional[list[str]] = None   # hex 팔레트 (style_element 카테고리)
    associated_trend_id: Optional[str] = None      # trend_match / methodology 연결


class PIReportSources(BaseModel):
    """생성 시점 데이터 풍부도 snapshot. boundary_message 동적 생성 및
    유저 대면 "얼마나 아는가" 표시 근거."""
    model_config = ConfigDict(extra="ignore")

    feed_photo_count: int = 0            # Apify 실 수집 장수 (공개/비공개 무관)
    ig_analysis_present: bool = False
    conversation_field_count: int = 0    # Sia 대화 수집 필드 수
    user_original_phrases_count: int = 0
    aspiration_history_count: int = 0
    best_shot_history_count: int = 0
    vault_strength_score: float = Field(ge=0.0, le=1.0, default=0.0)

    selected_from_count: int = 0         # 선별 대상 풀 크기
    public_count: int = 0
    locked_count: int = 0


class PIReport(BaseModel):
    """PI 리포트 도메인 모델 — pi_reports.report_data JSONB + row 조합."""
    model_config = ConfigDict(extra="ignore")

    report_id: str
    user_id: str
    version: int                         # 1-based
    is_current: bool = True
    generated_at: datetime

    # ── 사진 (유동 개수)
    public_photos: list[PhotoInsight] = Field(default_factory=list)
    locked_photos: list[PhotoInsight] = Field(default_factory=list)

    # ── 생성 시점 profile 스냅샷 (immutable)
    user_taste_profile_snapshot: dict = Field(default_factory=dict)

    # ── 아이작 M REPORT 7페이지 패턴
    #    P1 유저 요약 / P2 니즈 선언 / P3 좌표계 (user_original_phrases 활용)
    #    현재 값은 stub — Phase H 완료 시 Haiku/Sonnet concrete 교체.
    user_summary: str = ""               # P1
    needs_statement: str = ""            # P2
    user_original_phrases: list[str] = Field(default_factory=list)   # P3

    # ── Sia 종합 / 경계
    sia_overall_message: str = ""
    boundary_message: str = ""           # P6 — 공개/잠금 경계

    # ── Knowledge Base 매칭
    matched_trend_ids: list[str] = Field(default_factory=list)
    matched_methodology_ids: list[str] = Field(default_factory=list)
    matched_reference_ids: list[str] = Field(default_factory=list)

    # ── 생성 근거
    data_sources_used: PIReportSources = Field(default_factory=PIReportSources)


# ─────────────────────────────────────────────
#  Request / Response
# ─────────────────────────────────────────────

class GeneratePIRequest(BaseModel):
    """POST /api/v2/pi/generate (또는 unlock 경로).

    force_new_version=True: 기존 is_current 를 아카이브하고 신규 version 생성.
    force_new_version=False: is_current 있으면 그대로 반환.
    """
    model_config = ConfigDict(extra="ignore")

    force_new_version: bool = False


class PIStatusV2Response(BaseModel):
    """GET 조회 응답 — 현재 is_current 리포트 상태."""
    model_config = ConfigDict(extra="ignore")

    unlocked: bool                       # 한 번이라도 PI 생성된 적 있는지
    current_report_id: Optional[str] = None
    current_version: Optional[int] = None
    regenerate_cost_tokens: int = 50     # Phase I 재생성 비용 (첫 1회 무료)
    has_free_first: bool = False         # 아직 첫 무료 사용 전이면 True
    public_photo_count: int = 0
    locked_photo_count: int = 0
    unlocked_at: Optional[str] = None
