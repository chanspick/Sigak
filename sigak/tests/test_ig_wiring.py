"""IG wiring (분리 저장 + BackgroundTask + safety net) 테스트.

SPEC: essentials 제출 → preview flush → Vision → 최종 flush → chat/start 진입.
STEP IG-Wiring.

검증:
  (A) ig_scraper.fetch_ig_raw — Apify only (analysis=None)
  (B) ig_scraper.attach_vision_analysis — Vision 성공/실패 merge
  (C) BackgroundTask 로직 — preview flush → pending_vision → Vision → success
  (D) chat_start safety net — 최종 상태 아니면 동기 refresh, 최종이면 no-op
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import BackgroundTasks

from schemas.user_profile import (
    IgFeedAnalysis,
    IgFeedCache,
    IgFeedProfileBasics,
    IgLatestPost,
)
from services import ig_scraper


# ─────────────────────────────────────────────
#  Settings 격리
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    config_module._settings = config_module.Settings()
    # 테스트 기본 — ig_enabled=True + key 주입
    config_module._settings.ig_enabled = True
    config_module._settings.apify_api_key = "test-key"
    yield
    config_module._settings = None


# ─────────────────────────────────────────────
#  fixtures
# ─────────────────────────────────────────────

_SAMPLE_PROFILE_RAW = {
    "username": "testuser",
    "biography": "bio here",
    "followersCount": 100,
    "followsCount": 50,
    "postsCount": 12,
    "profilePicUrl": "https://cdn/profile.jpg",
    "verified": False,
    "private": False,
}

_SAMPLE_POST_RAW = {
    "caption": "cafe day",
    "timestamp": "2026-04-20T12:00:00.000Z",
    "hashtags": ["cafe"],
    "displayUrl": "https://cdn/post1.jpg",
    "latestComments": [],
}


def _apify_response(n_posts: int = 3) -> list[dict]:
    """n_posts 개 포스트가 포함된 Apify 응답 mock."""
    items = []
    for i in range(n_posts):
        item = dict(_SAMPLE_POST_RAW)
        item["displayUrl"] = f"https://cdn/post{i}.jpg"
        item["caption"] = f"caption {i}"
        # addParentData=True — 각 item 에 profile 메타 embedded
        item.update(_SAMPLE_PROFILE_RAW)
        items.append(item)
    return items


# ─────────────────────────────────────────────
#  (A) fetch_ig_raw
# ─────────────────────────────────────────────

class TestFetchIgRaw:
    def test_flag_off_returns_skipped(self):
        import config as config_module
        config_module._settings.ig_enabled = False
        status, cache = ig_scraper.fetch_ig_raw("@testuser")
        assert status == "skipped"
        assert cache is None

    def test_empty_handle_returns_skipped(self):
        for value in ("", "   ", None):
            status, cache = ig_scraper.fetch_ig_raw(value)
            assert status == "skipped", f"failed for {value!r}"
            assert cache is None

    def test_missing_api_key_returns_failed(self):
        import config as config_module
        config_module._settings.apify_api_key = ""
        status, cache = ig_scraper.fetch_ig_raw("testuser")
        assert status == "failed"
        assert cache is None

    def test_public_account_returns_preview_with_no_analysis(self, monkeypatch):
        """성공 케이스 — analysis=None 보장 (Vision 미실행)."""
        monkeypatch.setattr(
            ig_scraper, "_call_apify_actor",
            lambda **kwargs: _apify_response(3),
        )
        status, cache = ig_scraper.fetch_ig_raw("testuser")
        assert status == "success"
        assert cache is not None
        assert cache.scope == "full"
        assert cache.analysis is None  # ← 핵심: preview 는 analysis 없음
        assert cache.last_analyzed_post_count is None
        assert len(cache.latest_posts) == 3
        assert cache.profile_basics.username == "testuser"

    def test_private_account_returns_private(self, monkeypatch):
        def _response(**kwargs):
            item = dict(_SAMPLE_PROFILE_RAW, private=True)
            return [item]

        monkeypatch.setattr(ig_scraper, "_call_apify_actor", _response)
        status, cache = ig_scraper.fetch_ig_raw("private_user")
        assert status == "private"
        assert cache is not None
        assert cache.scope == "public_profile_only"
        assert cache.analysis is None

    def test_empty_response_returns_failed(self, monkeypatch):
        monkeypatch.setattr(ig_scraper, "_call_apify_actor", lambda **kwargs: [])
        status, cache = ig_scraper.fetch_ig_raw("nonexistent")
        assert status == "failed"
        assert cache is None

    def test_apify_error_returns_failed(self, monkeypatch):
        def _boom(**kwargs):
            raise RuntimeError("apify down")
        monkeypatch.setattr(ig_scraper, "_call_apify_actor", _boom)
        status, cache = ig_scraper.fetch_ig_raw("yuni")
        assert status == "failed"
        assert cache is None


# ─────────────────────────────────────────────
#  (B) attach_vision_analysis
# ─────────────────────────────────────────────

def _make_preview_cache() -> IgFeedCache:
    from datetime import datetime, timezone
    return IgFeedCache(
        scope="full",
        profile_basics=IgFeedProfileBasics(
            username="testuser",
            post_count=12,
        ),
        latest_posts=[
            IgLatestPost(
                caption="x",
                display_url="https://cdn/post1.jpg",
            ),
        ],
        analysis=None,
        last_analyzed_post_count=None,
        fetched_at=datetime.now(timezone.utc),
    )


class TestAttachVisionAnalysis:
    def test_attaches_analysis_on_success(self, monkeypatch):
        from datetime import datetime, timezone
        fake_analysis = IgFeedAnalysis(
            tone_category="쿨뮤트",
            tone_percentage=68,
            saturation_trend="안정",
            environment="실내 + 자연광",
            pose_frequency="측면 > 정면",
            observed_adjectives=[],
            style_consistency=0.7,
            mood_signal="차분한 무드입니다.",
            analyzed_at=datetime.now(timezone.utc),
        )
        from services import ig_feed_analyzer
        monkeypatch.setattr(
            ig_feed_analyzer, "analyze_ig_feed",
            lambda posts, biography: fake_analysis,
        )

        preview = _make_preview_cache()
        result = ig_scraper.attach_vision_analysis(preview)
        assert result.analysis is not None
        assert result.analysis.tone_category == "쿨뮤트"
        assert result.last_analyzed_post_count == 12

    def test_returns_original_on_vision_failure(self, monkeypatch):
        from services import ig_feed_analyzer
        monkeypatch.setattr(
            ig_feed_analyzer, "analyze_ig_feed",
            lambda posts, biography: None,   # Vision 실패 stub
        )

        preview = _make_preview_cache()
        result = ig_scraper.attach_vision_analysis(preview)
        assert result.analysis is None
        assert result.last_analyzed_post_count is None

    def test_private_cache_skipped(self):
        """scope=public_profile_only 는 Vision 호출 안 함."""
        from datetime import datetime, timezone
        private = IgFeedCache(
            scope="public_profile_only",
            profile_basics=IgFeedProfileBasics(username="priv"),
            latest_posts=None,
            analysis=None,
            fetched_at=datetime.now(timezone.utc),
        )
        result = ig_scraper.attach_vision_analysis(private)
        assert result is private   # 동일 객체

    def test_vision_exception_swallowed(self, monkeypatch):
        from services import ig_feed_analyzer

        def _boom(posts, biography):
            raise RuntimeError("sonnet error")
        monkeypatch.setattr(ig_feed_analyzer, "analyze_ig_feed", _boom)

        preview = _make_preview_cache()
        result = ig_scraper.attach_vision_analysis(preview)
        # 예외 삼키고 원본 반환
        assert result is preview


# ─────────────────────────────────────────────
#  (C) _run_ig_fetch_job — BackgroundTask 로직
# ─────────────────────────────────────────────

class _FakeDB:
    def __init__(self):
        self.committed = 0
        self.closed = False
        self.captured_upserts: list[tuple] = []  # (user_id, cache or None, status)

    def commit(self):
        self.committed += 1

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class TestRunIgFetchJob:
    def test_successful_flow_flushes_preview_then_final(self, monkeypatch):
        """pending → preview flush (pending_vision) → Vision → final (success)."""
        from routes import onboarding as onb

        fake_db = _FakeDB()
        import db as db_mod
        monkeypatch.setattr(db_mod, "get_db", lambda: fake_db)

        # fetch_ig_raw → preview cache
        preview = _make_preview_cache()
        monkeypatch.setattr(
            ig_scraper, "fetch_ig_raw",
            lambda h: ("success", preview),
        )

        # attach_vision → analysis attached
        from datetime import datetime, timezone
        analyzed = preview.model_copy(update={
            "analysis": IgFeedAnalysis(
                tone_category="쿨뮤트",
                tone_percentage=68,
                saturation_trend="안정",
                environment="실내",
                pose_frequency="정면",
                observed_adjectives=[],
                style_consistency=0.7,
                mood_signal="차분한 무드입니다.",
                analyzed_at=datetime.now(timezone.utc),
            ),
            "last_analyzed_post_count": 12,
        })
        monkeypatch.setattr(
            ig_scraper, "attach_vision_analysis",
            lambda cache: analyzed,
        )

        # upsert 캡처
        from services import user_profiles
        calls: list[tuple] = []
        monkeypatch.setattr(
            user_profiles, "upsert_ig_feed_cache",
            lambda db, *, user_id, cache, status: calls.append(
                (user_id, cache, status)
            ),
        )

        onb._run_ig_fetch_job(user_id="u-1", ig_handle="testuser")

        # 2회 flush: pending_vision → success
        assert len(calls) == 2
        assert calls[0][2] == "pending_vision"
        assert calls[0][1].analysis is None
        assert calls[1][2] == "success"
        assert calls[1][1].analysis is not None
        assert fake_db.committed == 2
        assert fake_db.closed is True

    def test_failed_apify_single_flush_no_vision(self, monkeypatch):
        from routes import onboarding as onb

        fake_db = _FakeDB()
        import db as db_mod
        monkeypatch.setattr(db_mod, "get_db", lambda: fake_db)

        monkeypatch.setattr(
            ig_scraper, "fetch_ig_raw",
            lambda h: ("failed", None),
        )
        vision_called = []
        monkeypatch.setattr(
            ig_scraper, "attach_vision_analysis",
            lambda cache: vision_called.append(cache) or cache,
        )

        from services import user_profiles
        calls: list[tuple] = []
        monkeypatch.setattr(
            user_profiles, "upsert_ig_feed_cache",
            lambda db, *, user_id, cache, status: calls.append(
                (user_id, cache, status)
            ),
        )

        onb._run_ig_fetch_job(user_id="u-1", ig_handle="testuser")

        assert len(calls) == 1
        assert calls[0][2] == "failed"
        assert calls[0][1] is None
        assert vision_called == []   # Vision 호출 안 됨
        assert fake_db.committed == 1

    def test_private_account_flushes_once_no_vision(self, monkeypatch):
        from routes import onboarding as onb
        from datetime import datetime, timezone

        fake_db = _FakeDB()
        import db as db_mod
        monkeypatch.setattr(db_mod, "get_db", lambda: fake_db)

        private_cache = IgFeedCache(
            scope="public_profile_only",
            profile_basics=IgFeedProfileBasics(username="priv"),
            fetched_at=datetime.now(timezone.utc),
        )
        monkeypatch.setattr(
            ig_scraper, "fetch_ig_raw",
            lambda h: ("private", private_cache),
        )
        vision_called = []
        monkeypatch.setattr(
            ig_scraper, "attach_vision_analysis",
            lambda cache: vision_called.append(cache) or cache,
        )

        from services import user_profiles
        calls: list[tuple] = []
        monkeypatch.setattr(
            user_profiles, "upsert_ig_feed_cache",
            lambda db, *, user_id, cache, status: calls.append(
                (user_id, cache, status)
            ),
        )

        onb._run_ig_fetch_job(user_id="u-priv", ig_handle="priv")

        assert len(calls) == 1
        assert calls[0][2] == "private"
        assert vision_called == []

    def test_db_unavailable_returns_without_crash(self, monkeypatch):
        from routes import onboarding as onb
        import db as db_mod
        monkeypatch.setattr(db_mod, "get_db", lambda: None)

        # 예외 없이 종료해야 함
        onb._run_ig_fetch_job(user_id="u-1", ig_handle="testuser")


# ─────────────────────────────────────────────
#  (D) chat_start safety net — _ensure_ig_cache_ready
# ─────────────────────────────────────────────

class TestChatStartSafetyNet:
    def test_no_handle_noop(self):
        from routes.sia import _ensure_ig_cache_ready
        profile = {"ig_handle": None, "ig_fetch_status": None}
        result = _ensure_ig_cache_ready(None, "u-1", profile)
        assert result is profile

    @pytest.mark.parametrize(
        "status", ["success", "private", "skipped", "failed"],
    )
    def test_terminal_status_noop(self, status, monkeypatch):
        """최종 상태 — safety net 발동 안 함."""
        from routes.sia import _ensure_ig_cache_ready
        from services import user_profiles

        called = []
        monkeypatch.setattr(
            user_profiles, "refresh_ig_feed",
            lambda db, uid, force: called.append(uid),
        )

        profile = {"ig_handle": "test", "ig_fetch_status": status}
        result = _ensure_ig_cache_ready(None, "u-1", profile)
        assert result is profile
        assert called == []   # refresh 호출 안 됨

    @pytest.mark.parametrize(
        "status", [None, "pending", "pending_vision"],
    )
    def test_pending_status_triggers_sync_refresh(self, status, monkeypatch):
        """최종 상태 아니고 ig_handle 있으면 동기 refresh_ig_feed 호출."""
        from routes import sia as sia_routes
        from services import user_profiles

        refresh_called = []

        def fake_refresh(db, uid, force):
            refresh_called.append((uid, force))
            return "success"

        refreshed_profile = {
            "ig_handle": "test",
            "ig_fetch_status": "success",
            "ig_feed_cache": {"scope": "full"},
        }
        monkeypatch.setattr(user_profiles, "refresh_ig_feed", fake_refresh)
        monkeypatch.setattr(
            user_profiles, "get_profile",
            lambda db, uid: refreshed_profile,
        )

        class _FakeDBCommit:
            def commit(self):
                pass

        profile = {"ig_handle": "test", "ig_fetch_status": status}
        result = sia_routes._ensure_ig_cache_ready(_FakeDBCommit(), "u-1", profile)

        assert refresh_called == [("u-1", True)]
        assert result == refreshed_profile   # refreshed 반환

    def test_sync_refresh_exception_falls_back(self, monkeypatch):
        """refresh_ig_feed 실패 시 원본 profile 반환 (Vision 없이 진행)."""
        from routes import sia as sia_routes
        from services import user_profiles

        def raise_(db, uid, force):
            raise RuntimeError("network down")

        monkeypatch.setattr(user_profiles, "refresh_ig_feed", raise_)

        class _FakeDBCommit:
            def commit(self):
                pass

        profile = {"ig_handle": "test", "ig_fetch_status": "pending"}
        result = sia_routes._ensure_ig_cache_ready(_FakeDBCommit(), "u-1", profile)
        # 예외 삼키고 원본 반환
        assert result is profile
