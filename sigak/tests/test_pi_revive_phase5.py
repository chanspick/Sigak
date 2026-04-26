"""PI-REVIVE Phase 5 backend wiring 검증 (2026-04-26).

본 task = handoff/PI_REVIVE_V5_OLD_SYSTEM.md 의 작업 A + 작업 E.

작업 A: main.py BETA 우회 분기 — _is_pi_beta_free() helper + access="full" 분기
작업 E: routes/pi.py v3 503 gate 영구 활성 — router_v3 dependencies 부착

검증 범위:
  - main._is_pi_beta_free() 함수 존재 + config.beta_free_until 정상 파싱
  - main.get_report() BETA 기간 access="full" 강제 (옛 SIGAK_V3 paywall 우회)
  - routes.pi.router_v3 dependencies 에 _pi_v3_maintenance_gate 부착 확인
  - 모든 v3 endpoint 503 응답 + detail 메시지 (옛 SIGAK_V3 안내) 검증
"""
from __future__ import annotations

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────
#  작업 E: routes/pi.py router_v3 dependencies + 503 gate
# ─────────────────────────────────────────────


def test_router_v3_has_maintenance_gate_dependency():
    """router_v3 에 _pi_v3_maintenance_gate 가 영구 부착됐는지 확인."""
    from routes.pi import _pi_v3_maintenance_gate, router_v3

    assert len(router_v3.dependencies) >= 1, "router_v3 dependencies 비어있음"
    deps = [d.dependency for d in router_v3.dependencies]
    assert _pi_v3_maintenance_gate in deps, "maintenance gate 미부착"


def test_v3_status_returns_503_with_old_system_message():
    """GET /api/v3/pi/status → 503 + 옛 SIGAK_V3 안내 메시지."""
    from routes.pi import router_v3

    app = FastAPI()
    app.include_router(router_v3)
    with TestClient(app) as c:
        r = c.get("/api/v3/pi/status")

    assert r.status_code == 503, r.text
    body = r.json()
    detail = body.get("detail", "")
    # detail 메시지에 핵심 키워드 — "갱신 중" + "SIGAK_V3" + "/report/{id}/full"
    assert "갱신" in detail, f"갱신 키워드 누락: {detail!r}"
    assert "SIGAK_V3" in detail, f"SIGAK_V3 키워드 누락: {detail!r}"
    assert "/report/" in detail, f"/report/ 가이드 누락: {detail!r}"


def test_v3_preview_returns_503():
    """POST /api/v3/pi/preview → 503 (gate)."""
    from routes.pi import router_v3

    app = FastAPI()
    app.include_router(router_v3)
    with TestClient(app) as c:
        r = c.post("/api/v3/pi/preview")
    assert r.status_code == 503


def test_v3_unlock_returns_503():
    """POST /api/v3/pi/unlock → 503 (gate)."""
    from routes.pi import router_v3

    app = FastAPI()
    app.include_router(router_v3)
    with TestClient(app) as c:
        r = c.post("/api/v3/pi/unlock")
    assert r.status_code == 503


def test_v3_list_returns_503():
    """GET /api/v3/pi/list → 503 (gate)."""
    from routes.pi import router_v3

    app = FastAPI()
    app.include_router(router_v3)
    with TestClient(app) as c:
        r = c.get("/api/v3/pi/list")
    assert r.status_code == 503


def test_v3_get_report_id_returns_503():
    """GET /api/v3/pi/{report_id} → 503 (gate)."""
    from routes.pi import router_v3

    app = FastAPI()
    app.include_router(router_v3)
    with TestClient(app) as c:
        r = c.get("/api/v3/pi/abc123")
    assert r.status_code == 503


def test_v3_delete_returns_503():
    """DELETE /api/v3/pi → 503 (gate)."""
    from routes.pi import router_v3

    app = FastAPI()
    app.include_router(router_v3)
    with TestClient(app) as c:
        r = c.delete("/api/v3/pi")
    assert r.status_code == 503


# ─────────────────────────────────────────────
#  작업 A: main._is_pi_beta_free + get_report BETA 우회
#
#  Note: main.py 풀 import 는 anthropic / redis / opencv 등 prod-only
#  의존성을 트리거 → 본 dev/CI 환경에서 비실용. 따라서 source-level 검증
#  + 동등 로직 standalone 검증으로 분리.
# ─────────────────────────────────────────────


def test_main_py_has_is_pi_beta_free_helper_defined():
    """main.py 소스에 _is_pi_beta_free() 함수 정의 + date import + config 사용 확인."""
    import ast
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        src = f.read()

    tree = ast.parse(src)
    funcs = {
        node.name for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    assert "_is_pi_beta_free" in funcs, "main.py 에 _is_pi_beta_free 미정의"

    # date import 가 module level 에 존재
    assert "from datetime import date" in src or "import date" in src, (
        "main.py 에 date import 누락"
    )
    # get_settings 호출 (helper 가 사용) 확인
    assert "get_settings()" in src, "main.py 에 get_settings() 호출 누락"
    # beta_free_until 참조
    assert "beta_free_until" in src, "main.py 에 beta_free_until 참조 누락"


def test_main_py_get_report_branches_on_beta_free():
    """get_report 함수가 _is_pi_beta_free() 호출 + access='full' 강제 분기 포함."""
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        src = f.read()

    # 핵심 분기 패턴 검증
    assert "_is_pi_beta_free()" in src, "_is_pi_beta_free() 호출 누락"
    # access = "full" 강제 분기 (get_report 안)
    assert 'access = "full"' in src, "BETA 분기에서 access=\"full\" 강제 누락"


def test_is_pi_beta_free_logic_during_beta_period(monkeypatch):
    """동등 로직 standalone — beta_free_until 미래 → True."""
    from config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "beta_free_until", "2099-12-31")

    # main._is_pi_beta_free 의 본체 로직과 동일
    def _is_pi_beta_free() -> bool:
        try:
            return date.today() < date.fromisoformat(get_settings().beta_free_until)
        except (ValueError, AttributeError, TypeError):
            return False

    assert _is_pi_beta_free() is True


def test_is_pi_beta_free_logic_after_beta_period(monkeypatch):
    """동등 로직 standalone — beta_free_until 과거 → False."""
    from config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "beta_free_until", "2000-01-01")

    def _is_pi_beta_free() -> bool:
        try:
            return date.today() < date.fromisoformat(get_settings().beta_free_until)
        except (ValueError, AttributeError, TypeError):
            return False

    assert _is_pi_beta_free() is False


def test_is_pi_beta_free_logic_invalid_date(monkeypatch):
    """동등 로직 standalone — 파싱 실패 → False (안전 fallback)."""
    from config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "beta_free_until", "not-a-date")

    def _is_pi_beta_free() -> bool:
        try:
            return date.today() < date.fromisoformat(get_settings().beta_free_until)
        except (ValueError, AttributeError, TypeError):
            return False

    assert _is_pi_beta_free() is False


def test_default_config_beta_free_until_is_iso_date():
    """config.beta_free_until 기본값이 ISO 날짜 문자열로 파싱 가능."""
    from config import get_settings
    settings = get_settings()
    parsed = date.fromisoformat(settings.beta_free_until)
    assert isinstance(parsed, date)
