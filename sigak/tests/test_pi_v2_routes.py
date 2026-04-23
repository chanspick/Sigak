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

def _stub_pi_report(report_id: str = "pi_abc", version: int = 1):
    """Phase I generate_pi_report 가 반환하는 PIReport stub."""
    from datetime import datetime, timezone
    from schemas.pi_report import PIReport, PIReportSources
    return PIReport(
        report_id=report_id,
        user_id="u1",
        version=version,
        is_current=True,
        generated_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        public_photos=[],
        locked_photos=[],
        user_taste_profile_snapshot={},
        user_summary="정세현님은 정돈된 인상을 추구하시는 분입니다.",
        needs_statement="그에 맞는 방향성이 필요합니다.",
        user_original_phrases=[],
        sia_overall_message="overall stub",
        boundary_message="boundary stub",
        matched_trend_ids=[],
        matched_methodology_ids=[],
        matched_reference_ids=[],
        data_sources_used=PIReportSources(),
    )


def _stub_vault():
    """Phase I: load_vault 가 반환하는 Vault stub."""
    from services.user_data_vault import UserBasicInfo, UserDataVault
    return UserDataVault(
        basic_info=UserBasicInfo(
            user_id="u1", gender="female", ig_handle="test_user", name="정세현",
        ),
        ig_feed_cache=None,
        structured_fields={"desired_image": "편안한 인상"},
    )


def test_v2_unlock_first_time_is_free(client_v2, monkeypatch):
    """Phase I 첫 1회 무료 정책. 기존 '항상 50 차감' 로직 폐기."""
    c, fake_db = client_v2

    monkeypatch.setattr(
        "services.user_data_vault.load_vault",
        lambda db, uid: _stub_vault(),
    )
    # 기존 is_current 없음 → _has_real_current_report = False
    # credit_tokens 호출되면 안 됨 (무료)
    called = {"credit": 0}
    monkeypatch.setattr(
        "services.tokens.credit_tokens",
        lambda *a, **k: called.__setitem__("credit", called["credit"] + 1) or 100,
    )
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 100,
    )
    # generate_pi_report stub
    monkeypatch.setattr(
        "services.pi_engine.generate_pi_report",
        lambda db, **kw: _stub_pi_report(),
    )

    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unlocked"] is True
    assert body["token_balance"] == 100   # 차감 없음
    assert called["credit"] == 0
    assert body["report_data"]["report_id"] == "pi_abc"
    assert body["report_data"]["version"] == 1


def test_v2_unlock_no_vault_409(client_v2, monkeypatch):
    c, _ = client_v2
    monkeypatch.setattr(
        "services.user_data_vault.load_vault",
        lambda db, uid: None,
    )
    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 409
    assert "온보딩" in r.json()["detail"]


def test_v2_unlock_regenerate_charges_50(client_v2, monkeypatch):
    """기존 is_current 있으면 재생성 = 50 토큰 차감 + force_new_version."""
    c, fake_db = client_v2
    monkeypatch.setattr(
        "services.user_data_vault.load_vault",
        lambda db, uid: _stub_vault(),
    )
    # 기존 is_current 리포트 존재 → _has_real_current_report = True
    fake_db.queue_result(
        "FROM pi_reports "
        "WHERE user_id = :uid AND is_current = TRUE LIMIT 1",
        _make_row(report_data={"report_id": "pi_old", "version": 1, "status": "ready"}),
    )
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 80,
    )
    credit_called = {"n": 0}

    def _credit(db, **k):
        credit_called["n"] += 1
        return 30    # 80 - 50

    monkeypatch.setattr("services.tokens.credit_tokens", _credit)

    # generate 가 force_new_version=True 로 호출됐는지 확인
    force_new_seen = {"v": None}

    def _gen(db, **kw):
        force_new_seen["v"] = kw.get("force_new_version")
        return _stub_pi_report(report_id="pi_new", version=2)

    monkeypatch.setattr("services.pi_engine.generate_pi_report", _gen)

    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["report_data"]["version"] == 2
    assert body["token_balance"] == 30
    assert credit_called["n"] == 1          # 1회 차감
    assert force_new_seen["v"] is True      # 재생성


def test_v2_unlock_regenerate_insufficient_tokens_402(client_v2, monkeypatch):
    """재생성인데 잔액 < 50 → 402."""
    c, fake_db = client_v2
    monkeypatch.setattr(
        "services.user_data_vault.load_vault",
        lambda db, uid: _stub_vault(),
    )
    fake_db.queue_result(
        "FROM pi_reports "
        "WHERE user_id = :uid AND is_current = TRUE LIMIT 1",
        _make_row(report_data={"report_id": "pi_old", "version": 1}),
    )
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 10,   # 50 미만
    )
    r = c.post("/api/v2/pi/unlock")
    assert r.status_code == 402


# (구 test_v2_unlock_insufficient_tokens_402 삭제 — Phase I 첫 1회 무료 정책에
#  맞춰 test_v2_unlock_regenerate_insufficient_tokens_402 로 대체됨)


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
