"""Phase M — 이달의 시각 스켈레톤 테스트.

KST 15일 경계 / scheduler stub / DB 조회 defensive / 상태 매핑.
실 엔진 v1.1+ 이관 — MVP 는 placeholder.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import monthly_engine as me
from services.monthly_engine import (
    KST,
    MVP_PLACEHOLDER_MESSAGE,
    days_between,
    get_current_month_report,
    next_delivery_kst_fifteenth,
    run_monthly_scheduler_tick,
    year_month_for_delivery,
)


# ─────────────────────────────────────────────
#  next_delivery_kst_fifteenth — 경계 테스트
# ─────────────────────────────────────────────

def _kst(y, m, d, h=0, mnt=0) -> datetime:
    return datetime(y, m, d, h, mnt, tzinfo=KST)


def test_before_fifteenth_returns_this_month():
    """14일 23:59 KST → 이번 달 15일."""
    now = _kst(2026, 4, 14, 23, 59).astimezone(timezone.utc)
    nd = next_delivery_kst_fifteenth(now)
    nd_kst = nd.astimezone(KST)
    assert nd_kst.year == 2026
    assert nd_kst.month == 4
    assert nd_kst.day == 15
    assert nd_kst.hour == 0 and nd_kst.minute == 0


def test_exactly_fifteenth_midnight_returns_next_month():
    """15일 00:00 KST → 다음 달 15일 (이미 도달한 시점 skip)."""
    now = _kst(2026, 4, 15, 0, 0).astimezone(timezone.utc)
    nd = next_delivery_kst_fifteenth(now)
    nd_kst = nd.astimezone(KST)
    assert nd_kst.month == 5
    assert nd_kst.day == 15


def test_after_fifteenth_returns_next_month():
    now = _kst(2026, 4, 16).astimezone(timezone.utc)
    nd = next_delivery_kst_fifteenth(now).astimezone(KST)
    assert nd.month == 5
    assert nd.day == 15


def test_december_crosses_year():
    """12월 20일 → 다음 해 1월 15일."""
    now = _kst(2026, 12, 20).astimezone(timezone.utc)
    nd = next_delivery_kst_fifteenth(now).astimezone(KST)
    assert nd.year == 2027
    assert nd.month == 1
    assert nd.day == 15


def test_year_month_for_delivery():
    d = _kst(2026, 5, 15).astimezone(timezone.utc)
    assert year_month_for_delivery(d) == "2026-05"
    d2 = _kst(2027, 1, 15).astimezone(timezone.utc)
    assert year_month_for_delivery(d2) == "2027-01"


def test_days_between_non_negative():
    now = datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc)
    target = datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc)
    assert days_between(now, target) == 3
    # 음수는 0 으로 clamp
    assert days_between(target, now) == 0


# ─────────────────────────────────────────────
#  DB defensive — 테이블 없으면 조용히 None/0
# ─────────────────────────────────────────────

class _RaisingDB:
    """execute 가 무조건 예외 → 테이블 미생성 (dev 환경) 시나리오."""
    def execute(self, *a, **kw):
        raise RuntimeError("relation monthly_reports does not exist")

    def commit(self): pass


def test_get_current_month_report_table_missing_returns_none():
    db = _RaisingDB()
    assert get_current_month_report(db, user_id="u1", year_month="2026-04") is None


def test_count_past_reports_table_missing_returns_zero():
    db = _RaisingDB()
    assert me.count_past_reports(db, user_id="u1") == 0


def test_get_current_month_report_none_db():
    assert get_current_month_report(None, user_id="u1") is None


# ─────────────────────────────────────────────
#  DB 조회 happy path — fake DB
# ─────────────────────────────────────────────

class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _FakeResult:
    def __init__(self, first=None, scalar=None, rows=None):
        self._first = first
        self._scalar = scalar
        self._rows = rows or []

    def first(self): return self._first
    def scalar(self): return self._scalar
    def fetchall(self): return self._rows


class _FakeDB:
    def __init__(self, first=None, scalar=None, rows=None):
        self._first = first
        self._scalar = scalar
        self._rows = rows or []
        self.commits = 0
        self.executed: list[str] = []

    def execute(self, stmt, params=None):
        self.executed.append(str(stmt))
        # 간단한 SQL 분기 — INSERT / SELECT COUNT / SELECT *
        sql = str(stmt).lower()
        if "count(" in sql:
            return _FakeResult(scalar=self._scalar)
        if sql.strip().startswith("insert"):
            return _FakeResult()
        if "select user_id from user_profiles" in sql:
            return _FakeResult(rows=self._rows)
        return _FakeResult(first=self._first)

    def commit(self):
        self.commits += 1


def test_get_current_month_report_returns_domain_obj():
    row = _Row(
        report_id="mr_abc",
        user_id="u1",
        year_month="2026-04",
        status="placeholder",
        scheduled_for=datetime(2026, 4, 15, tzinfo=timezone.utc),
        generated_at=None,
        result_data=None,
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    db = _FakeDB(first=row)
    rep = get_current_month_report(db, user_id="u1", year_month="2026-04")
    assert rep is not None
    assert rep.report_id == "mr_abc"
    assert rep.status == "placeholder"


def test_count_past_reports_returns_scalar():
    db = _FakeDB(scalar=5)
    assert me.count_past_reports(db, user_id="u1") == 5


# ─────────────────────────────────────────────
#  scheduler tick — stub 동작
# ─────────────────────────────────────────────

def test_scheduler_tick_none_db():
    now = datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc)
    result = run_monthly_scheduler_tick(None, now_utc=now)
    assert result.candidates_scanned == 0
    assert result.scheduled_created == 0


def test_scheduler_tick_scans_profiles():
    """user_profiles 에서 유저 3명 스캔 → 3개 INSERT 시도 (rowcount 추적 없이 성공 가정)."""
    # 14일 KST → next delivery 는 이번 달 15일. year_month = "2026-04"
    now = _kst(2026, 4, 14, 12, 0).astimezone(timezone.utc)
    rows = [_Row(user_id=f"u{i}") for i in range(3)]
    db = _FakeDB(rows=rows)
    result = run_monthly_scheduler_tick(db, now_utc=now)
    assert result.candidates_scanned == 3
    assert result.scheduled_created == 3
    assert result.year_month == "2026-04"
    assert db.commits == 1


def test_scheduler_tick_handles_profile_scan_failure():
    """user_profiles 테이블 못 읽으면 errors 없이 0 scanned 로 종료."""
    now = datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc)
    db = _RaisingDB()
    result = run_monthly_scheduler_tick(db, now_utc=now)
    assert result.candidates_scanned == 0
    assert result.scheduled_created == 0


# ─────────────────────────────────────────────
#  placeholder_message 상수 노출
# ─────────────────────────────────────────────

def test_placeholder_message_non_empty():
    assert isinstance(MVP_PLACEHOLDER_MESSAGE, str)
    assert len(MVP_PLACEHOLDER_MESSAGE) > 10
    assert "15일" in MVP_PLACEHOLDER_MESSAGE
