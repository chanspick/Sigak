"""ig_scraper.is_analysis_stale 테스트 — D6 Phase A refresh 정책 B.

delta >= 3 기준. 양방향 (증가/감소) 경계 포함.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import IgFeedAnalysis, IgFeedCache, IgFeedProfileBasics
from services import ig_scraper


def _cache(
    analysis: IgFeedAnalysis | None,
    last_analyzed_post_count: int | None,
) -> IgFeedCache:
    return IgFeedCache(
        scope="full",
        profile_basics=IgFeedProfileBasics(username="u", post_count=0),
        analysis=analysis,
        last_analyzed_post_count=last_analyzed_post_count,
        fetched_at=datetime.now(timezone.utc),
    )


def _analysis() -> IgFeedAnalysis:
    return IgFeedAnalysis(
        tone_category="쿨뮤트",
        tone_percentage=50,
        saturation_trend="안정",
        environment="x",
        pose_frequency="x",
        observed_adjectives=[],
        style_consistency=0.5,
        mood_signal="x입니다.",
        analyzed_at=datetime.now(timezone.utc),
    )


def test_is_analysis_stale_none_cache_is_true():
    assert ig_scraper.is_analysis_stale(None, current_post_count=10) is True


def test_is_analysis_stale_analysis_missing_is_true():
    cache = _cache(analysis=None, last_analyzed_post_count=10)
    assert ig_scraper.is_analysis_stale(cache, current_post_count=10) is True


def test_is_analysis_stale_legacy_cache_without_count_is_true():
    cache = _cache(analysis=_analysis(), last_analyzed_post_count=None)
    assert ig_scraper.is_analysis_stale(cache, current_post_count=10) is True


def test_is_analysis_stale_delta_below_threshold_is_false():
    cache = _cache(analysis=_analysis(), last_analyzed_post_count=10)
    # delta=2 < 3 → fresh
    assert ig_scraper.is_analysis_stale(cache, current_post_count=12) is False
    assert ig_scraper.is_analysis_stale(cache, current_post_count=8) is False


def test_is_analysis_stale_delta_at_threshold_is_true():
    cache = _cache(analysis=_analysis(), last_analyzed_post_count=10)
    assert ig_scraper.is_analysis_stale(cache, current_post_count=13) is True
    assert ig_scraper.is_analysis_stale(cache, current_post_count=7) is True


def test_is_analysis_stale_delta_over_threshold_is_true():
    cache = _cache(analysis=_analysis(), last_analyzed_post_count=10)
    assert ig_scraper.is_analysis_stale(cache, current_post_count=20) is True


def test_is_analysis_stale_custom_threshold():
    cache = _cache(analysis=_analysis(), last_analyzed_post_count=10)
    # threshold=5, delta=4 → fresh
    assert ig_scraper.is_analysis_stale(
        cache, current_post_count=14, delta_threshold=5,
    ) is False
    # threshold=5, delta=5 → stale
    assert ig_scraper.is_analysis_stale(
        cache, current_post_count=15, delta_threshold=5,
    ) is True
