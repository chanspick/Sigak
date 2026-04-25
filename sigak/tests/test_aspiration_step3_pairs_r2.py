"""STEP 3 검증 — photo_pairs 실제 채워짐 + R2 materialization + vault 추출.

phase_j (test_phase_j.py) 가 엔진 전반을 커버하고, 본 모듈은 STEP 3 에서
추가한 3개 동작을 격리 검증:

  1. extract_user_posts_from_vault — vault.ig_feed_cache → IgLatestPost 리스트
  2. materialize_pairs_to_r2 — target_photo_url 만 업로드, R2 key 형식 정합
  3. run_aspiration_ig 에 user_posts 전달 시 photo_pairs 생성 + R2 URL 반영

실 httpx / R2 호출 0건 — monkey-patch 로 전부 격리.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.aspiration import PhotoPair
from schemas.user_profile import IgFeedAnalysis, IgLatestPost
from services import aspiration_common
from services import aspiration_engine_ig as ig_engine
from services import r2_client
from services.coordinate_system import VisualCoordinate


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    yield
    config_module._settings = None


def _set_settings(**overrides):
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


def _sample_analysis() -> IgFeedAnalysis:
    return IgFeedAnalysis(
        tone_category="쿨뮤트",
        tone_percentage=65,
        saturation_trend="감소",
        environment="실내",
        pose_frequency="측면 > 정면",
        observed_adjectives=[],
        style_consistency=0.75,
        mood_signal="차분한 결입니다.",
        three_month_shift=None,
        analyzed_at=datetime.now(timezone.utc),
    )


def _fake_apify_response():
    meta = {
        "username": "targetuser",
        "private": False,
        "followersCount": 5000,
        "postsCount": 120,
        "profilePicUrl": "https://cdn.example.com/pp.jpg",
    }
    return [
        {**meta, **{
            "caption": f"p{i}",
            "timestamp": f"2026-04-0{i + 1}T10:00:00.000Z",
            "displayUrl": f"https://cdn.example.com/target_{i}.jpg",
            "latestComments": [],
        }}
        for i in range(5)
    ]


# ─────────────────────────────────────────────
#  1. extract_user_posts_from_vault
# ─────────────────────────────────────────────

class _StubVault:
    def __init__(self, ig_feed_cache):
        self.ig_feed_cache = ig_feed_cache


def test_extract_user_posts_empty_when_no_cache():
    v = _StubVault(ig_feed_cache=None)
    assert aspiration_common.extract_user_posts_from_vault(v) == []


def test_extract_user_posts_skips_entries_without_display_url():
    v = _StubVault(ig_feed_cache={
        "latest_posts": [
            {"caption": "a", "display_url": "https://cdn/1.jpg"},
            {"caption": "b"},  # display_url 누락 — skip
            {"caption": "c", "display_url": None},  # None — skip
            {"caption": "d", "display_url": "https://cdn/4.jpg"},
        ],
    })
    posts = aspiration_common.extract_user_posts_from_vault(v)
    assert len(posts) == 2
    assert posts[0].display_url == "https://cdn/1.jpg"
    assert posts[1].display_url == "https://cdn/4.jpg"


def test_extract_user_posts_none_vault():
    assert aspiration_common.extract_user_posts_from_vault(None) == []


# ─────────────────────────────────────────────
#  2. materialize_pairs_to_r2 — R2 key 형식 + target 전용
# ─────────────────────────────────────────────

def test_materialize_empty_pairs_returns_none_prefix():
    out_pairs, prefix = aspiration_common.materialize_pairs_to_r2(
        [], user_id="u_x", analysis_id="asp_abc",
    )
    assert out_pairs == []
    assert prefix is None


def test_materialize_uploads_target_only_and_keeps_user_url(monkeypatch):
    """user_photo_url 은 vault 에서 온 URL 유지, target 만 R2 업로드."""
    # 업로드 호출 기록
    put_calls: list[tuple[str, bytes]] = []

    def _fake_put_bytes(key, data, content_type="image/jpeg"):
        put_calls.append((key, data))
        return key

    monkeypatch.setattr(r2_client, "put_bytes", _fake_put_bytes)
    # public_url 단순 반환 (테스트 환경)
    monkeypatch.setattr(r2_client, "public_url",
                        lambda key: f"https://cdn.r2.test/{key}")

    # httpx.Client.get 스텁
    class _StubResp:
        def __init__(self, content=b"IMGBYTES", ct="image/jpeg"):
            self.content = content
            self.headers = {"content-type": ct}
        def raise_for_status(self):
            pass

    class _StubClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url):
            return _StubResp()

    monkeypatch.setattr("httpx.Client", _StubClient)

    pairs = [
        PhotoPair(
            user_photo_url="https://cdn.instagram.com/user_0.jpg",
            user_sia_comment="u0",
            target_photo_url="https://cdn.instagram.com/target_0.jpg",
            target_sia_comment="t0",
            pair_axis_hint="shape 축 차이",
        ),
        PhotoPair(
            user_photo_url="https://cdn.instagram.com/user_1.jpg",
            user_sia_comment="u1",
            target_photo_url="https://cdn.instagram.com/target_1.jpg",
            target_sia_comment="t1",
            pair_axis_hint="shape 축 차이",
        ),
    ]

    out, prefix = aspiration_common.materialize_pairs_to_r2(
        pairs, user_id="u_abc", analysis_id="asp_xyz",
    )

    # user URL 원본 유지
    assert out[0].user_photo_url == "https://cdn.instagram.com/user_0.jpg"
    assert out[1].user_photo_url == "https://cdn.instagram.com/user_1.jpg"

    # target URL 은 R2 로 교체
    assert out[0].target_photo_url.startswith("https://cdn.r2.test/user_media/u_abc/aspiration_targets/asp_xyz/")
    assert out[0].target_photo_url.endswith("photo_00.jpg")
    assert out[1].target_photo_url.endswith("photo_01.jpg")

    # put_bytes 는 target 만 (2회, user 사진은 업로드 X)
    assert len(put_calls) == 2
    for key, _ in put_calls:
        assert key.startswith("user_media/u_abc/aspiration_targets/asp_xyz/")
        assert "user_" not in key.split("/")[-1]

    # r2_target_dir 은 새 헬퍼 경로
    assert prefix == "user_media/u_abc/aspiration_targets/asp_xyz/"


def test_materialize_upload_failure_keeps_original_target_url(monkeypatch):
    """put_bytes 실패 시 해당 pair 의 target_photo_url 은 원본 유지."""
    def _boom_put(key, data, content_type="image/jpeg"):
        raise RuntimeError("R2 down")

    monkeypatch.setattr(r2_client, "put_bytes", _boom_put)
    monkeypatch.setattr(r2_client, "public_url", lambda k: None)

    class _StubResp:
        content = b"IMG"
        headers = {"content-type": "image/jpeg"}
        def raise_for_status(self): pass

    class _StubClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url): return _StubResp()

    monkeypatch.setattr("httpx.Client", _StubClient)

    original_target = "https://cdn.instagram.com/t.jpg"
    pairs = [PhotoPair(
        user_photo_url="https://cdn/u.jpg",
        user_sia_comment="",
        target_photo_url=original_target,
        target_sia_comment="",
        pair_axis_hint=None,
    )]

    out, _prefix = aspiration_common.materialize_pairs_to_r2(
        pairs, user_id="u1", analysis_id="asp_1",
    )
    assert out[0].target_photo_url == original_target  # 원본 유지


# ─────────────────────────────────────────────
#  3. run_aspiration_ig — user_posts 전달 시 photo_pairs 실제 생성
# ─────────────────────────────────────────────

def test_run_aspiration_ig_with_user_posts_produces_pairs(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")

    monkeypatch.setattr(ig_engine, "_call_apify_actor",
                        lambda **kw: _fake_apify_response())

    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed",
        # v1.5: 시그니처 (analysis, raw_text) tuple. raw_text 는 R2 mock 안 거치니 임의 str.
        lambda posts, biography: (_sample_analysis(), "{\"mock\": true}"),
    )

    # materialize_pairs_to_r2 단순 통과 스텁 — 실 업로드 X
    monkeypatch.setattr(
        ig_engine, "materialize_pairs_to_r2",
        lambda pairs, *, user_id, analysis_id: (
            pairs, f"user_media/{user_id}/aspiration_targets/{analysis_id}/"
        ),
    )

    user_posts = [
        IgLatestPost(caption=f"u{i}",
                     display_url=f"https://cdn.example.com/user_{i}.jpg")
        for i in range(3)
    ]

    class _FakeDB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()

    result = ig_engine.run_aspiration_ig(
        _FakeDB(),
        user_id="u_me",
        user_gender="female",
        user_coordinate=VisualCoordinate(shape=0.3, volume=0.5, age=0.4),
        target_handle_raw="@targetuser",
        user_posts=user_posts,
    )

    assert result.status == "completed"
    a = result.analysis
    assert a is not None

    # STEP 3 핵심: photo_pairs 가 실제로 생성됨 (min(3 user, 5 target) = 3)
    assert len(a.photo_pairs) == 3
    for pair in a.photo_pairs:
        assert pair.user_photo_url.startswith("https://cdn.example.com/user_")
        assert pair.target_photo_url.startswith("https://cdn.example.com/target_")

    # r2_target_dir 는 새 디렉토리 포맷
    assert a.r2_target_dir is not None
    assert a.r2_target_dir.startswith("user_media/u_me/aspiration_targets/")


def test_run_aspiration_ig_without_user_posts_still_completes(monkeypatch):
    """user_posts None → photo_pairs 빈 배열이지만 status=completed 유지 (회귀)."""
    _set_settings(ig_enabled=True, apify_api_key="k")
    monkeypatch.setattr(ig_engine, "_call_apify_actor",
                        lambda **kw: _fake_apify_response())
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed",
        # v1.5: 시그니처 (analysis, raw_text) tuple. raw_text 는 R2 mock 안 거치니 임의 str.
        lambda posts, biography: (_sample_analysis(), "{\"mock\": true}"),
    )
    monkeypatch.setattr(
        ig_engine, "materialize_pairs_to_r2",
        lambda pairs, *, user_id, analysis_id: (pairs, None),
    )

    class _FakeDB:
        def execute(self, *a, **kw):
            class _R:
                def first(self): return None
            return _R()

    result = ig_engine.run_aspiration_ig(
        _FakeDB(),
        user_id="u1",
        user_gender="female",
        user_coordinate=None,
        target_handle_raw="targetuser",
        # user_posts 생략 — None default
    )
    assert result.status == "completed"
    assert len(result.analysis.photo_pairs) == 0
