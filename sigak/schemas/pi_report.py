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


# ─────────────────────────────────────────────
#  PI v3 — 9 컴포넌트 3-3-3 구조 (Phase I PI-D)
#
#  본인 결정 (2026-04-25):
#    가입 30 + 추가 20 = 50 토큰 (첫 1회 무료 폐기)
#    preview 무료 (혼합 iii) → 결제 → 풀 PI
#
#  9 컴포넌트:
#    raw 3:   cover / celeb_reference / face_structure
#    vault 3: type_reference / gap_analysis / skin_analysis
#    trend 3: coordinate_map / hair_recommendation / action_plan
#
#  preview visibility:
#    full  : cover / celeb_reference
#    teaser: face_structure / type_reference / gap_analysis / skin_analysis
#    locked: coordinate_map / hair_recommendation / action_plan
# ─────────────────────────────────────────────

PISectionId = Literal[
    "cover",
    "celeb_reference",
    "face_structure",
    "type_reference",
    "gap_analysis",
    "skin_analysis",
    "coordinate_map",
    "hair_recommendation",
    "action_plan",
]

# preview 분기 — 컴포넌트별 가시성 (혼합 iii 패턴)
PI_V3_PREVIEW_VISIBILITY: dict[str, str] = {
    "cover":               "full",
    "face_structure":      "teaser",
    "type_reference":      "teaser",
    "gap_analysis":        "teaser",
    "skin_analysis":       "teaser",
    "coordinate_map":      "locked",
    "hair_recommendation": "locked",
    "action_plan":         "locked",
}

PI_V3_SECTION_ORDER: list[str] = [
    "cover", "face_structure",
    "type_reference", "gap_analysis", "skin_analysis",
    "coordinate_map", "hair_recommendation", "action_plan",
]

PI_V3_UNLOCK_COST_TOKENS = 50


class PIv3Section(BaseModel):
    """PI v3 단일 컴포넌트. content 는 PI-C 가 채울 component-specific dict."""
    model_config = ConfigDict(extra="ignore")

    section_id: PISectionId
    visibility: Literal["full", "teaser", "locked"]
    content: dict = Field(default_factory=dict)


class PIv3Status(BaseModel):
    """GET /api/v3/pi/status 응답."""
    model_config = ConfigDict(extra="ignore")

    has_baseline: bool                      # users.pi_baseline_r2_key 존재 여부
    baseline_uploaded_at: Optional[str] = None
    has_current_report: bool = False        # is_current=TRUE row 존재
    current_report_id: Optional[str] = None
    current_version: Optional[int] = None
    unlocked_at: Optional[str] = None
    unlock_cost_tokens: int = PI_V3_UNLOCK_COST_TOKENS
    token_balance: int = 0
    needs_payment_tokens: int = 0           # 부족 토큰 (UI paywall)
    pi_pending: bool = False                # baseline 업로드 후 preview 미생성


class PIv3UploadResponse(BaseModel):
    """POST /api/v3/pi/upload 응답 — baseline 정면 사진 업로드."""
    model_config = ConfigDict(extra="ignore")

    uploaded: bool
    baseline_r2_key: Optional[str] = None
    uploaded_at: str
    makeup_warning: Optional[str] = None    # 화장 검증 soft warning


class PIv3Report(BaseModel):
    """POST /api/v3/pi/preview & /unlock & GET /{report_id} 공용 응답.

    preview = visibility 가 "full"/"teaser"/"locked" 혼합
    unlock  = 모든 sections.visibility = "full"
    """
    model_config = ConfigDict(extra="ignore")

    report_id: str
    version: int
    is_current: bool = True
    generated_at: str
    is_preview: bool                        # True = preview (토큰 차감 X), False = unlocked
    sections: list[PIv3Section] = Field(default_factory=list)

    # 페이월 안내 — preview 응답에서만 채움
    unlock_cost_tokens: int = PI_V3_UNLOCK_COST_TOKENS
    token_balance: Optional[int] = None
    needs_payment_tokens: Optional[int] = None


class PIv3VersionEntry(BaseModel):
    """GET /api/v3/pi/list 응답 행."""
    model_config = ConfigDict(extra="ignore")

    report_id: str
    version: int
    is_current: bool
    generated_at: str
    is_preview: bool = False


class PIv3VersionsList(BaseModel):
    """GET /api/v3/pi/list 응답."""
    model_config = ConfigDict(extra="ignore")

    versions: list[PIv3VersionEntry] = Field(default_factory=list)
    current_report_id: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
#  Phase I PI v1 — 9 컴포넌트 typed content schemas (PI-C 영역)
# ═══════════════════════════════════════════════════════════════
#
#  CLAUDE.md §0 / §5.1 / §7 — 풀 분량 = raw 3 + vault 3 + trend 3.
#
#  본 schema 는 PI-C 어댑터들이 산출하는 컨테이너.
#  PI-A 가 PiContent → PIv3Section.content (dict) 직렬화. PI-D 는 PiPreview 로
#  혼합 iii 노출. extra="ignore" 로 BC 보장 (기존 PIv3Section.content dict
#  타입과 양립 — 어댑터가 model_dump() 해서 dict 로 변환 가능).

class CoverContent(BaseModel):
    """Cover — 풀 노출 컴포넌트.

    vault user_phrases echo + IG taste 종합 narrative. 첫인상.
    Day 1: matched_type_name 만으로 generic narrative.
    """
    model_config = ConfigDict(extra="ignore")

    narrative: str = ""          # 3-4 문장
    key_phrases: list[str] = Field(default_factory=list)   # vault user_phrases echo
    headline: str = ""           # 한 줄 헤드라인


class CelebReferenceMatch(BaseModel):
    """단일 셀럽 매칭 — PI-B Vision 결과를 어댑트한 형태."""
    model_config = ConfigDict(extra="ignore")

    name: str
    photo_url: str
    similarity: float = Field(ge=0.0, le=1.0)
    reason: str = ""             # ~80자


class CelebReferenceContent(BaseModel):
    """Celeb Reference — 풀 노출 (top 3 닮은꼴)."""
    model_config = ConfigDict(extra="ignore")

    top_celebs: list[CelebReferenceMatch] = Field(default_factory=list)


class FaceStructureMetric(BaseModel):
    """Face structure 단일 메트릭 (한국어 descriptor 포함)."""
    model_config = ConfigDict(extra="ignore")

    name: str
    value: float | str
    descriptor: str              # 한국어 — "둥근 얼굴형" 등


class FaceStructureContent(BaseModel):
    """Face Structure — 풀 노출 (5-7 메트릭 + harmony + distinctive)."""
    model_config = ConfigDict(extra="ignore")

    metrics: list[FaceStructureMetric] = Field(default_factory=list)
    harmony_note: str = ""
    distinctive_points: list[str] = Field(default_factory=list)


class TypeReferenceContent(BaseModel):
    """Type Reference — vault 매칭 type + cluster + features bullet."""
    model_config = ConfigDict(extra="ignore")

    matched_type_id: str = ""           # "type_1" 등
    matched_type_name: str = ""         # "따뜻한 첫사랑"
    reason: str = ""                    # vault 매칭 근거 ~120자
    features_bullet: list[str] = Field(default_factory=list)
    cluster_label: str = ""             # 4 클러스터 한 단어


class AxisCoord(BaseModel):
    """3축 좌표 — VisualCoordinate 와 동일 0~1 외부 스케일."""
    model_config = ConfigDict(extra="ignore")

    shape: float = Field(ge=0.0, le=1.0)
    volume: float = Field(ge=0.0, le=1.0)
    age: float = Field(ge=0.0, le=1.0)


class GapAnalysisContent(BaseModel):
    """Gap Analysis — essence ↔ aspiration narrative."""
    model_config = ConfigDict(extra="ignore")

    essence_coord: AxisCoord
    aspiration_coord: Optional[AxisCoord] = None
    gap_narrative: str = ""             # ~150자
    vault_phrase_echo: list[str] = Field(default_factory=list)


class SkinAnalysisContent(BaseModel):
    """Skin Analysis — BEST/OK/AVOID 5개씩 + foundation + 부위별 가이드."""
    model_config = ConfigDict(extra="ignore")

    best_colors: list[str] = Field(default_factory=list)   # hex 5
    ok_colors: list[str] = Field(default_factory=list)
    avoid_colors: list[str] = Field(default_factory=list)
    foundation_guide: str = ""
    lip_cheek_eye: dict[str, str] = Field(default_factory=dict)   # {lip, cheek, eye}
    trend_palette_match: list[str] = Field(default_factory=list)  # trend_id list


class HairRecommendation(BaseModel):
    """단일 헤어 추천 — hair_rules 근거."""
    model_config = ConfigDict(extra="ignore")

    hair_id: str
    hair_name: str
    reason: str = ""
    trend_match: list[str] = Field(default_factory=list)   # trend_id list
    score: float = 0.0


class HairRecommendationContent(BaseModel):
    """Hair Recommendation — top 3-5."""
    model_config = ConfigDict(extra="ignore")

    top_hairs: list[HairRecommendation] = Field(default_factory=list)


class CoordinateMapContent(BaseModel):
    """Coordinate Map — 유저 좌표 + 8 type 앵커 + trend overlay."""
    model_config = ConfigDict(extra="ignore")

    user_coord: AxisCoord
    type_anchors: dict[str, AxisCoord] = Field(default_factory=dict)
    trend_overlay: list[dict] = Field(default_factory=list)   # [{trend_id, coord_center}]


class ActionItem(BaseModel):
    """Action plan 단일 아이템."""
    model_config = ConfigDict(extra="ignore")

    title: str
    description: str = ""               # ~120자
    source: str = ""                    # KB 출처 또는 axis rule
    vault_echo: Optional[str] = None    # 매칭된 user phrase 1개


class ActionPlanContent(BaseModel):
    """Action Plan — top 3-5 actions."""
    model_config = ConfigDict(extra="ignore")

    actions: list[ActionItem] = Field(default_factory=list)


# ─────────────────────────────────────────────
#  PiContent (9 컴포넌트 풀)
# ─────────────────────────────────────────────

class PiContent(BaseModel):
    """PI v1 풀 분량 컨테이너 — 9 컴포넌트 (raw 3 + vault 3 + trend 3).

    PI-A 가 LLM payload 구성 시 인풋. PI-D 가 PiPreview 로 분배.
    """
    model_config = ConfigDict(extra="ignore")

    # raw 3
    coordinate_map: CoordinateMapContent
    face_structure: FaceStructureContent
    celeb_reference: CelebReferenceContent

    # vault 3
    cover: CoverContent
    type_reference: TypeReferenceContent
    gap_analysis: GapAnalysisContent

    # trend 3
    skin_analysis: SkinAnalysisContent
    hair_recommendation: HairRecommendationContent
    action_plan: ActionPlanContent


# ─────────────────────────────────────────────
#  PiPreview (혼합 iii — 공개/잠금 분배)
# ─────────────────────────────────────────────

class PiPreview(BaseModel):
    """PI 리포트 미리보기 — 혼합 iii 패턴.

    - cover 풀 노출
    - celeb_reference top1 풀 노출
    - face/type/gap/skin teaser 한 줄
    - coordinate_map / hair_recommendation / action_plan 잠금
    """
    model_config = ConfigDict(extra="ignore")

    cover: CoverContent
    celeb_reference_top1: Optional[CelebReferenceMatch] = None
    face_structure_teaser: str = "—"
    type_reference_teaser: str = "—"
    gap_analysis_teaser: str = "—"
    skin_analysis_teaser: str = "—"
    locked_components: list[str] = Field(
        default_factory=lambda: [
            "coordinate_map",
            "hair_recommendation",
            "action_plan",
        ]
    )
