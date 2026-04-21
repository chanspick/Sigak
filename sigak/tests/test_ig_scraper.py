"""IG scraper tests (v2 Priority 1 D2).

Apify 실 API key 없이 동작. `_call_apify_actor` 를 monkey-patch 해서 raw 응답 주입.
Feature flag (IG_ENABLED) on/off 양쪽 커버.

실 API 검증은 D3-D4 E2E 단계에서.
"""
import sys
import os
from datetime import datetime, timedelta, timezone

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import get_settings
from schemas.user_profile import IgFeedCache
from services import ig_scraper


# ─────────────────────────────────────────────
#  Settings 격리 (테스트마다 reset)
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings():
    """테스트가 끝나면 singleton settings 를 재생성해서 오염 방지."""
    import config as config_module
    config_module._settings = None
    yield
    config_module._settings = None


def _set_settings(**overrides):
    """get_settings() 싱글톤을 테스트 값으로 교체."""
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


# ─────────────────────────────────────────────
#  Feature flag off
# ─────────────────────────────────────────────

def test_fetch_ig_profile_flag_off_returns_skipped():
    _set_settings(ig_enabled=False, apify_api_key="whatever")
    status, cache = ig_scraper.fetch_ig_profile("@yuni")
    assert status == "skipped"
    assert cache is None


# ─────────────────────────────────────────────
#  Empty handle
# ─────────────────────────────────────────────

def test_fetch_ig_profile_empty_handle_returns_skipped():
    _set_settings(ig_enabled=True, apify_api_key="key")
    for value in (None, "", "  ", "@"):
        status, cache = ig_scraper.fetch_ig_profile(value)
        assert status == "skipped", f"failed for {value!r}"
        assert cache is None


# ─────────────────────────────────────────────
#  Flag on, missing API key
# ─────────────────────────────────────────────

def test_fetch_ig_profile_missing_api_key_returns_failed():
    _set_settings(ig_enabled=True, apify_api_key="")
    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "failed"
    assert cache is None


# ─────────────────────────────────────────────
#  Public profile success
# ─────────────────────────────────────────────

def test_fetch_ig_profile_public_success(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="test_key")

    def _mock_call(handle, api_key, actor_id, timeout):
        assert handle == "yuni"
        assert api_key == "test_key"
        return [
            {
                "username": "yuni",
                "biography": "모든 것은 결국 모드로 수렴한다",
                "followersCount": 3200,
                "followsCount": 180,
                "postsCount": 42,
                "private": False,
                "verified": False,
                "profilePicUrl": "https://example.com/pic.jpg",
            },
            {"caption": "오늘의 무드 — 차분하게"},
            {"caption": "뮤트 톤 기록"},
            {"caption": ""},  # 빈 caption 은 highlight 에서 제외돼야
        ]

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _mock_call)

    status, cache = ig_scraper.fetch_ig_profile("@Yuni")   # @ + 대문자 정규화 검증
    assert status == "success"
    assert isinstance(cache, IgFeedCache)
    assert cache.scope == "full"
    assert cache.profile_basics.username == "yuni"
    assert cache.profile_basics.follower_count == 3200
    assert cache.feed_highlights == ["오늘의 무드 — 차분하게", "뮤트 톤 기록"]


# ─────────────────────────────────────────────
#  Private profile
# ─────────────────────────────────────────────

def test_fetch_ig_profile_private_returns_basics_only(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="test_key")

    def _mock_call(handle, api_key, actor_id, timeout):
        return [
            {
                "username": "privacy_user",
                "private": True,
                "followersCount": 50,
                "followsCount": 200,
                "postsCount": 10,
                "profilePicUrl": "https://example.com/p.jpg",
                # 비공개라 posts 없어야 정상이나 Actor 가 반환해도 무시
            }
        ]

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _mock_call)
    status, cache = ig_scraper.fetch_ig_profile("privacy_user")
    assert status == "private"
    assert cache.scope == "public_profile_only"
    assert cache.profile_basics.is_private is True
    assert cache.feed_highlights is None
    assert cache.current_style_mood is None


# ─────────────────────────────────────────────
#  Apify HTTP error / timeout
# ─────────────────────────────────────────────

def test_fetch_ig_profile_http_error_returns_failed(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="test_key")

    def _mock_call(handle, api_key, actor_id, timeout):
        req = httpx.Request("POST", "https://api.apify.com/test")
        resp = httpx.Response(503, request=req)
        raise httpx.HTTPStatusError("service unavailable", request=req, response=resp)

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _mock_call)
    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "failed"
    assert cache is None


def test_fetch_ig_profile_timeout_returns_failed(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="test_key", ig_fetch_timeout=10.0)

    def _mock_call(handle, api_key, actor_id, timeout):
        raise httpx.TimeoutException("Apify slow", request=None)

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _mock_call)
    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "failed"
    assert cache is None


def test_fetch_ig_profile_empty_response_returns_failed(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="test_key")

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", lambda *a, **kw: [])
    status, cache = ig_scraper.fetch_ig_profile("nonexistent")
    assert status == "failed"
    assert cache is None


def test_fetch_ig_profile_generic_exception_returns_failed(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="test_key")

    def _boom(*a, **kw):
        raise ValueError("parser blew up")

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _boom)
    status, cache = ig_scraper.fetch_ig_profile("yuni")
    assert status == "failed"


# ─────────────────────────────────────────────
#  is_stale
# ─────────────────────────────────────────────

def test_is_stale_none_is_true():
    assert ig_scraper.is_stale(None) is True


def test_is_stale_fresh_is_false():
    _set_settings(ig_refresh_days=14)
    fresh = datetime.now(timezone.utc) - timedelta(days=3)
    assert ig_scraper.is_stale(fresh) is False


def test_is_stale_old_is_true():
    _set_settings(ig_refresh_days=14)
    old = datetime.now(timezone.utc) - timedelta(days=20)
    assert ig_scraper.is_stale(old) is True


def test_is_stale_boundary_is_false_then_true():
    _set_settings(ig_refresh_days=14)
    # 정확히 14일 경계: is_stale 정의상 > 만 true, == 는 false
    just_inside = datetime.now(timezone.utc) - timedelta(days=14) + timedelta(seconds=1)
    assert ig_scraper.is_stale(just_inside) is False
    just_outside = datetime.now(timezone.utc) - timedelta(days=14, seconds=1)
    assert ig_scraper.is_stale(just_outside) is True
