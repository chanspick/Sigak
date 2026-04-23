"""IG Feed Analyzer (Sonnet Vision) tests — D6 Phase A.

Sonnet API 실 호출 없이 monkey-patch 로 `_call_sonnet_vision` 차단.
verdict_v2 테스트 패턴 복사.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import IgFeedAnalysis, IgLatestPost
from services import ig_feed_analyzer


@pytest.fixture(autouse=True)
def _reset_settings_and_client():
    import config as config_module
    config_module._settings = None
    ig_feed_analyzer.reset_client()
    yield
    config_module._settings = None
    ig_feed_analyzer.reset_client()


def _set_settings(**overrides):
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


def _sample_posts(n: int = 3, with_url: bool = True) -> list[IgLatestPost]:
    """최근 n개 post fixture. display_url 포함 여부 토글."""
    out = []
    for i in range(n):
        out.append(IgLatestPost(
            caption=f"post {i}",
            timestamp=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            hashtags=[],
            latest_comments=["단정하다", "감성 있다"] if i == 0 else [],
            display_url=(f"https://cdn.example.com/img{i}.jpg" if with_url else None),
        ))
    return out


# ─────────────────────────────────────────────
#  _aggregate_comments
# ─────────────────────────────────────────────

def test_aggregate_comments_flattens_and_caps_30():
    posts = []
    # 40 댓글 분산
    for i in range(4):
        posts.append(IgLatestPost(
            caption="",
            latest_comments=[f"c{i}_{j}" for j in range(10)],
        ))
    agg = ig_feed_analyzer._aggregate_comments(posts)
    assert agg["total_count"] == 40
    assert len(agg["sample_texts"]) == 30


def test_aggregate_comments_empty_posts_returns_empty():
    agg = ig_feed_analyzer._aggregate_comments([])
    assert agg == {"total_count": 0, "sample_texts": []}


# ─────────────────────────────────────────────
#  analyze_ig_feed — happy path
# ─────────────────────────────────────────────

def test_analyze_ig_feed_happy_path(monkeypatch):
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(5, with_url=True)

    def _mock_call(prompt, images):
        assert len(images) == 5
        assert all(p.display_url for p in images)
        return json.dumps({
            "tone_category": "쿨뮤트",
            "tone_percentage": 68,
            "saturation_trend": "감소",
            "environment": "실내 + 자연광",
            "pose_frequency": "측면 > 정면",
            "observed_adjectives": ["단정한", "감성적인"],
            "style_consistency": 0.82,
            "mood_signal": "조용한 자신감이 드러납니다.",
            "three_month_shift": "채도가 점진적으로 낮아졌습니다.",
        })

    monkeypatch.setattr(ig_feed_analyzer, "_call_sonnet_vision", _mock_call)

    result = ig_feed_analyzer.analyze_ig_feed(posts=posts, biography="bio 텍스트")
    assert isinstance(result, IgFeedAnalysis)
    assert result.tone_category == "쿨뮤트"
    assert result.tone_percentage == 68
    assert result.style_consistency == pytest.approx(0.82)
    assert "단정한" in result.observed_adjectives


def test_analyze_ig_feed_strips_json_fence(monkeypatch):
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(2, with_url=True)

    def _mock_call(prompt, images):
        payload = json.dumps({
            "tone_category": "중성",
            "tone_percentage": 50,
            "saturation_trend": "안정",
            "environment": "혼합",
            "pose_frequency": "정면 > 측면",
            "observed_adjectives": [],
            "style_consistency": 0.5,
            "mood_signal": "중립적 인상입니다.",
            "three_month_shift": None,
        })
        return f"```json\n{payload}\n```"

    monkeypatch.setattr(ig_feed_analyzer, "_call_sonnet_vision", _mock_call)

    result = ig_feed_analyzer.analyze_ig_feed(posts=posts, biography=None)
    assert result is not None
    assert result.tone_category == "중성"


# ─────────────────────────────────────────────
#  analyze_ig_feed — skip / failure paths
# ─────────────────────────────────────────────

def test_analyze_ig_feed_skips_posts_without_display_url(monkeypatch):
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(3, with_url=False)  # all missing display_url

    called = {"hits": 0}
    def _mock_call(prompt, images):
        called["hits"] += 1
        return "{}"

    monkeypatch.setattr(ig_feed_analyzer, "_call_sonnet_vision", _mock_call)

    result = ig_feed_analyzer.analyze_ig_feed(posts=posts, biography="")
    assert result is None
    assert called["hits"] == 0  # Sonnet 호출 자체 skip


def test_analyze_ig_feed_returns_none_on_invalid_json(monkeypatch):
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(1, with_url=True)

    monkeypatch.setattr(
        ig_feed_analyzer, "_call_sonnet_vision",
        lambda prompt, images: "not a json",
    )
    result = ig_feed_analyzer.analyze_ig_feed(
        posts=posts, biography="", max_retries=0,
    )
    assert result is None


def test_analyze_ig_feed_returns_none_on_pydantic_error(monkeypatch):
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(1, with_url=True)

    # tone_percentage 범위 벗어남 (0-100)
    bad = json.dumps({
        "tone_category": "쿨뮤트",
        "tone_percentage": 999,
        "saturation_trend": "감소",
        "environment": "x",
        "pose_frequency": "x",
        "observed_adjectives": [],
        "style_consistency": 0.5,
        "mood_signal": "x",
        "three_month_shift": None,
    })
    monkeypatch.setattr(
        ig_feed_analyzer, "_call_sonnet_vision", lambda p, i: bad,
    )
    result = ig_feed_analyzer.analyze_ig_feed(
        posts=posts, biography="", max_retries=0,
    )
    assert result is None


def test_call_sonnet_vision_downloads_and_base64(monkeypatch):
    """Sonnet 에 URL direct 가 아니라 base64 로 이미지를 넘기는지 검증."""
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(2, with_url=True)

    # 다운로드 모킹 — 이미지 2개 모두 성공
    def _mock_dl(url, timeout=8.0):
        return ("ZmFrZWJ5dGVz", "image/jpeg")  # base64("fakebytes"), jpeg

    import services.ig_feed_analyzer as ifa
    monkeypatch.setattr(ifa, "_download_image_as_base64", _mock_dl)

    captured = {"content": None}

    class _FakeClient:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            captured["content"] = kwargs["messages"][0]["content"]

            class _Resp:
                content = [type("B", (), {"type": "text", "text": '{"tone_category":"중성","tone_percentage":50,"saturation_trend":"안정","environment":"x","pose_frequency":"x","observed_adjectives":[],"style_consistency":0.5,"mood_signal":"x입니다.","three_month_shift":null}'})()]

            return _Resp()

    monkeypatch.setattr(ifa, "_get_client", lambda: _FakeClient())

    result = ifa.analyze_ig_feed(posts=posts, biography="")
    assert result is not None

    # Sonnet 에 전달된 content_blocks 에 base64 이미지 2개 + text 1개
    blocks = captured["content"]
    image_blocks = [b for b in blocks if b.get("type") == "image"]
    assert len(image_blocks) == 2
    for b in image_blocks:
        src = b["source"]
        assert src["type"] == "base64"   # URL direct 아님 (robots.txt 회피)
        assert src["data"] == "ZmFrZWJ5dGVz"
        assert src["media_type"] == "image/jpeg"


def test_call_sonnet_vision_all_downloads_fail_returns_none(monkeypatch):
    """모든 이미지 다운로드 실패 → IgFeedAnalyzerError → analyze_ig_feed None."""
    _set_settings(anthropic_api_key="key")
    posts = _sample_posts(3, with_url=True)

    import services.ig_feed_analyzer as ifa
    monkeypatch.setattr(ifa, "_download_image_as_base64", lambda url, timeout=8.0: None)

    # _get_client 호출되면 안 됨 (이미지 0장이면 Sonnet 스킵)
    def _should_not_call():
        raise AssertionError("Sonnet should not be called with 0 images")

    monkeypatch.setattr(ifa, "_get_client", _should_not_call)

    result = ifa.analyze_ig_feed(posts=posts, biography="", max_retries=0)
    assert result is None


def test_download_image_base64_returns_none_on_http_error(monkeypatch):
    """CDN 403 (TTL 만료) → None."""
    import services.ig_feed_analyzer as ifa
    import httpx as _httpx

    class _FakeClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url):
            req = _httpx.Request("GET", url)
            resp = _httpx.Response(403, request=req)
            raise _httpx.HTTPStatusError("403", request=req, response=resp)

    monkeypatch.setattr(ifa, "httpx", type("H", (), {
        "Client": _FakeClient,
        "HTTPStatusError": _httpx.HTTPStatusError,
        "TimeoutException": _httpx.TimeoutException,
    }))

    result = ifa._download_image_as_base64("https://cdn.example.com/expired.jpg")
    assert result is None


def test_analyze_ig_feed_mixed_url_coverage(monkeypatch):
    """일부 posts 만 display_url 있는 경우 — 있는 것만 Sonnet 전달."""
    _set_settings(anthropic_api_key="key")
    posts = [
        IgLatestPost(caption="a", display_url="https://cdn.example.com/a.jpg"),
        IgLatestPost(caption="b", display_url=None),
        IgLatestPost(caption="c", display_url="https://cdn.example.com/c.jpg"),
    ]

    received = {"count": 0}
    def _mock_call(prompt, images):
        received["count"] = len(images)
        return json.dumps({
            "tone_category": "중성",
            "tone_percentage": 50,
            "saturation_trend": "안정",
            "environment": "x",
            "pose_frequency": "x",
            "observed_adjectives": [],
            "style_consistency": 0.5,
            "mood_signal": "x입니다.",
            "three_month_shift": None,
        })

    monkeypatch.setattr(ig_feed_analyzer, "_call_sonnet_vision", _mock_call)

    result = ig_feed_analyzer.analyze_ig_feed(posts=posts, biography="")
    assert result is not None
    assert received["count"] == 2  # b 는 제외됨
