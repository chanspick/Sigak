"""Onboarding Step 0 essentials route tests (SPEC-ONBOARDING-V2 REQ-ONBD-001/002).

`/api/v1/onboarding/essentials` FastAPI TestClient 통합 테스트.
DB 는 mock (execute 호출 기록). 실 DB 검증은 staging 에서.

커버리지:
  - 정상 케이스 (female + birth_date + ig_handle)
  - ig_handle 정규화 (@ 제거 / 빈 문자열 → None / 공백 trim)
  - 만 14세 미만 거부
  - 미래 날짜 거부
  - ig_handle 포맷 위반 (한글/공백 포함) 거부
  - 잘못된 gender (Pydantic Literal)
  - DB 2회 execute (users UPDATE + user_profiles upsert)
  - /auth/me 에 essentials_completed=True 반영
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from typing import Optional
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

def _user() -> dict:
    return {
        "id": "u1",
        "kakao_id": "k1",
        "email": "",
        "name": "정세현",
        "gender": "female",
        "tier": "standard",
    }


class _FakeDB:
    """최소 DB mock — execute 호출 기록 + first() row 지정 가능."""

    def __init__(self):
        self.executes: list[tuple[str, dict]] = []
        self.committed = 0
        self._next_first = None  # /auth/me 에서 쓸 가상 row

    def execute(self, stmt, params: Optional[dict] = None):
        self.executes.append((str(stmt), params or {}))
        result = MagicMock()
        result.first.return_value = self._next_first
        result.rowcount = 0
        return result

    def commit(self):
        self.committed += 1

    def rollback(self):
        pass

    def set_next_first(self, row):
        """다음 execute.first() 가 반환할 mock row 지정."""
        self._next_first = row


@pytest.fixture
def onboarding_app():
    """onboarding router + auth router 로 구성한 FastAPI app."""
    from routes import onboarding as onb_route
    from routes import auth as auth_route
    import deps

    app = FastAPI()
    app.include_router(onb_route.router)
    app.include_router(auth_route.router)

    fake_db = _FakeDB()
    app.dependency_overrides[deps.db_session] = lambda: fake_db
    user_holder = {"current": _user()}
    app.dependency_overrides[deps.get_current_user] = lambda: user_holder["current"]

    return app, fake_db, user_holder


@pytest.fixture
def client(onboarding_app):
    app, fake_db, user_holder = onboarding_app
    with TestClient(app) as c:
        yield c, fake_db, user_holder


# ─────────────────────────────────────────────
#  Happy path
# ─────────────────────────────────────────────

def test_essentials_happy_path(client):
    c, fake_db, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={
            "gender": "female",
            "birth_date": "1999-03-15",
            "ig_handle": "yuni_kim",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["essentials_completed"] is True
    assert body["gender"] == "female"
    assert body["birth_date"] == "1999-03-15"
    assert body["ig_handle"] == "yuni_kim"

    # DB: users UPDATE + user_profiles upsert 2회
    sqls = [s.upper() for s, _ in fake_db.executes]
    assert any("UPDATE USERS SET" in s for s in sqls)
    assert any("INSERT INTO USER_PROFILES" in s and "ON CONFLICT" in s for s in sqls)
    assert fake_db.committed == 1


def test_essentials_without_ig_handle_stores_null(client):
    c, fake_db, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={"gender": "male", "birth_date": "1990-01-01"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["ig_handle"] is None
    # DB 바인딩 확인
    for stmt, params in fake_db.executes:
        if "ig_handle" in stmt.lower():
            assert params.get("ig_handle") is None


# ─────────────────────────────────────────────
#  ig_handle normalization
# ─────────────────────────────────────────────

def test_essentials_strips_at_prefix(client):
    c, fake_db, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={
            "gender": "female",
            "birth_date": "1999-03-15",
            "ig_handle": "@yuni_kim",
        },
    )
    assert r.status_code == 200
    assert r.json()["ig_handle"] == "yuni_kim"


def test_essentials_empty_ig_handle_becomes_null(client):
    c, _, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={
            "gender": "female",
            "birth_date": "1999-03-15",
            "ig_handle": "   ",
        },
    )
    assert r.status_code == 200
    assert r.json()["ig_handle"] is None


def test_essentials_rejects_hangul_ig_handle(client):
    c, _, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={
            "gender": "female",
            "birth_date": "1999-03-15",
            "ig_handle": "한글계정",
        },
    )
    assert r.status_code == 400
    assert "ig_handle" in r.json()["detail"] or "영문" in r.json()["detail"]


# ─────────────────────────────────────────────
#  Age validation
# ─────────────────────────────────────────────

def test_essentials_rejects_under_14(client):
    c, _, _ = client
    today = date.today()
    # 정확히 13세 (14세 생일 하루 전)
    thirteen_years_old = today.replace(year=today.year - 13) + timedelta(days=30)
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={
            "gender": "female",
            "birth_date": thirteen_years_old.isoformat(),
        },
    )
    assert r.status_code == 400
    assert "14" in r.json()["detail"]


def test_essentials_rejects_future_birth_date(client):
    c, _, _ = client
    future = (date.today() + timedelta(days=30)).isoformat()
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={"gender": "female", "birth_date": future},
    )
    assert r.status_code == 400
    assert "미래" in r.json()["detail"]


def test_essentials_accepts_exactly_14_years(client):
    c, _, _ = client
    today = date.today()
    # 정확히 14세 (14세 생일 당일)
    exactly_14 = today.replace(year=today.year - 14)
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={
            "gender": "female",
            "birth_date": exactly_14.isoformat(),
        },
    )
    assert r.status_code == 200


# ─────────────────────────────────────────────
#  Schema validation (Pydantic)
# ─────────────────────────────────────────────

def test_essentials_rejects_invalid_gender(client):
    c, _, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={"gender": "other", "birth_date": "1999-03-15"},
    )
    assert r.status_code == 422  # Pydantic Literal


def test_essentials_rejects_malformed_date(client):
    c, _, _ = client
    r = c.post(
        "/api/v1/onboarding/essentials",
        json={"gender": "female", "birth_date": "not-a-date"},
    )
    assert r.status_code == 422


# ─────────────────────────────────────────────
#  /auth/me essentials_completed flag
# ─────────────────────────────────────────────

def test_me_reports_essentials_completed_when_birth_date_set(client):
    c, fake_db, _ = client
    row = MagicMock()
    row.consent_completed = True
    row.onboarding_completed = False
    row.birth_date = date(1999, 3, 15)
    fake_db.set_next_first(row)

    r = c.get("/api/v1/auth/me")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["essentials_completed"] is True
    assert body["consent_completed"] is True
    assert body["onboarding_completed"] is False


def test_me_reports_essentials_incomplete_when_birth_date_null(client):
    c, fake_db, _ = client
    row = MagicMock()
    row.consent_completed = True
    row.onboarding_completed = False
    row.birth_date = None
    fake_db.set_next_first(row)

    r = c.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["essentials_completed"] is False
