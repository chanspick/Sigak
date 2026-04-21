"""Verdict 2.0 Pydantic schemas (v2 Priority 1 D5).

Application-level JSONB validation for verdicts.preview_content / full_content
(SPEC-ONBOARDING-V2 REQ-SCHEMA-001~004 동일 원칙).

Schemas:
  PreviewContent    — verdicts.preview_content (30% hook 공개)
  PhotoInsight      — full_content.photo_insights[] 개별 엔트리
  Recommendation    — full_content.recommendation (스타일 방향 + 다음 액션)
  FullContent       — verdicts.full_content (10토큰 결제 후 공개)
  VerdictV2Result   — LLM 출력 전체 (preview + full_content)
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class _BaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ─────────────────────────────────────────────
#  Preview — 결제 전 공개
# ─────────────────────────────────────────────

class PreviewContent(_BaseSchema):
    """판정 결론의 30% hook.

    Rules (SPEC REQ-VERDICT-002):
    - hook_line: ≤50 chars (30자 목표 + 여유 20자)
    - reason_summary: 2-3 문장, 근거 30% 까지만
    - 사진별 상세 insight / recommendation 구체 값 금지 (full 전용)
    """
    hook_line: str = Field(min_length=1, max_length=50)
    reason_summary: str = Field(min_length=1, max_length=500)


# ─────────────────────────────────────────────
#  Full — 10 토큰 결제 후 공개
# ─────────────────────────────────────────────

class PhotoInsight(_BaseSchema):
    """업로드 사진 1장별 분석 결과."""
    photo_index: int = Field(ge=0)
    insight: str = Field(min_length=1, max_length=500)
    improvement: str = Field(min_length=1, max_length=500)


class Recommendation(_BaseSchema):
    """전체 분석 결론 + 실행 방향."""
    style_direction: str = Field(min_length=1, max_length=500)
    next_action: str = Field(min_length=1, max_length=500)
    why: str = Field(min_length=1, max_length=500)


class VerdictNumbers(_BaseSchema):
    """구체 숫자 메트릭 — Sia 숫자 근거 규칙 동일 (grounding).

    None-able 필드. LLM 이 계산 가능한 경우에만 populate.
    """
    photo_count: Optional[int] = Field(default=None, ge=1, le=10)
    dominant_tone: Optional[str] = None
    dominant_tone_pct: Optional[int] = Field(default=None, ge=0, le=100)
    chroma_multiplier: Optional[float] = Field(default=None, ge=0.0)
    alignment_with_profile: Optional[str] = None  # 예: "일치" / "부분 일치" / "상충"


class FullContent(_BaseSchema):
    """결제 후 노출. photo_insights 는 업로드 사진 수와 일치."""
    verdict: str = Field(min_length=1, max_length=1500)
    photo_insights: list[PhotoInsight] = Field(default_factory=list)
    recommendation: Recommendation
    numbers: VerdictNumbers = Field(default_factory=VerdictNumbers)
    # PI CTA (클로징) — Priority 1 은 카피 보류 (Q8 deferred to Priority 2)
    # full_content 내부 embedded CTA 자리 확보. D5 Phase 3 에서 채움.
    cta_pi: Optional[dict] = None


# ─────────────────────────────────────────────
#  Top-level LLM 출력
# ─────────────────────────────────────────────

class VerdictV2Result(_BaseSchema):
    """Sonnet 4.6 verdict LLM 출력 전체 (preview + full)."""
    preview: PreviewContent
    full_content: FullContent
