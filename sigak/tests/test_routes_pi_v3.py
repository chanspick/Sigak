"""PI v3 routes 통합 테스트 (Phase I PI-D, 본인 결정 2026-04-25).

PI-REVIVE Phase 5 (2026-04-26): v3 router 영구 503 gate 활성화.
옛 SIGAK_V3 system (main.py + pipeline/*) 부활. 본 파일의 모든 endpoint-level
기존 테스트는 obsolete — 신 v3 endpoints 모두 503 maintenance 응답.
모듈 전체를 skip 처리 + gate 동작 검증 테스트 1건은 별도 파일 유지 가능.

원본 Covers (참고용 — 더는 적용되지 않음):
  GET  /api/v3/pi/status              baseline 없음 / 있음 / current_report
  POST /api/v3/pi/preview             409 (vault 없음 / baseline 없음) / 정상
  POST /api/v3/pi/unlock              402 (토큰 부족) / 정상 / 환불 (engine 실패)
  GET  /api/v3/pi/list                빈 / 1개
  GET  /api/v3/pi/{report_id}         403 (다른 유저) / 404 / 정상
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

# PI-REVIVE Phase 5 영구 gate. v3 endpoints 503 only — 기존 endpoint 단위 검증
# 모두 obsolete. 새 검증 (gate 동작) 은 test_v3_maintenance_gate 1건으로 충분.
pytestmark = pytest.mark.skip(
    reason="PI v3 영구 503 gate (PI-REVIVE Phase 5, 2026-04-26). 옛 SIGAK_V3 부활.",
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────


class _FakeUser:
    @staticmethod
    def dep() -> dict:
        return {
            "id": "u1",
            "kakao_id": "k1",
            "email": "",
            "name": "정세현",
            "gender": "female",
        }


class _FakeDB:
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
        result.fetchall.return_value = []
        result.scalar.return_value = None
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


def _make_rows(rows: list[dict]):
    """fetchall 결과 stub."""
    result = MagicMock()
    objs = []
    for r in rows:
        m = MagicMock()
        for k, v in r.items():
            setattr(m, k, v)
        objs.append(m)
    result.fetchall.return_value = objs
    return result


@pytest.fixture
def client_v3(monkeypatch):
    """v3 router only — 테스트 목적."""
    from routes.pi import router_v3
    import deps

    app = FastAPI()
    app.include_router(router_v3)

    fake_db = _FakeDB()
    app.dependency_overrides[deps.db_session] = lambda: fake_db
    app.dependency_overrides[deps.get_current_user] = _FakeUser.dep

    with TestClient(app) as c:
        yield c, fake_db, monkeypatch


# ─────────────────────────────────────────────
#  GET /api/v3/pi/status
# ─────────────────────────────────────────────

def test_v3_status_no_baseline(client_v3, monkeypatch):
    """baseline 없음 → has_baseline=False, has_current_report=False."""
    c, fake_db, _ = client_v3

    # users.pi_baseline_* 컬럼 응답 — None
    fake_db.queue_result(
        "FROM users WHERE id",
        _make_row(
            pi_baseline_r2_key=None,
            pi_baseline_uploaded_at=None,
            pi_pending=False,
        ),
    )
    # current report 없음 (FROM pi_reports WHERE user_id 응답 없음 = MagicMock None)
    monkeypatch.setattr(
        "services.tokens.get_balance",
        lambda db, uid: 30,   # 가입 30 토큰
    )

    r = c.get("/api/v3/pi/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_baseline"] is False
    assert body["has_current_report"] is False
    assert body["unlock_cost_tokens"] == 50
    assert body["token_balance"] == 30
    assert body["needs_payment_tokens"] == 20   # 50 - 30


def test_v3_status_with_baseline(client_v3, monkeypatch):
    """baseline 있고 current_report 없음."""
    c, fake_db, _ = client_v3

    now = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)
    fake_db.queue_result(
        "FROM users WHERE id",
        _make_row(
            pi_baseline_r2_key="users/u1/pi_baseline/abc.jpg",
            pi_baseline_uploaded_at=now,
            pi_pending=True,
        ),
    )
    monkeypatch.setattr("services.tokens.get_balance", lambda db, uid: 50)

    r = c.get("/api/v3/pi/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["has_baseline"] is True
    assert body["pi_pending"] is True
    assert body["needs_payment_tokens"] == 0   # 50 충분


# ─────────────────────────────────────────────
#  POST /api/v3/pi/preview
# ─────────────────────────────────────────────

def test_v3_preview_no_baseline_returns_409(client_v3):
    """baseline 미업로드 시 409."""
    c, fake_db, _ = client_v3

    fake_db.queue_result(
        "FROM users WHERE id",
        _make_row(
            pi_baseline_r2_key=None,
            pi_baseline_uploaded_at=None,
            pi_pending=False,
        ),
    )

    r = c.post("/api/v3/pi/preview")
    assert r.status_code == 409
    assert "정면 사진" in r.json()["detail"]


def test_v3_preview_no_vault_returns_409(client_v3, monkeypatch):
    """baseline 있고 vault 없음 → 409 (온보딩 필요)."""
    c, fake_db, _ = client_v3

    fake_db.queue_result(
        "FROM users WHERE id",
        _make_row(
            pi_baseline_r2_key="users/u1/pi_baseline/abc.jpg",
            pi_baseline_uploaded_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
            pi_pending=False,
        ),
    )
    monkeypatch.setattr("services.user_data_vault.load_vault", lambda db, uid: None)

    r = c.post("/api/v3/pi/preview")
    assert r.status_code == 409
    assert "온보딩" in r.json()["detail"]


# ─────────────────────────────────────────────
#  POST /api/v3/pi/unlock — 토큰 부족 / 환불
# ─────────────────────────────────────────────

def test_v3_unlock_insufficient_tokens_returns_402(client_v3, monkeypatch):
    """토큰 보유 30 < 필요 50 → 402."""
    c, fake_db, _ = client_v3

    fake_db.queue_result(
        "FROM users WHERE id",
        _make_row(
            pi_baseline_r2_key="users/u1/pi_baseline/abc.jpg",
            pi_baseline_uploaded_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
            pi_pending=True,
        ),
    )

    # vault stub
    from services.user_data_vault import UserBasicInfo, UserDataVault
    fake_vault = UserDataVault(
        basic_info=UserBasicInfo(user_id="u1", gender="female"),
    )
    monkeypatch.setattr(
        "services.user_data_vault.load_vault",
        lambda db, uid: fake_vault,
    )
    monkeypatch.setattr("services.tokens.get_balance", lambda db, uid: 30)

    r = c.post("/api/v3/pi/unlock")
    assert r.status_code == 402
    assert "토큰" in r.json()["detail"]


def test_v3_unlock_engine_failure_refunds(client_v3, monkeypatch):
    """pi_engine 실패 시 환불 + 500."""
    c, fake_db, _ = client_v3

    fake_db.queue_result(
        "FROM users WHERE id",
        _make_row(
            pi_baseline_r2_key="users/u1/pi_baseline/abc.jpg",
            pi_baseline_uploaded_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
            pi_pending=True,
        ),
    )

    from services.user_data_vault import UserBasicInfo, UserDataVault
    fake_vault = UserDataVault(
        basic_info=UserBasicInfo(user_id="u1", gender="female"),
    )
    monkeypatch.setattr(
        "services.user_data_vault.load_vault",
        lambda db, uid: fake_vault,
    )
    monkeypatch.setattr("services.tokens.get_balance", lambda db, uid: 100)

    # 토큰 차감 mock — 50 차감 후 잔액 50 반환
    debit_calls: list[int] = []

    def _fake_credit(db, *, user_id, amount, kind, idempotency_key, **kwargs):
        debit_calls.append(amount)
        return 100 + amount   # 차감 (-50) → 50, 환불 (+50) → 50

    monkeypatch.setattr("services.tokens.credit_tokens", _fake_credit)

    # pi_engine 실패 stub
    from services.pi_engine import PIEngineError
    def _fail_engine(*args, **kwargs):
        raise PIEngineError("Sonnet 호출 실패 stub")
    monkeypatch.setattr("services.pi_engine.generate_pi_report", _fail_engine)

    # PI-A v1 시그니처도 fail
    import services.pi_engine as pi_eng_mod
    if hasattr(pi_eng_mod, "generate_pi_report_v1"):
        monkeypatch.setattr(
            "services.pi_engine.generate_pi_report_v1", _fail_engine,
        )

    r = c.post("/api/v3/pi/unlock")
    assert r.status_code == 500
    assert "PI 생성 실패" in r.json()["detail"]
    # 환불이 시도되었는지 — debit (-50) + refund (+50) 두 호출
    assert -50 in debit_calls, f"debit not called: {debit_calls}"
    assert +50 in debit_calls, f"refund not called: {debit_calls}"


# ─────────────────────────────────────────────
#  GET /api/v3/pi/list
# ─────────────────────────────────────────────

def test_v3_list_empty(client_v3):
    """pi_reports 없음 → versions []."""
    c, fake_db, _ = client_v3

    fake_db.queue_result(
        "FROM pi_reports WHERE user_id",
        _make_rows([]),
    )

    r = c.get("/api/v3/pi/list")
    assert r.status_code == 200
    body = r.json()
    assert body["versions"] == []
    assert body["current_report_id"] is None


# ─────────────────────────────────────────────
#  GET /api/v3/pi/{report_id} — 권한 검증
# ─────────────────────────────────────────────

def test_v3_get_report_other_user_returns_403(client_v3):
    """다른 유저 리포트 조회 시 403."""
    c, fake_db, _ = client_v3

    fake_db.queue_result(
        "FROM pi_reports WHERE report_id",
        _make_row(
            report_id="pi_abc",
            user_id="other_user",
            version=1,
            is_current=True,
            unlocked_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
            report_data={"report_id": "pi_abc", "version": 1},
            created_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        ),
    )

    r = c.get("/api/v3/pi/pi_abc")
    assert r.status_code == 403


def test_v3_get_report_not_found_returns_404(client_v3):
    """존재하지 않는 report_id → 404."""
    c, _, _ = client_v3
    r = c.get("/api/v3/pi/pi_nonexistent")
    assert r.status_code == 404
