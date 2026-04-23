"""Phase J — Aspiration 엔진 테스트.

aspiration_common / aspiration_engine_ig / aspiration_engine_pinterest / 라우트.
실 Apify / Anthropic API 호출 0건 — monkey-patch 로 전부 격리.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.aspiration import (
    AspirationAnalysis,
    PhotoPair,
    TargetType,
)
from schemas.user_profile import (
    IgFeedAnalysis,
    IgFeedCache,
    IgFeedProfileBasics,
    IgLatestPost,
)
from services import aspiration_common
from services import aspiration_engine_ig as ig_engine
from services import aspiration_engine_pinterest as pin_engine
from services.coordinate_system import VisualCoordinate, neutral_coordinate


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _sample_target_analysis(tone: str = "쿨뮤트", pct: int = 68) -> IgFeedAnalysis:
    return IgFeedAnalysis(
        tone_category=tone,        # type: ignore[arg-type]
        tone_percentage=pct,
        saturation_trend="감소",    # type: ignore[arg-type]
        environment="실내",
        pose_frequency="측면 > 정면",
        observed_adjectives=["단정"],
        style_consistency=0.8,
        mood_signal="정돈된 여운을 남기는 분입니다.",
        three_month_shift=None,
        analyzed_at=datetime.now(timezone.utc),
    )


def _sample_posts(n: int, with_url: bool = True) -> list[IgLatestPost]:
    return [
        IgLatestPost(
            caption=f"post {i}",
            display_url=(f"https://cdn.example.com/{i}.jpg" if with_url else None),
        )
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    yield
    config_module._settings = None


def _set_settings(**overrides):
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


# ─────────────────────────────────────────────
#  aspiration_common — coordinate derivation
# ─────────────────────────────────────────────

def test_derive_coordinate_cool_mute_biases_shape_positive():
    a = _sample_target_analysis(tone="쿨뮤트", pct=68)
    coord = aspiration_common.derive_coordinate_from_analysis(a)
    # 쿨뮤트는 shape + (sharp 쪽) 편향
    assert coord.shape >= 0.5
    assert 0.0 <= coord.volume <= 1.0
    assert 0.0 <= coord.age <= 1.0


def test_derive_coordinate_warm_vivid_biases_shape_negative():
    a = IgFeedAnalysis(
        tone_category="웜비비드",
        tone_percentage=60,
        saturation_trend="증가",
        environment="외부",
        pose_frequency="정면 > 측면",
        observed_adjectives=[],
        style_consistency=0.9,
        mood_signal="프레시 무드가 드러납니다.",
        three_month_shift=None,
        analyzed_at=datetime.now(timezone.utc),
    )
    coord = aspiration_common.derive_coordinate_from_analysis(a)
    # 웜비비드 = 살짝 소프트 + 프레시
    assert coord.shape <= 0.5
    assert coord.age <= 0.5


def test_derive_coordinate_clamps():
    # 극단 값도 0-1 구간 유지
    a = _sample_target_analysis(tone="쿨비비드", pct=100)
    c = aspiration_common.derive_coordinate_from_analysis(a)
    assert 0.0 <= c.shape <= 1.0
    assert 0.0 <= c.volume <= 1.0
    assert 0.0 <= c.age <= 1.0


# ─────────────────────────────────────────────
#  Photo pair selection
# ─────────────────────────────────────────────

def test_select_photo_pairs_matches_min_count():
    user_posts = _sample_posts(3, with_url=True)
    target_posts = _sample_posts(5, with_url=True)
    gap = VisualCoordinate(shape=0.3, volume=0.5, age=0.5).gap_vector(
        VisualCoordinate(shape=0.7, volume=0.5, age=0.5)
    )
    pairs = aspiration_common.select_photo_pairs(
        user_posts=user_posts, target_posts=target_posts, gap=gap, max_pairs=5,
    )
    assert len(pairs) == 3   # min(3, 5)
    for p in pairs:
        assert p.user_photo_url
        assert p.target_photo_url
        assert "shape" in (p.pair_axis_hint or "")


def test_select_photo_pairs_empty_inputs():
    gap = neutral_coordinate().gap_vector(neutral_coordinate())
    pairs = aspiration_common.select_photo_pairs(
        user_posts=[], target_posts=[], gap=gap,
    )
    assert pairs == []


# ─────────────────────────────────────────────
#  IG engine — run_aspiration_ig
# ─────────────────────────────────────────────

def _fake_apify_response():
    """addParentData 형태의 Apify 응답 — profile meta + 10 posts."""
    profile_meta = {
        "username": "targetuser",
        "private": False,
        "followersCount": 5000,
        "postsCount": 100,
        "profilePicUrl": "https://cdn.example.com/pp.jpg",
    }
    items = [
        {**profile_meta, **{
            "caption": f"p{i}",
            "timestamp": f"2026-04-0{i + 1}T10:00:00.000Z",
            "displayUrl": f"https://cdn.example.com/img{i}.jpg",
            "latestComments": [],
        }}
        for i in range(5)
    ]
    return items


def test_run_aspiration_ig_happy_path(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    # Apify stub
    monkeypatch.setattr(ig_engine, "_call_apify_actor",
                        lambda **kw: _fake_apify_response())
    # Vision stub — 실 Sonnet 호출 금지
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed",
        lambda posts, biography: _sample_target_analysis(),
    )

    class _FakeDB:
        def execute(self, *a, **kw):
            class _R:
                def first(self):
                    return None
            return _R()

    result = ig_engine.run_aspiration_ig(
        _FakeDB(),
        user_id="u1",
        user_gender="female",
        user_coordinate=VisualCoordinate(shape=0.3, volume=0.5, age=0.4),
        target_handle_raw="@targetuser",
    )
    assert result.status == "completed"
    assert result.analysis is not None
    assert result.analysis.target_type == "ig"
    assert result.analysis.target_identifier == "targetuser"
    assert result.analysis.gap_narrative
    # Apify 수집 이미지 존재
    assert result.analysis.images_captured_count > 0


def test_run_aspiration_ig_private_account(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")

    def _priv(**kw):
        return [{"username": "priv", "private": True, "followersCount": 0}]

    monkeypatch.setattr(ig_engine, "_call_apify_actor", _priv)

    class _DB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()

    result = ig_engine.run_aspiration_ig(
        _DB(),
        user_id="u1", user_gender="female",
        user_coordinate=None, target_handle_raw="priv",
    )
    assert result.status == "failed_private"


def test_run_aspiration_ig_empty_handle():
    class _DB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()
    result = ig_engine.run_aspiration_ig(
        _DB(),
        user_id="u1", user_gender="female",
        user_coordinate=None, target_handle_raw="  ",
    )
    assert result.status == "failed_skipped"


def test_run_aspiration_ig_blocked(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    monkeypatch.setattr(
        aspiration_common, "is_blocked",
        lambda db, *, target_type, target_identifier: True,
    )
    # blocklist 는 ig_engine 이 is_blocked 를 import 사용 — 같은 symbol 패치되야함
    monkeypatch.setattr(
        ig_engine, "is_blocked",
        lambda db, *, target_type, target_identifier: True,
    )

    class _DB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()
    result = ig_engine.run_aspiration_ig(
        _DB(),
        user_id="u1", user_gender="female",
        user_coordinate=None, target_handle_raw="blockedone",
    )
    assert result.status == "failed_blocked"


def test_run_aspiration_ig_vision_failure_degrades(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    monkeypatch.setattr(ig_engine, "_call_apify_actor",
                        lambda **kw: _fake_apify_response())
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed",
        lambda posts, biography: None,   # Vision 실패
    )

    class _DB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()

    result = ig_engine.run_aspiration_ig(
        _DB(),
        user_id="u1", user_gender="female",
        user_coordinate=neutral_coordinate(),
        target_handle_raw="targetuser",
    )
    assert result.status == "failed_scrape"


# ─────────────────────────────────────────────
#  Pinterest engine
# ─────────────────────────────────────────────

def test_pinterest_url_normalization():
    ok = pin_engine._normalize_board_url(
        "https://www.pinterest.com/user123/my-board/"
    )
    assert ok == "https://www.pinterest.com/user123/my-board/"

    ok2 = pin_engine._normalize_board_url(
        "https://pinterest.com/user123/my-board"
    )
    assert ok2 == "https://www.pinterest.com/user123/my-board/"

    assert pin_engine._normalize_board_url("") == ""
    assert pin_engine._normalize_board_url("https://pin.it/abc") == ""
    assert pin_engine._normalize_board_url("https://www.pinterest.com/only") == ""


def test_pinterest_board_hash_deterministic():
    a = pin_engine._board_hash("https://www.pinterest.com/u/b/")
    b = pin_engine._board_hash("https://www.pinterest.com/u/b/")
    c = pin_engine._board_hash("https://www.pinterest.com/x/y/")
    assert a == b
    assert a != c


def test_run_aspiration_pinterest_disabled_by_default(monkeypatch):
    _set_settings(apify_api_key="k", pinterest_enabled=False)

    class _DB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()

    result = pin_engine.run_aspiration_pinterest(
        _DB(),
        user_id="u1", user_gender="female",
        user_coordinate=None,
        board_url="https://www.pinterest.com/u/b/",
    )
    assert result.status == "failed_skipped"


def test_run_aspiration_pinterest_happy_path(monkeypatch):
    _set_settings(
        apify_api_key="k",
        pinterest_enabled=True,
    )
    monkeypatch.setattr(
        pin_engine, "_call_pinterest_actor",
        lambda **kw: [f"https://i.pinimg.com/{i}.jpg" for i in range(6)],
    )
    # pin_engine 이 import 해서 보유한 reference 를 교체해야 monkey-patch 먹힘
    monkeypatch.setattr(
        pin_engine, "analyze_ig_feed",
        lambda posts, biography: _sample_target_analysis(),
    )

    class _DB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()

    result = pin_engine.run_aspiration_pinterest(
        _DB(),
        user_id="u1", user_gender="female",
        user_coordinate=VisualCoordinate(shape=0.4, volume=0.5, age=0.5),
        board_url="https://www.pinterest.com/curator/moodboard/",
    )
    assert result.status == "completed"
    assert result.analysis is not None
    assert result.analysis.target_type == "pinterest"
    assert result.analysis.images_captured_count == 6


def test_wrap_images_as_posts():
    urls = ["https://x/1.jpg", "https://x/2.jpg"]
    posts = pin_engine._wrap_images_as_posts(urls)
    assert len(posts) == 2
    assert posts[0].display_url == urls[0]
    assert posts[0].caption == ""
