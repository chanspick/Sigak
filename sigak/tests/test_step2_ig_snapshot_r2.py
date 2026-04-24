"""STEP 2 검증 — IG 스냅샷 R2 저장 + 24h 캐시 헬퍼.

범위:
  1. materialize_snapshot_to_r2 — scope/latest_posts 유무 분기
  2. _materialize_latest_posts_to_r2 — display_url R2 교체 + 실패 fallback
  3. should_refresh_ig_snapshot — 24h TTL / 최초 / 컬럼 없음

실 httpx / R2 호출 0건. monkey-patch 로 격리.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.user_profile import (
    IgFeedCache,
    IgFeedProfileBasics,
    IgLatestPost,
)
from services import ig_scraper, r2_client, user_profiles


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    yield
    config_module._settings = None


def _make_cache(scope="full", posts_n=3, fetched=None) -> IgFeedCache:
    basics = IgFeedProfileBasics(
        username="yuni",
        profile_picture=None,
        bio=None,
        follower_count=100,
        following_count=50,
        post_count=42,
        is_private=(scope != "full"),
        is_verified=False,
    )
    posts = [
        IgLatestPost(
            caption=f"p{i}",
            display_url=f"https://cdn.example.com/ig_{i}.jpg",
        )
        for i in range(posts_n)
    ] if scope == "full" else None
    return IgFeedCache(
        scope=scope,
        profile_basics=basics,
        latest_posts=posts,
        fetched_at=fetched or datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc),
    )


class _StubResp:
    def __init__(self, content=b"JPGBYTES", ct="image/jpeg"):
        self.content = content
        self.headers = {"content-type": ct}
    def raise_for_status(self):
        pass


class _StubClient:
    def __init__(self, *a, **kw): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get(self, url): return _StubResp()


# ─────────────────────────────────────────────
#  1. materialize_snapshot_to_r2
# ─────────────────────────────────────────────

def test_materialize_skips_private_scope():
    """scope='public_profile_only' (비공개) 는 원본 그대로."""
    cache = _make_cache(scope="public_profile_only", posts_n=0)
    out = ig_scraper.materialize_snapshot_to_r2(cache, user_id="u1")
    assert out is cache  # model_copy 없이 그대로


def test_materialize_skips_empty_latest_posts():
    """latest_posts None 또는 빈 리스트도 원본 그대로."""
    basics = IgFeedProfileBasics(
        username="x", follower_count=0, following_count=0, post_count=0,
        is_private=False, is_verified=False,
    )
    cache = IgFeedCache(
        scope="full",
        profile_basics=basics,
        latest_posts=None,
        fetched_at=datetime.now(timezone.utc),
    )
    out = ig_scraper.materialize_snapshot_to_r2(cache, user_id="u1")
    assert out is cache


def test_materialize_swaps_display_urls_and_sets_r2_dir(monkeypatch):
    """full scope + posts → display_url R2 URL 로 교체 + r2_snapshot_dir 채움."""
    put_calls = []
    monkeypatch.setattr(r2_client, "put_bytes",
                        lambda key, data, content_type="image/jpeg": put_calls.append(key) or key)
    monkeypatch.setattr(r2_client, "public_url",
                        lambda key: f"https://cdn.r2.test/{key}")
    monkeypatch.setattr("httpx.Client", _StubClient)

    cache = _make_cache(posts_n=3)
    out = ig_scraper.materialize_snapshot_to_r2(
        cache, user_id="u_abc", snapshot_ts="20260424T120000Z",
    )

    # r2_snapshot_dir 새로 채워짐
    assert out.r2_snapshot_dir == "user_media/u_abc/ig_snapshots/20260424T120000Z/"
    # 각 latest_posts 의 display_url 교체됨
    for i, p in enumerate(out.latest_posts):
        expected_suffix = f"/photo_{i:02d}.jpg"
        assert p.display_url.endswith(expected_suffix)
        assert "user_media/u_abc/ig_snapshots/" in p.display_url
    # put_bytes 3회 호출, 각 key user_media/ 네임스페이스
    assert len(put_calls) == 3
    for k in put_calls:
        assert k.startswith("user_media/u_abc/ig_snapshots/20260424T120000Z/")


def test_materialize_partial_failure_keeps_cdn_url(monkeypatch):
    """일부 이미지 업로드 실패 → 해당 CDN URL 유지, 나머지 R2."""
    call_count = {"n": 0}
    def _put_fail_first(key, data, content_type="image/jpeg"):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("R2 down for first image")
        return key

    monkeypatch.setattr(r2_client, "put_bytes", _put_fail_first)
    monkeypatch.setattr(r2_client, "public_url",
                        lambda key: f"https://cdn.r2.test/{key}")
    monkeypatch.setattr("httpx.Client", _StubClient)

    cache = _make_cache(posts_n=3)
    out = ig_scraper.materialize_snapshot_to_r2(
        cache, user_id="u_x", snapshot_ts="20260424T120000Z",
    )

    # 첫 이미지: CDN URL 원본 유지
    assert out.latest_posts[0].display_url == "https://cdn.example.com/ig_0.jpg"
    # 나머지 2개: R2 URL
    assert "cdn.r2.test" in out.latest_posts[1].display_url
    assert "cdn.r2.test" in out.latest_posts[2].display_url
    # r2_snapshot_dir 은 최소 1장 성공이라 채워짐
    assert out.r2_snapshot_dir is not None


def test_materialize_all_failure_returns_none_dir(monkeypatch):
    """전체 업로드 실패 → r2_snapshot_dir None + 모든 display_url CDN."""
    monkeypatch.setattr(r2_client, "put_bytes",
                        lambda key, data, content_type="image/jpeg": (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr("httpx.Client", _StubClient)

    cache = _make_cache(posts_n=2)
    out = ig_scraper.materialize_snapshot_to_r2(
        cache, user_id="u_x", snapshot_ts="20260424T120000Z",
    )
    assert out.r2_snapshot_dir is None
    assert all(p.display_url.startswith("https://cdn.example.com/") for p in out.latest_posts)


# ─────────────────────────────────────────────
#  2. should_refresh_ig_snapshot — 24h TTL
# ─────────────────────────────────────────────

class _StubRow:
    def __init__(self, ts):
        self.ig_last_snapshot_at = ts


class _StubExecute:
    def __init__(self, row_or_exc):
        self._v = row_or_exc
    def first(self):
        if isinstance(self._v, Exception):
            raise self._v
        return self._v


class _StubDB:
    def __init__(self, result):
        self._result = result
    def execute(self, *a, **kw):
        if isinstance(self._result, Exception):
            raise self._result
        return _StubExecute(self._result)


def test_should_refresh_no_snapshot_row_returns_true():
    """row 없음 → True (처음 스크랩)."""
    db = _StubDB(None)
    assert user_profiles.should_refresh_ig_snapshot(db, "u1") is True


def test_should_refresh_null_timestamp_returns_true():
    db = _StubDB(_StubRow(None))
    assert user_profiles.should_refresh_ig_snapshot(db, "u1") is True


def test_should_refresh_fresh_snapshot_returns_false():
    """스냅샷 1h 전 → False (24h cache hit)."""
    recent = datetime.now(timezone.utc) - timedelta(hours=1)
    db = _StubDB(_StubRow(recent))
    assert user_profiles.should_refresh_ig_snapshot(db, "u1") is False


def test_should_refresh_stale_snapshot_returns_true():
    """스냅샷 25h 전 → True (재스크랩 필요)."""
    stale = datetime.now(timezone.utc) - timedelta(hours=25)
    db = _StubDB(_StubRow(stale))
    assert user_profiles.should_refresh_ig_snapshot(db, "u1") is True


def test_should_refresh_column_missing_returns_false():
    """migration 미적용 환경 — exception 발생 → False (기존 cache 유지)."""
    db = _StubDB(RuntimeError("column ig_last_snapshot_at does not exist"))
    assert user_profiles.should_refresh_ig_snapshot(db, "u1") is False


# ─────────────────────────────────────────────
#  3. mark_ig_snapshot_taken — 실패 무해
# ─────────────────────────────────────────────

def test_mark_ig_snapshot_taken_swallows_errors():
    class _RaiseDB:
        def execute(self, *a, **kw):
            raise RuntimeError("column missing")
    # 예외 밖으로 새지 않음
    user_profiles.mark_ig_snapshot_taken(_RaiseDB(), "u1")


def test_mark_ig_snapshot_taken_executes_update():
    calls = []
    class _RecordDB:
        def execute(self, stmt, params):
            calls.append((str(stmt), params))
    user_profiles.mark_ig_snapshot_taken(_RecordDB(), "u_xyz")
    assert len(calls) == 1
    sql, params = calls[0]
    assert "UPDATE users" in sql
    assert "ig_last_snapshot_at" in sql
    assert params == {"uid": "u_xyz"}
