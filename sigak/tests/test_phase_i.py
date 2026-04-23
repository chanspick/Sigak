"""Phase I — PI 엔진 스켈레톤 테스트.

범위:
  - determine_pi_photo_count 유동 경계값
  - generate_pi_report end-to-end (Sonnet / Apify / R2 전부 mock)
  - ig_scraper fetch_ig_profile_for_pi limit=30
  - 버전 관리 / is_current 처리

실 Sonnet / Apify / R2 호출 0.
"""
from __future__ import annotations

import io
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from schemas.pi_report import PIReport, PhotoCategory
from schemas.user_profile import IgFeedAnalysis, IgFeedCache, IgLatestPost, IgFeedProfileBasics
from schemas.user_taste import UserTasteProfile
from services import ig_scraper, pi_engine, r2_client
from services.coordinate_system import VisualCoordinate
from services.pi_engine import PIEngineError, determine_pi_photo_count


# ─────────────────────────────────────────────
#  determine_pi_photo_count 경계 테스트
# ─────────────────────────────────────────────

@pytest.mark.parametrize("available,expected", [
    (0,   (0, 0)),
    (1,   (1, 0)),
    (3,   (1, 2)),
    (8,   (2, 6)),     # 8 // 3 = 2
    (12,  (4, 8)),
    (15,  (5, 10)),    # boundary: 15 → public=5, locked=10 (using //3)
    (16,  (5, 10)),    # 16~40: fixed 5/10
    (20,  (5, 10)),
    (30,  (5, 10)),
    (40,  (5, 10)),
    (41,  (5, 10)),    # 41//6 = 6, min(6,15)=6, max(10,6)=10
    (50,  (5, 10)),    # 50//6 = 8, min(8,15)=8, max(10,8)=10
    (70,  (5, 11)),    # 70//6 = 11, min(11,15)=11, max(10,11)=11
    (90,  (5, 15)),    # 90//6 = 15, min(15,15)=15
    (150, (5, 15)),    # 150//6 = 25, min(25,15)=15
    (500, (5, 15)),    # 500//6 = 83, min(83,15)=15
])
def test_determine_pi_photo_count_boundaries(available, expected):
    assert determine_pi_photo_count(available) == expected


def test_determine_pi_photo_count_small_edge():
    """available=2 → public=1, locked=1 (2//3=0, max(1,0)=1)."""
    assert determine_pi_photo_count(2) == (1, 1)


# ─────────────────────────────────────────────
#  ig_scraper limit extension
# ─────────────────────────────────────────────

def _fake_apify_response(n: int):
    meta = {
        "username": "target", "private": False,
        "followersCount": 100, "postsCount": n,
    }
    return [
        {**meta, **{
            "caption": f"p{i}",
            "displayUrl": f"https://cdn.example.com/img{i}.jpg",
            "latestComments": [],
        }}
        for i in range(n)
    ]


@pytest.fixture(autouse=True)
def _reset_settings():
    import config as config_module
    config_module._settings = None
    r2_client.reset_client()
    yield
    config_module._settings = None
    r2_client.reset_client()


def _set_settings(**overrides):
    import config as config_module
    config_module._settings = config_module.Settings(**overrides)


def test_fetch_ig_profile_for_pi_calls_with_limit_30(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    captured = {}

    def _mock(handle, api_key, actor_id, timeout, **kw):
        captured["results_limit"] = kw.get("results_limit")
        return _fake_apify_response(30)

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _mock)
    # Vision 우회
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed", lambda posts, biography: None,
    )

    status, cache = ig_scraper.fetch_ig_profile_for_pi("target")
    assert status == "success"
    assert captured["results_limit"] == 30
    assert len(cache.latest_posts) == 30


def test_fetch_ig_profile_default_limit_10(monkeypatch):
    _set_settings(ig_enabled=True, apify_api_key="k")
    captured = {}

    def _mock(handle, api_key, actor_id, timeout, **kw):
        captured["results_limit"] = kw.get("results_limit", "default")
        return _fake_apify_response(10)

    monkeypatch.setattr(ig_scraper, "_call_apify_actor", _mock)
    from services import ig_feed_analyzer
    monkeypatch.setattr(
        ig_feed_analyzer, "analyze_ig_feed", lambda posts, biography: None,
    )
    ig_scraper.fetch_ig_profile("target")
    assert captured["results_limit"] == 10


# ─────────────────────────────────────────────
#  generate_pi_report — happy path (engine mock)
# ─────────────────────────────────────────────

def _stub_vault_for_pi():
    from services.user_data_vault import UserBasicInfo, UserDataVault
    return UserDataVault(
        basic_info=UserBasicInfo(
            user_id="u1", gender="female", ig_handle="userhandle",
        ),
        ig_feed_cache=None,
        structured_fields={
            "desired_image": "차분한 또렷함",
            "current_concerns": "톤 일관성",
        },
    )


def _stub_feed(n: int = 20) -> tuple[str, IgFeedCache]:
    posts = [
        IgLatestPost(
            caption=f"p{i}",
            display_url=f"https://cdn.example.com/{i}.jpg",
        )
        for i in range(n)
    ]
    cache = IgFeedCache(
        scope="full",
        profile_basics=IgFeedProfileBasics(username="userhandle", post_count=n),
        latest_posts=posts,
        analysis=IgFeedAnalysis(
            tone_category="쿨뮤트",
            tone_percentage=68,
            saturation_trend="안정",
            environment="실내",
            pose_frequency="측면 > 정면",
            observed_adjectives=["단정"],
            style_consistency=0.8,
            mood_signal="정돈된 결",
            analyzed_at=datetime.now(timezone.utc),
        ),
        fetched_at=datetime.now(timezone.utc),
    )
    return ("success", cache)


class _FakeDB:
    def __init__(self):
        self.executes = []
        self._current_row = None

    def queue_current(self, row):
        self._current_row = row

    def execute(self, stmt, params=None):
        self.executes.append((str(stmt), params or {}))
        from unittest.mock import MagicMock
        result = MagicMock()
        sql = str(stmt)
        if "is_current = TRUE" in sql and "SELECT" in sql:
            result.first.return_value = self._current_row
        elif "COALESCE(MAX(version)" in sql:
            result.scalar.return_value = 1 if self._current_row else 0
        else:
            result.first.return_value = None
            result.scalar.return_value = 0
        result.rowcount = 0
        return result

    def commit(self): pass
    def rollback(self): pass


def test_generate_pi_report_happy_e2e(monkeypatch, tmp_path):
    """Sonnet / Apify / R2 전부 모킹. generate_pi_report 파이프 end-to-end 검증."""
    _set_settings(
        ig_enabled=True, apify_api_key="k",
        anthropic_api_key="k", r2_local_fallback_dir=str(tmp_path),
    )

    # Vault stub
    monkeypatch.setattr(
        pi_engine, "load_vault",
        lambda db, uid: _stub_vault_for_pi(),
    )

    # Apify + Vision stub
    monkeypatch.setattr(
        pi_engine, "fetch_ig_profile_for_pi",
        lambda handle: _stub_feed(20),
    )

    # Sonnet 선별 stub — 5 signature + 10 locked 카테고리 분배
    selection_plan = [
        {
            "photo_index": i,
            "category": "signature",
            "rank_within_category": i + 1,
            "rationale": "정돈된 구도가 유저다움을 잘 담았습니다",
            "associated_trend_id": None,
        }
        for i in range(5)
    ] + [
        {
            "photo_index": 5 + i,
            "category": ["detail_analysis", "style_element", "trend_match",
                         "aspiration_gap", "weaker_angle", "methodology"][i % 6],
            "rank_within_category": 1,
            "rationale": "보조 관찰",
            "associated_trend_id": None,
        }
        for i in range(10)
    ]
    monkeypatch.setattr(
        pi_engine, "_sonnet_select_for_pi",
        lambda **kw: selection_plan,
    )

    # httpx GET stub (materialize 단계에서 이미지 download)
    import httpx

    class _FakeResp:
        status_code = 200
        content = b"\x00" * 100

        def raise_for_status(self): pass

    class _FakeClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def get(self, url): return _FakeResp()

    monkeypatch.setattr(httpx, "Client", _FakeClient)

    db = _FakeDB()
    report = pi_engine.generate_pi_report(
        db, user_id="u1", force_new_version=False,
    )
    assert isinstance(report, PIReport)
    assert report.user_id == "u1"
    assert report.version == 1
    assert report.is_current is True
    # 20장 → (5, 10) 설정이지만 signature 개수는 selection_plan 에 따라
    assert len(report.public_photos) == 5
    assert len(report.locked_photos) == 10
    # sources 확인
    assert report.data_sources_used.feed_photo_count == 20
    assert report.data_sources_used.ig_analysis_present is True


def test_generate_pi_report_no_vault_raises():
    class _NoProfileDB:
        def execute(self, *a, **kw):
            from unittest.mock import MagicMock
            r = MagicMock()
            r.first.return_value = None
            r.scalar.return_value = 0
            return r
        def commit(self): pass

    # vault 도 None 반환하도록
    import services.pi_engine as pe
    original = pe.load_vault
    try:
        pe.load_vault = lambda db, uid: None
        with pytest.raises(PIEngineError):
            pe.generate_pi_report(_NoProfileDB(), user_id="missing")
    finally:
        pe.load_vault = original


def test_generate_pi_report_returns_existing_current(monkeypatch):
    """force_new_version=False + is_current 존재 → 기존 반환, 엔진 재실행 없음."""
    # 기존 report row — full PIReport dump
    existing = {
        "report_id": "pi_existing",
        "user_id": "u1",
        "version": 2,
        "is_current": True,
        "generated_at": "2026-04-15T00:00:00+00:00",
        "public_photos": [],
        "locked_photos": [],
        "user_taste_profile_snapshot": {},
        "user_summary": "기존 요약",
        "needs_statement": "",
        "user_original_phrases": [],
        "sia_overall_message": "",
        "boundary_message": "",
        "matched_trend_ids": [],
        "matched_methodology_ids": [],
        "matched_reference_ids": [],
        "data_sources_used": {},
    }
    from unittest.mock import MagicMock

    class _DB:
        def execute(self, stmt, params=None):
            r = MagicMock()
            sql = str(stmt)
            if "is_current = TRUE" in sql:
                row = MagicMock()
                row.report_id = "pi_existing"
                row.user_id = "u1"
                row.version = 2
                row.is_current = True
                row.unlocked_at = None
                row.report_data = existing
                row.created_at = None
                r.first.return_value = row
            else:
                r.first.return_value = None
            return r
        def commit(self): pass

    # 엔진 재실행 방지 — Vault 로드 등 호출되면 실패해야 함
    call_count = {"vault": 0}

    def _vault(db, uid):
        call_count["vault"] += 1
        return None
    monkeypatch.setattr(pi_engine, "load_vault", _vault)

    report = pi_engine.generate_pi_report(_DB(), user_id="u1", force_new_version=False)
    assert report.report_id == "pi_existing"
    assert report.version == 2
    # 재생성 파이프 호출 없음
    assert call_count["vault"] == 0
