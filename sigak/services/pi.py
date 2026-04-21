"""PI (Personal Image) 리포트 generation service (v2 Priority 1 D5 Phase 3).

SPEC-ONBOARDING-V2 REQ-PI-001~003.

역할 분리:
- v1 path (/api/v1/pi/unlock): 기존 stub 그대로 유지.
  build_v1_report_data() 는 routes/pi.py 의 _stub_report_data() 를 이관한 것.
- v2 path (/api/v2/pi/unlock): user_profile.structured_fields + ig_feed_cache
  를 seed 로 받아 PI 리포트 placeholder 를 생성.

D5 Phase 3 에선 LLM 호출 없이 structured echo 만 수행. 실제 Sonnet 기반 얼굴
분석 + gap 생성은 D6+ 스코프 (사진 업로드 파이프라인 결정 이후).

설계 원칙:
- 이 서비스는 DB 접근 / commit 금지. Dict 입출력만.
- Transaction ownership 은 routes 가 가진다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  v1 (unchanged behavior) — PLC compliance 용으로 이관
# ─────────────────────────────────────────────

def build_v1_report_data() -> dict:
    """v1 stub. status='generating' placeholder.

    routes/pi.py._stub_report_data() 와 동일한 계약. 호출 측은 이 함수만 쓰면
    된다. (routes 는 v1 엔드포인트에서 이 함수로 교체.)
    """
    return {
        "status": "generating",
        "face_analysis": None,
        "skin_tone": None,
        "gap_analysis": None,
        "hair_recommendations": None,
        "makeup_guide": None,
    }


# ─────────────────────────────────────────────
#  v2 — user_profile 통합
# ─────────────────────────────────────────────

_STRUCTURED_ECHO_KEYS = (
    "desired_image",
    "reference_style",
    "current_concerns",
    "self_perception",
    "lifestyle_context",
    "height",
    "weight",
    "shoulder_width",
)


def _echo_structured_fields(structured: dict) -> dict:
    """PI v2 seed 로 재사용할 structured_fields 부분 추출.

    확장 키 / 빈 값은 제외. 이 함수는 PI 리포트 저장 전 source-of-truth 로 쓰이며,
    향후 D6+ LLM 리포트 생성에서도 이 seed 를 입력으로 받게 된다.
    """
    out: dict[str, Any] = {}
    for k in _STRUCTURED_ECHO_KEYS:
        v = structured.get(k)
        if v not in (None, "", [], {}):
            out[k] = v
    return out


def _echo_ig_feed_cache(cache: Optional[dict]) -> Optional[dict]:
    """ig_feed_cache 에서 PI 관련 key 만 복사.

    tone / trajectory / feed_highlights 는 gap 분석 seed 로 유용.
    profile_basics 는 follower_count 등 식별 가능 정보 포함해 저장에서 제외.
    """
    if not cache:
        return None
    out: dict[str, Any] = {}
    if v := cache.get("current_style_mood"):
        out["current_style_mood"] = v
    if v := cache.get("style_trajectory"):
        out["style_trajectory"] = v
    if v := cache.get("feed_highlights"):
        out["feed_highlights"] = v
    if v := cache.get("scope"):
        out["scope"] = v
    return out or None


def build_v2_report_data(user_profile: dict) -> dict:
    """v2 PI 리포트 payload — user_profile seed 반영.

    D5 Phase 3 scope: LLM 미호출, status='generating' + seed echo.
    D6+ scope 에서 이 dict 를 Sonnet 입력으로 넘겨 실제 리포트를 채운다.

    Args:
      user_profile: services.user_profiles.get_profile() 반환 dict.

    Returns:
      pi_reports.report_data JSONB 에 저장할 dict.
    """
    structured = user_profile.get("structured_fields") or {}
    ig_cache = user_profile.get("ig_feed_cache")
    now_iso = datetime.now(timezone.utc).isoformat()

    data: dict[str, Any] = {
        "status": "generating",
        "version": "v2",
        "generated_at": now_iso,
        "profile_seed": {
            "gender": user_profile.get("gender"),
            "structured_fields": _echo_structured_fields(structured),
            "ig_feed_cache": _echo_ig_feed_cache(ig_cache),
        },
        "face_analysis": None,
        "skin_tone": None,
        "gap_analysis": None,
        "hair_recommendations": None,
        "makeup_guide": None,
    }
    return data
