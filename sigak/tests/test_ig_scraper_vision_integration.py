"""ig_scraper ↔ ig_feed_analyzer 통합 테스트 — D6 Phase A.

fetch_ig_profile 성공 경로에서 analysis 가 채워지는지, Vision 실패 시
analysis=None 으로 degrade 되는지 확인. Apify / Sonnet 둘 다 monkey-patch.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import IgFeedAnalysis, IgFeedCache
from services import ig_scraper


@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    yield
    config_module._settings = None


def _set_settings(**overrides):
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


def _apify_profile_raw():
    return {
        "username": "yuni",
        "biography": "bio",
        "followersCount": 100,
        "followsCount": 200,
        "postsCount": 10,
        "private": False,
        "verified": False,
        "profilePicUrl": "https://example.com/pic.jpg",
    }


def _apify_post(idx: int, with_url: bool = True):
    return {
        "caption": f"post {idx}",
        "timestamp": f"2026-01-0{idx + 1}T10:00:00.000Z",
        "hashtags": [],
        "displayUrl": (
            f"https://cdn.example.com/img{idx}.jpg" if with_url else None
        ),
        "latestComments": [
            {"text": "단정하다", "ownerUsername": "타인", "owner": {"id": "1"}},
        ],
    }


def _fake_analysis():
    return IgFeedAnalysis(
        tone_category="쿨뮤트",
        tone_percentage=68,
        saturation_trend="감소",
        environment="실내 + 자연광",
        pose_frequency="측면 > 정면",
        observed_adjectives=["단정한"],
        style_consistency=0.82,
        mood_signal="조용한 자신감이 드러납니다.",
        three_month_shift=None,
        analyzed_at=datetime.now(timezone.utc),
    )


# ─────────────────────────────────────────────
#  Success — analysis populated
# ─────────────────────────────────────────────

def test_fetch_success_populates_analysis(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")

    monkeypatch.setattr(
        ig_scraper, "_call_apify_actor",
        lambda handle, api_key, actor_id, timeout, **kw: [
            _apify_profile_raw(),
            _apify_post(0),
            _apify_post(1),
        ],
    )
    # Vision 우회 — analyze_ig_feed 모킹
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed",
        lambda posts, biography: _fake_analysis(),
    )

    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "success"
    assert isinstance(cache, IgFeedCache)
    assert cache.analysis is not None
    assert cache.analysis.tone_category == "쿨뮤트"
    assert cache.last_analyzed_post_count == 10  # postsCount


def test_latest_posts_preserve_display_url(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    # addParentData=True 의 실 shape: 각 post 에 profile meta 가 merge 된 형태
    monkeypatch.setattr(
        ig_scraper, "_call_apify_actor",
        lambda *a, **kw: [
            {**_apify_profile_raw(), **_apify_post(0, with_url=True)},
        ],
    )
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed",
        lambda posts, biography: _fake_analysis(),
    )

    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "success"
    assert cache.latest_posts[0].display_url == "https://cdn.example.com/img0.jpg"


# ─────────────────────────────────────────────
#  Vision failure degradation
# ─────────────────────────────────────────────

def test_vision_failure_degrades_analysis_none(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    monkeypatch.setattr(
        ig_scraper, "_call_apify_actor",
        lambda *a, **kw: [_apify_profile_raw(), _apify_post(0)],
    )
    # Vision 이 예외 던짐 — _run_vision_analysis 가 흡수
    from services import ig_feed_analyzer

    def _boom(posts, biography):
        raise RuntimeError("sonnet down")

    monkeypatch.setattr(ig_feed_analyzer, "analyze_ig_feed", _boom)

    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "success"  # cache 자체는 살아남음
    assert cache.analysis is None
    assert cache.last_analyzed_post_count is None


def test_vision_returns_none_degrades_cleanly(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    monkeypatch.setattr(
        ig_scraper, "_call_apify_actor",
        lambda *a, **kw: [_apify_profile_raw(), _apify_post(0)],
    )
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed", lambda posts, biography: None,
    )

    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "success"
    assert cache.analysis is None
    assert cache.last_analyzed_post_count is None


def test_private_account_skips_vision(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    private_profile = dict(_apify_profile_raw())
    private_profile["private"] = True
    monkeypatch.setattr(
        ig_scraper, "_call_apify_actor", lambda *a, **kw: [private_profile],
    )

    called = {"hits": 0}
    from services import ig_feed_analyzer

    def _spy(posts, biography):
        called["hits"] += 1
        return _fake_analysis()

    monkeypatch.setattr(ig_feed_analyzer, "analyze_ig_feed", _spy)

    status, cache = ig_scraper.fetch_ig_profile("priv")
    assert status == "private"
    assert cache.analysis is None  # 비공개는 Vision 없음
    assert called["hits"] == 0
