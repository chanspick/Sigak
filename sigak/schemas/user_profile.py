"""User profile + conversation Pydantic schemas (v2 Priority 1 D2).

Pydantic v2. Matches SPEC-ONBOARDING-V2 §11 and design doc §5-6.

Coverage:
  - ConversationMessage         : conversations.messages[] 엔트리
  - StructuredFieldsConfidence  : extraction 신뢰도 맵
  - StructuredFields            : user_profiles.structured_fields (대화 추출 8 필드)
  - IgFeedProfileBasics         : IG 프로필 기본 정보
  - IgFeedCache                 : user_profiles.ig_feed_cache
  - ExtractionResult            : conversations.extraction_result (Sonnet 출력)

Design principles:
  - `extra="ignore"` for forward-compat (새 필드 등장해도 load 실패 X)
  - `confidence <0.4` 필드는 null 로 정규화 (application layer 가 enforce)
  - 시간 필드는 datetime UTC (psycopg2 TIMESTAMPTZ → datetime 자동 변환)
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────
#  Common
# ─────────────────────────────────────────────

class _BaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ─────────────────────────────────────────────
#  Conversations
# ─────────────────────────────────────────────

class ConversationMessage(_BaseSchema):
    """Single message in conversations.messages[].

    role: "user" | "assistant" (Sia)
    ts: ISO-8601 datetime (Redis 에서 문자열, DB에선 datetime)
    """
    role: Literal["user", "assistant"]
    content: str
    ts: datetime


# ─────────────────────────────────────────────
#  Structured Fields (대화 추출 결과)
# ─────────────────────────────────────────────

HeightEnum = Literal[
    "under_155", "155_160", "160_165", "165_170", "170_175", "175_180",
    "180_185", "185_190", "over_190",
]

WeightEnum = Literal[
    "under_45", "45_50", "50_55", "55_60", "60_65", "65_70", "70_80",
    "80_90", "over_90",
]

ShoulderWidthEnum = Literal["narrow", "medium", "wide"]


class StructuredFieldsConfidence(_BaseSchema):
    """Sonnet 4.6 extraction 결과 내 필드별 신뢰도. 0.0 ~ 1.0."""
    desired_image: float = Field(ge=0.0, le=1.0, default=0.0)
    reference_style: float = Field(ge=0.0, le=1.0, default=0.0)
    current_concerns: float = Field(ge=0.0, le=1.0, default=0.0)
    self_perception: float = Field(ge=0.0, le=1.0, default=0.0)
    lifestyle_context: float = Field(ge=0.0, le=1.0, default=0.0)
    height: float = Field(ge=0.0, le=1.0, default=0.0)
    weight: float = Field(ge=0.0, le=1.0, default=0.0)
    shoulder_width: float = Field(ge=0.0, le=1.0, default=0.0)


class StructuredFields(_BaseSchema):
    """user_profiles.structured_fields — Sia 대화 추출 8 필드.

    모든 필드 nullable. Sonnet extraction 시 confidence < 0.4 는 null 로 저장.
    정적 필드 (height/weight/shoulder_width) 는 설정 페이지 수동 수정 가능.
    """
    desired_image: Optional[str] = None
    reference_style: Optional[str] = None
    current_concerns: Optional[list[str]] = None
    self_perception: Optional[str] = None
    lifestyle_context: Optional[str] = None
    height: Optional[HeightEnum] = None
    weight: Optional[WeightEnum] = None
    shoulder_width: Optional[ShoulderWidthEnum] = None
    confidence: Optional[StructuredFieldsConfidence] = None

    def as_merge_dict(self) -> dict:
        """shallow merge 용 dict — 명시 설정된 필드만 포함 (Pydantic v2)."""
        return self.model_dump(exclude_none=True, mode="json")


# ─────────────────────────────────────────────
#  IG Feed Cache (Apify 수집)
# ─────────────────────────────────────────────

IgScope = Literal["full", "public_profile_only"]


class IgFeedProfileBasics(_BaseSchema):
    """ig_feed_cache.profile_basics — 계정 메타 (공개/비공개 양쪽 가능)."""
    username: str
    profile_picture: Optional[str] = None
    bio: Optional[str] = None
    follower_count: int = Field(ge=0, default=0)
    following_count: int = Field(ge=0, default=0)
    post_count: int = Field(ge=0, default=0)
    is_private: bool = False
    is_verified: bool = False


class IgLatestPost(_BaseSchema):
    """ig_feed_cache.latest_posts[] — 최근 10개 포스트 스냅샷.

    Sia Haiku 가 뒷단 분석용으로 소비. 댓글은 본문만 보존 (타인 식별자 제거).
    프라이버시: ownerUsername / ownerProfilePicUrl / owner.id 등 모두 제거된 상태.
    display_url: Instagram CDN URL. TTL 24-48h. Vision 분석은 fetch 직후 즉시만.
    """
    caption: str
    timestamp: Optional[datetime] = None
    hashtags: list[str] = Field(default_factory=list)
    latest_comments: list[str] = Field(default_factory=list)  # 본문 text 만
    display_url: Optional[str] = None  # Sonnet Vision 입력용, 만료 주의


ToneCategory = Literal["쿨뮤트", "웜뮤트", "쿨비비드", "웜비비드", "중성"]
SaturationTrend = Literal["감소", "안정", "증가"]


class IgFeedAnalysis(_BaseSchema):
    """ig_feed_cache.analysis — Sonnet 4.6 Vision 분석 결과 (D6 Phase A, Task 0).

    Apify latest_posts 이미지 10장 + bio + 댓글 집계를 입력으로 받아
    Sonnet 멀티모달이 JSON 산출. Sia Haiku 가 오프닝 데이터 리스트
    생성 시 직접 참조하는 ground-truth.

    analyzed_at: Vision 호출 시각. last_analyzed_post_count 와 결합하여
    refresh 정책 (delta >= 3) 판정.

    v4 (2026-04-28): signature_observations 신규 — Sia v4 T6/T7/T8 의 [관찰]
    슬롯 입력. 관형형+명사 형식 5-10개 (예: "채도 높은 쪽" / "톤 정돈된 분위기").
    sia_v4_slots.render_slot 이 첫 항목 사용.
    """
    tone_category: ToneCategory
    tone_percentage: int = Field(ge=0, le=100)
    saturation_trend: SaturationTrend
    environment: str
    pose_frequency: str
    observed_adjectives: list[str] = Field(default_factory=list, max_length=5)
    style_consistency: float = Field(ge=0.0, le=1.0)
    mood_signal: str  # 1문장 정중체
    three_month_shift: Optional[str] = None
    analyzed_at: datetime
    # v4: 관형형+명사 관찰 5-10개 (T6/T7/T8 [관찰] 슬롯 입력)
    signature_observations: list[str] = Field(default_factory=list, max_length=10)


class IgFeedCache(_BaseSchema):
    """user_profiles.ig_feed_cache — Apify Instagram Scraper 정규화 결과.

    scope:
      - "full": 공개 계정, 피드 수집 완료
      - "public_profile_only": 비공개 계정 — profile_basics 만

    analysis: Sonnet Vision 분석 결과. Vision 실패 or 비공개 계정이면 None.
    last_analyzed_post_count: refresh 정책 B (delta>=3) 판정용.
    """
    scope: IgScope
    profile_basics: IgFeedProfileBasics
    # 아래 필드는 full scope 일 때만 populated. private 이면 None/빈 리스트.
    current_style_mood: Optional[list[str]] = None   # DEPRECATED (D6): analysis.observed_adjectives 로 대체
    style_trajectory: Optional[str] = None           # Phase B 시계열 분석 예약 (현재 None)
    feed_highlights: Optional[list[str]] = None
    latest_posts: Optional[list[IgLatestPost]] = None   # 최근 10개, Sia 뒷단 분석용
    analysis: Optional[IgFeedAnalysis] = None           # D6 Phase A — Sonnet Vision
    last_analyzed_post_count: Optional[int] = None      # D6 Phase A — refresh delta 판정
    raw: Optional[dict] = None   # Apify 원본 payload (debug / 재파싱 용 — PII scrubbed)
    fetched_at: datetime
    # STEP 2 — R2 영구 저장 전환. display_url 이 R2 public URL (또는 업로드 실패 시 CDN URL).
    r2_snapshot_dir: Optional[str] = None   # "user_media/{user_id}/ig_snapshots/{ts}/" — None 이면 R2 미업로드
    # v1.5 — Vision Sonnet raw 응답 R2 보존. PII 격리 위해 DB 직접 저장 X, R2 키 참조만.
    # 메타분석 시 R2 fetch. None 이면 Vision raw 미보존 (구 row 또는 Vision 실패).
    r2_vision_raw_key: Optional[str] = None   # "user_media/{user_id}/ig_snapshots/{ts}/vision_raw.json"


# ─────────────────────────────────────────────
#  Extraction Result (Sonnet 4.6 출력)
# ─────────────────────────────────────────────

class ExtractionResult(_BaseSchema):
    """conversations.extraction_result — Sonnet 4.6 extraction 최종 출력.

    fields: StructuredFields (8 대화 필드 + confidence)
    fallback_needed: 낮은 confidence 로 재질문이 필요한 필드명 리스트
      (Sia 가 fallback 턴에서 이 리스트 기반으로 추가 질문)
    """
    fields: StructuredFields
    fallback_needed: list[str] = Field(default_factory=list)
