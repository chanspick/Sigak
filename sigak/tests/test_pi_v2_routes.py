"""PI v2 routes integration tests (Priority 1 D5 Phase 3).

Covers:
  GET  /api/v2/pi                locked / unlocked
  POST /api/v2/pi/unlock         happy, 409 no profile, 402 insufficient,
                                 idempotent re-unlock
  v1 backward compat             POST /api/v1/pi/unlock 이 services.pi.build_v1_report_data
                                 경유하는지 확인

DB + tokens_service 둘 다 monkeypatch. 실 Postgres 불필요.
"""
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _fake_profile() -> dict:
    return {
        "user_id": "u1",
        "gender": "female",
        "birth_date": "1999-03-15",
        "ig_handle": "test_user",
        "ig_feed_cache": {
            "scope": "full",
            "current_style_mood": [{"tag": "쿨뮤트", "ratio": 0.68}],
            "style_trajectory": "3개월간 톤 다운",
            "feed_highlights": ["차분한 주말"],
            "profile_basics": {"follower_count": 3200},  # 삭제 대상 확인용
        },
        "ig_fetch_status": "ok",
        "structured_fields": {
            "desired_image": "편안한 인상",
            "reference_style": "한소희 초반",
            "current_concerns": ["추구미 갭"],
            "self_perception": "정돈된 인상",
            "lifestyle_context": "프리랜서",
            "height": "165_170",
            "weight": "50_55",
            "shoulder_width": "medium",
            "extra_legacy": "skipped",  # 화이트리스트 필터링 확인
        },
    }


class _FakeUser:
    @staticmethod
    def dep() -> dict:
        return {
            "id": "u1",
            "kakao_id": "k1",
            "email": "",
            "name": "정세현",
            "gender": "female",
            "tier": "standard",
        }


class _FakeDB:
    """Minimal Session mock — execute + commit + rollback."""

    def __init__(self):
        self.executes: list[tuple[str, dict]] = []
        self.committed = 0
        self.rolled_back = 0
        self._responses: dict[str, Any] = {}

    def execute(self, stmt, params: Optional[dict] = None):
        sql = str(stmt)
        self.executes.append((sql, params or {}))
        for key, resp in self._responses.items():
            if key in sql:
                return resp
        result = MagicMock()
        result.first.return_value = None
        result.rowcount = 0
        return result

    def commit(self):
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1

    def queue_result(self, sql_substring: str, value):
        self._responses[sql_substring] = value


def _make_row(**kwargs):
    result = MagicMock()
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    result.first.return_value = row
    return result


# ─────────────────────────────────────────────
#  App fixture
# ─────────────────────────────────────────────

@pytest.fixture
def client_v2():
    """v2 router only — 테스트 목적."""
    from routes.pi import router_v2
    import deps

    app = FastAPI()
    app.include_router(router_v2)

    fake_db = _FakeDB()
    app.dependency_overrides[deps.db_session] = lambda: fake_db
    app.dependency_overrides[deps.get_current_user] = _FakeUser.dep

    with TestClient(app) as c:
        yield c, fake_db


@pytest.fixture
def client_v1():
    """v1 router — backward-compat 회귀 검증."""
    from routes.pi import router
    import deps

    app = FastAPI()
    app.include_router(router)

    fake_db = _FakeDB()
    app.dependency_overrides[deps.db_session] = lambda: fake_db
    app.dependency_overrides[deps.get_current_user] = _FakeUser.dep

    with TestClient(app) as c:
        yield c, fake_db


# ─────────────────────────────────────────────
#  GET /api/v2/pi
# ─────────────────────────────────────────────

def test_v2_get_locked_no_row(client_v2):
    c, _ = client_v2
    r = c.get("/api/v2/pi")
    assert r.status_code == 200
    body = r.json()
    assert body["unlocked"] is False
    assert body["cost"] == 50
    assert body["report_data"] is None


def test_v2_get_unlocked_with_row(client_v2):
    c, fake_db = client_v2
    now = datetime(2026, 4, 21, 12, 0, 0)
    fake_db.queue_result(
        "FROM pi_reports WHERE user_id",
        _make_row(unlocked_at=now, report_data={"status": "generating", "version": "v2"}),
    )
    r = c.get("/api/v2/pi")
    assert r.status_code == 200
    body = r.json()
    assert body["unlocked"] is True
    assert body["unlocked_at"] == now.isoformat()
    assert body["report_data"]["version"] == "v2"


# ─────────────────────────────────────────────
#  POST /api/v2/pi/unlock — happy + edge
# ─────────────────────────────────────────────

def test_v2_unlock_happy_path(client_v2, monkeypatch):
    c, fake_db = client_v2

    monkeypatch.setattr(
        "services.user_profiles.get_profile",
        lambda db, uid: _fake_profile(),
    )
    # pi_reports 는 locked 상태
    # tokens 차감 + get_balance stub
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 100,
    )
    monkeypatch.setattr(
        "services.tokens.credit_tokens",
        lambda db, **kw: 50,
    )

    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unlocked"] is True
    assert body["token_balance"] == 50
    assert body["report_data"]["version"] == "v2"
    assert body["report_data"]["status"] == "generating"
    assert body["report_data"]["profile_seed"]["gender"] == "female"

    # structured_fields 화이트리스트 검증
    seed_structured = body["report_data"]["profile_seed"]["structured_fields"]
    assert seed_structured["reference_style"] == "한소희 초반"
    assert "extra_legacy" not in seed_structured  # 화이트리스트 필터

    # ig_feed_cache 에서 profile_basics 제거 검증
    ig_seed = body["report_data"]["profile_seed"]["ig_feed_cache"]
    assert "profile_basics" not in ig_seed
    assert ig_seed["current_style_mood"][0]["tag"] == "쿨뮤트"

    # UPSERT + commit 호출 확인
    upsert_calls = [e for e in fake_db.executes if "INSERT INTO pi_reports" in e[0]]
    assert len(upsert_calls) == 1
    assert fake_db.committed == 1


def test_v2_unlock_no_profile_409(client_v2, monkeypatch):
    c, _ = client_v2
    monkeypatch.setattr(
        "services.user_profiles.get_profile",
        lambda db, uid: None,
    )
    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 409
    assert "온보딩" in r.json()["detail"]


def test_v2_unlock_already_unlocked_idempotent(client_v2, monkeypatch):
    c, fake_db = client_v2
    monkeypatch.setattr(
        "services.user_profiles.get_profile",
        lambda db, uid: _fake_profile(),
    )
    # pi_reports 기존 해제 row
    now = datetime(2026, 4, 20, 9, 0, 0)
    fake_db.queue_result(
        "FROM pi_reports WHERE user_id",
        _make_row(unlocked_at=now, report_data={"version": "v2", "status": "ready"}),
    )
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 80,
    )
    # credit_tokens 가 호출되면 실패해야 함 (idempotent 반환 전제)
    called = {"n": 0}

    def _credit(*a, **k):
        called["n"] += 1
        return 30

    monkeypatch.setattr("services.tokens.credit_tokens", _credit)

    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 200
    body = r.json()
    assert body["unlocked"] is True
    assert body["unlocked_at"] == now.isoformat()
    assert body["report_data"]["status"] == "ready"
    assert body["token_balance"] == 80
    # credit 호출 없음 (idempotent)
    assert called["n"] == 0


def test_v2_unlock_insufficient_tokens_402(client_v2, monkeypatch):
    c, _ = client_v2
    monkeypatch.setattr(
        "services.user_profiles.get_profile",
        lambda db, uid: _fake_profile(),
    )
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 10,  # 50 미만
    )
    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 402
    assert "토큰이 부족" in r.json()["detail"]


# ─────────────────────────────────────────────
#  v1 backward-compat
# ─────────────────────────────────────────────

def test_v1_unlock_uses_service_build_v1(client_v1, monkeypatch):
    """v1 엔드포인트가 services.pi.build_v1_report_data() 를 경유하는지 검증."""
    c, fake_db = client_v1

    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 100,
    )
    monkeypatch.setattr(
        "services.tokens.credit_tokens",
        lambda db, **kw: 50,
    )

    called = {"n": 0}

    def _build():
        called["n"] += 1
        return {
            "status": "generating",
            "face_analysis": None,
            "skin_tone": None,
            "gap_analysis": None,
            "hair_recommendations": None,
            "makeup_guide": None,
        }

    monkeypatch.setattr("services.pi.build_v1_report_data", _build)

    r = c.post("/api/v1/pi/unlock")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unlocked"] is True
    assert body["report_data"]["status"] == "generating"
    # v1 엔드포인트는 version 키 없어야 함 (v2 전용)
    assert "version" not in body["report_data"]
    assert called["n"] == 1


# ─────────────────────────────────────────────
#  services.pi 단위 테스트 (순수 함수)
# ─────────────────────────────────────────────

def test_build_v2_report_data_filters_unknown_keys():
    from services import pi as pi_service

    profile = _fake_profile()
    data = pi_service.build_v2_report_data(profile)
    seed = data["profile_seed"]["structured_fields"]
    assert "extra_legacy" not in seed
    assert set(seed.keys()).issubset({
        "desired_image", "reference_style", "current_concerns",
        "self_perception", "lifestyle_context", "height", "weight",
        "shoulder_width",
    })


def test_build_v2_report_data_empty_profile_drops_nones():
    from services import pi as pi_service

    profile = {
        "gender": "male",
        "structured_fields": {
            "desired_image": "",       # 빈 값 — 제외
            "reference_style": None,   # None — 제외
            "height": "170_175",       # 유효
        },
        "ig_feed_cache": None,
    }
    data = pi_service.build_v2_report_data(profile)
    seed_structured = data["profile_seed"]["structured_fields"]
    assert seed_structured == {"height": "170_175"}
    assert data["profile_seed"]["ig_feed_cache"] is None
    assert data["version"] == "v2"
    assert data["status"] == "generating"


def test_build_v1_report_data_stable_shape():
    from services import pi as pi_service

    data = pi_service.build_v1_report_data()
    expected_keys = {
        "status", "face_analysis", "skin_tone", "gap_analysis",
        "hair_recommendations", "makeup_guide",
    }
    assert set(data.keys()) == expected_keys
    assert data["status"] == "generating"
    # v2-only 키 유출 없음
    assert "version" not in data
    assert "profile_seed" not in data
