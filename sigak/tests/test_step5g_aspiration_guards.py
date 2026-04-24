"""STEP 5g 검증 — Aspiration 본인 핸들 차단 + Sia 미완 차단.

TestClient 로 라우트 전체 호출 → HTTP 상태/payload 확인.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routes import aspiration as aspiration_route
from services.coordinate_system import VisualCoordinate


# ─────────────────────────────────────────────
#  Test app + 공통 override
# ─────────────────────────────────────────────

def _make_app(current_user_id="u_test"):
    from deps import db_session, get_current_user
    app = FastAPI()
    app.include_router(aspiration_route.router)

    def _stub_db():
        mock = MagicMock()
        # SELECT blocklist → no row
        first_mock = MagicMock()
        first_mock.first.return_value = None
        mock.execute.return_value = first_mock
        return mock

    def _stub_user():
        return {"id": current_user_id}

    app.dependency_overrides[db_session] = _stub_db
    app.dependency_overrides[get_current_user] = _stub_user
    return app


def _make_vault(ig_handle=None, current_position=None):
    """load_vault 스텁용 duck-type 객체 (Pydantic 우회)."""
    class _BasicInfoStub:
        def __init__(self, handle):
            self.ig_handle = handle
            self.gender = "female"
            self.user_id = "u_test"

    class _TasteStub:
        def __init__(self, pos):
            self.current_position = pos

    class _VaultStub:
        def __init__(self, handle, pos):
            self.basic_info = _BasicInfoStub(handle)
            self.ig_feed_cache = None
            self.structured_fields = {}
            self._pos = pos
        def get_user_taste_profile(self):
            return _TasteStub(self._pos)

    return _VaultStub(ig_handle, current_position)


# ─────────────────────────────────────────────
#  본인 핸들 차단
# ─────────────────────────────────────────────

def test_self_handle_returns_400_with_error_code(monkeypatch):
    app = _make_app()
    vault = _make_vault(
        ig_handle="myself",
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.5),
    )
    monkeypatch.setattr(aspiration_route, "load_vault", lambda db, uid: vault)
    monkeypatch.setattr(aspiration_route, "is_blocked",
                        lambda db, *, target_type, target_identifier: False)

    client = TestClient(app)
    resp = client.post("/api/v2/aspiration/ig", json={"target_handle": "@myself"})
    assert resp.status_code == 400
    body = resp.json()
    detail = body.get("detail")
    assert isinstance(detail, dict)
    assert detail["error_code"] == "self_handle_rejected"
    assert "본인 IG" in detail["message"]


def test_self_handle_case_insensitive(monkeypatch):
    app = _make_app()
    vault = _make_vault(
        ig_handle="MYSELF",  # 대문자로 저장된 경우
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.5),
    )
    monkeypatch.setattr(aspiration_route, "load_vault", lambda db, uid: vault)
    monkeypatch.setattr(aspiration_route, "is_blocked",
                        lambda db, *, target_type, target_identifier: False)

    client = TestClient(app)
    resp = client.post("/api/v2/aspiration/ig", json={"target_handle": "@myself"})
    assert resp.status_code == 400


def test_different_handle_passes_guard(monkeypatch):
    """다른 핸들은 통과 (이후 balance 체크 등에서 다른 에러 발생 가능)."""
    app = _make_app()
    vault = _make_vault(
        ig_handle="myself",
        current_position=VisualCoordinate(shape=0.5, volume=0.5, age=0.5),
    )
    monkeypatch.setattr(aspiration_route, "load_vault", lambda db, uid: vault)
    monkeypatch.setattr(aspiration_route, "is_blocked",
                        lambda db, *, target_type, target_identifier: False)
    # 토큰 체크는 별도 — balance=0 으로 402 기대
    from services import tokens
    monkeypatch.setattr(tokens, "get_balance", lambda db, uid: 0)

    client = TestClient(app)
    resp = client.post("/api/v2/aspiration/ig", json={"target_handle": "@someone_else"})
    # self_handle_rejected 가 아닌 토큰 부족 (402) 으로 진행
    assert resp.status_code == 402


# ─────────────────────────────────────────────
#  Sia 미완 차단
# ─────────────────────────────────────────────

def test_sia_required_returns_409_with_error_code(monkeypatch):
    app = _make_app()
    vault = _make_vault(ig_handle="someone", current_position=None)  # Sia 미완
    monkeypatch.setattr(aspiration_route, "load_vault", lambda db, uid: vault)
    monkeypatch.setattr(aspiration_route, "is_blocked",
                        lambda db, *, target_type, target_identifier: False)

    client = TestClient(app)
    resp = client.post("/api/v2/aspiration/ig", json={"target_handle": "@target"})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error_code"] == "sia_required"
    assert detail["cta"]["href"] == "/sia"


def test_sia_required_for_pinterest_too(monkeypatch):
    app = _make_app()
    vault = _make_vault(ig_handle=None, current_position=None)
    monkeypatch.setattr(aspiration_route, "load_vault", lambda db, uid: vault)

    client = TestClient(app)
    resp = client.post(
        "/api/v2/aspiration/pinterest",
        json={"board_url": "https://www.pinterest.com/u/b/"},
    )
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error_code"] == "sia_required"
