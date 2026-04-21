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


class CtaPi(_BaseSchema):
    """피드 분석 말미 '시각이 본 나' 진입 CTA (D5 Phase 3).

    SPEC-ONBOARDING-V2 REQ-VERDICT-004 / REQ-NAMING-004.

    Rules:
    - "PI" 단일 단어 유저 노출 금지 → "시각이 본 나" 로 표기
    - Sia 톤 서술형 정중체 유지 ("~합니다" / "~있습니다")
    - 판정어 / 평가어 / 확인 요청 금지 (상위 Hard Rules 동일)
    - headline: 30자 이내 훅 문구
    - body: 1-2 문장, 피드 분석에서 드러난 갭을 '시각이 본 나' 로 잇는 교차 설명
    - action_label: 20자 이내 버튼 카피 (예: "시각이 본 나 열기")
    """
    headline: str = Field(min_length=1, max_length=30)
    body: str = Field(min_length=1, max_length=200)
    action_label: str = Field(min_length=1, max_length=20)


class FullContent(_BaseSchema):
    """결제 후 노출. photo_insights 는 업로드 사진 수와 일치."""
    verdict: str = Field(min_length=1, max_length=1500)
    photo_insights: list[PhotoInsight] = Field(default_factory=list)
    recommendation: Recommendation
    numbers: VerdictNumbers = Field(default_factory=VerdictNumbers)
    # '시각이 본 나' CTA — D5 Phase 3 에서 Sonnet 이 verdict 와 함께 동시 생성.
    # Optional 로 둬 Priority 2 이후 PI 리포트 구조 변경 시 후방호환 여지 확보.
    cta_pi: Optional[CtaPi] = None


# ─────────────────────────────────────────────
#  Top-level LLM 출력
# ─────────────────────────────────────────────

class VerdictV2Result(_BaseSchema):
    """Sonnet 4.6 verdict LLM 출력 전체 (preview + full)."""
    preview: PreviewContent
    full_content: FullContent
