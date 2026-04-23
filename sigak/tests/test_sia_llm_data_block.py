"""Sia system prompt data_block (Vision 주입) 테스트 — D6 Phase A.

_render_analysis_block 의 emphasis 분기 경계 (70/55) + None 폴백 + 전체
prompt assembly 에 Vision 데이터가 들어가는지 확인.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import sia_llm


# ─────────────────────────────────────────────
#  _render_analysis_block — emphasis thresholds
# ─────────────────────────────────────────────

def _analysis(pct: int, **overrides) -> dict:
    base = {
        "tone_category": "쿨뮤트",
        "tone_percentage": pct,
        "saturation_trend": "감소",
        "environment": "실내 + 자연광",
        "pose_frequency": "측면 > 정면",
        "observed_adjectives": ["단정한"],
        "style_consistency": 0.8,
        "mood_signal": "조용한 자신감이 드러납니다.",
        "three_month_shift": None,
    }
    base.update(overrides)
    return base


def test_render_analysis_block_over_70_says_jibae():
    block = sia_llm._render_analysis_block(_analysis(71))
    assert "지배" in block
    assert "71%" in block


def test_render_analysis_block_at_70_says_usei():
    """경계값 70 → '우세' (> 70 만 '지배')."""
    block = sia_llm._render_analysis_block(_analysis(70))
    assert "우세" in block
    assert "지배" not in block


def test_render_analysis_block_at_56_says_usei():
    block = sia_llm._render_analysis_block(_analysis(56))
    assert "우세" in block
    assert "혼재" not in block


def test_render_analysis_block_at_55_says_honjae():
    """경계값 55 → '혼재' (> 55 만 '우세')."""
    block = sia_llm._render_analysis_block(_analysis(55))
    assert "혼재" in block
    assert "우세" not in block


def test_render_analysis_block_includes_adjectives_and_mood():
    block = sia_llm._render_analysis_block(
        _analysis(68, observed_adjectives=["단정한", "감성적인"]),
    )
    assert "단정한" in block and "감성적인" in block
    assert "직접 인용 금지" in block
    assert "조용한 자신감이 드러납니다" in block


def test_render_analysis_block_none_fallback_bans_fake_numbers():
    block = sia_llm._render_analysis_block(None)
    assert "Vision 분석" in block
    assert "가짜 숫자 금지" in block
    assert "생략" in block


def test_render_analysis_block_empty_dict_also_fallback():
    block = sia_llm._render_analysis_block({})
    assert "가짜 숫자 금지" in block


# ─────────────────────────────────────────────
#  build_system_prompt — end-to-end assembly
# ─────────────────────────────────────────────

def _ig_cache_with_analysis(analysis_pct: int | None):
    """cache dict — analysis_pct None 이면 analysis 없음."""
    cache: dict = {
        "scope": "full",
        "profile_basics": {
            "username": "yuni", "post_count": 10,
            "follower_count": 100, "following_count": 50,
            "is_private": False, "is_verified": False,
        },
        "feed_highlights": ["무드 기록"],
        "latest_posts": [
            {"caption": "p0", "latest_comments": ["단정하다"]},
        ] * 10,
    }
    if analysis_pct is not None:
        cache["analysis"] = _analysis(analysis_pct)
    return cache


def test_build_prompt_with_analysis_includes_data_block():
    prompt = sia_llm.build_system_prompt(
        user_name="민지",
        resolved_name=None,
        collected_fields={},
        missing_fields=["desired_image"],
        ig_feed_cache=_ig_cache_with_analysis(68),
    )
    assert "쿨뮤트" in prompt
    assert "우세" in prompt
    assert "단정한" in prompt
    # Vision data_block 헤더 (분석 성공 시 유니크 문구)
    assert "[Vision 분석 data_block" in prompt
    # Vision-None 폴백의 유니크 헤더는 나오면 안 됨
    assert "[Vision 분석] (없음)" not in prompt


def test_build_prompt_without_analysis_injects_fallback():
    prompt = sia_llm.build_system_prompt(
        user_name="민지",
        resolved_name=None,
        collected_fields={},
        missing_fields=["desired_image"],
        ig_feed_cache=_ig_cache_with_analysis(None),
    )
    # Vision-None 전용 폴백 헤더 + 지시 문구
    assert "[Vision 분석] (없음)" in prompt
    assert "bio / 댓글 기반 단정 1개만" in prompt


def test_build_prompt_no_ig_cache_uses_outer_fallback():
    """ig_feed_cache 자체 None — 기존 기존 placeholder 유지."""
    prompt = sia_llm.build_system_prompt(
        user_name="민지",
        resolved_name=None,
        collected_fields={},
        missing_fields=[],
        ig_feed_cache=None,
    )
    assert "IG 피드 데이터 없음" in prompt
