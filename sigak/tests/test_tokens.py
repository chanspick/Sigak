"""token service tests.

credit_tokens 의 UPSERT 패턴 회귀 테스트 집중.

버그 히스토리:
  2026-04-25 — INSERT..ON CONFLICT DO UPDATE 단일 쿼리가 debit (amount < 0) 시
  CHECK constraint (balance >= 0) 를 INSERT VALUES 단계에서 먼저 검증해 raise.
  ON CONFLICT DO UPDATE 분기에 도달하지 못함. 2-단계 upsert (ensure row +
  apply delta via UPDATE) 로 fix.
"""
from __future__ import annotations

import os
import sys
from typing import Optional
from unittest.mock import MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import tokens as tokens_service


class _FakeDB:
    """SQL 호출 기록 + first/scalar 반환 스텁."""

    def __init__(self):
        self.executes: list[tuple[str, dict]] = []
        self._first_returns: list = []
        self._scalar_returns: list = []

    def execute(self, stmt, params: Optional[dict] = None):
        self.executes.append((str(stmt), params or {}))
        result = MagicMock()
        # lazy pop — 실 호출 시점에만 큐 소비
        result.first = lambda: (
            self._first_returns.pop(0) if self._first_returns else None
        )
        result.scalar = lambda: (
            self._scalar_returns.pop(0) if self._scalar_returns else 0
        )
        result.rowcount = 1
        return result

    def queue_first(self, value):
        self._first_returns.append(value)

    def queue_scalar(self, value):
        self._scalar_returns.append(value)


# ─────────────────────────────────────────────
#  Regression — 2-stage upsert pattern
# ─────────────────────────────────────────────

def test_credit_tokens_debit_uses_two_stage_upsert():
    """debit 시 INSERT (balance=0 DO NOTHING) + UPDATE (balance + delta) 패턴."""
    db = _FakeDB()
    # idempotency 조회 → None (first 호출)
    db.queue_first(None)
    # UPDATE RETURNING balance → 20 (기존 30 - 10)
    db.queue_scalar(20)

    balance_after = tokens_service.credit_tokens(
        db,
        user_id="u1",
        amount=-10,
        kind=tokens_service.KIND_CONSUME_VERDICT_V2,
        idempotency_key="verdict:u1:v1",
    )
    assert balance_after == 20

    sqls = [s for s, _ in db.executes]
    # 1) SELECT idempotency_key
    assert "SELECT balance_after FROM token_transactions" in sqls[0]
    # 2) INSERT balance=0 ON CONFLICT DO NOTHING (row 존재 보장)
    assert "INSERT INTO token_balances" in sqls[1]
    assert "ON CONFLICT (user_id) DO NOTHING" in sqls[1]
    # INSERT 의 VALUES 에 amount 가 직접 들어가면 debit 시 CHECK 위반 재발.
    # balance=0 고정이어야 함.
    assert ":amt" not in sqls[1], "INSERT 에 amount 바인딩 금지 (CHECK 제약 우회)"
    # 3) UPDATE SET balance = balance + :amt RETURNING (최종 상태에 CHECK 적용)
    assert "UPDATE token_balances" in sqls[2]
    assert "balance + :amt" in sqls[2]
    assert "RETURNING balance" in sqls[2]
    # 4) INSERT token_transactions 기록
    assert "INSERT INTO token_transactions" in sqls[3]


def test_credit_tokens_credit_also_uses_two_stage_upsert():
    """credit (amount > 0) 도 같은 패턴 — debit 과 분기 X."""
    db = _FakeDB()
    db.queue_first(None)
    db.queue_scalar(30)

    balance_after = tokens_service.credit_tokens(
        db,
        user_id="u1",
        amount=+30,
        kind=tokens_service.KIND_GRANT_ESSENTIALS,
        idempotency_key="essentials_grant:u1",
    )
    assert balance_after == 30

    sqls = [s for s, _ in db.executes]
    assert "INSERT INTO token_balances" in sqls[1]
    assert "DO NOTHING" in sqls[1]
    assert "UPDATE token_balances" in sqls[2]


def test_credit_tokens_idempotent_returns_existing_balance():
    """idempotency_key 일치 시 기존 balance 반환, UPDATE 호출 없음."""
    db = _FakeDB()
    # SELECT 가 balance_after=50 tuple 반환
    db.queue_first((50,))

    balance_after = tokens_service.credit_tokens(
        db,
        user_id="u1",
        amount=-10,
        kind=tokens_service.KIND_CONSUME_VERDICT_V2,
        idempotency_key="verdict:u1:v1",
    )
    assert balance_after == 50

    # SELECT 1개만 실행, UPDATE/INSERT 없음
    sqls = [s for s, _ in db.executes]
    assert len(sqls) == 1
    assert "SELECT balance_after" in sqls[0]


def test_credit_tokens_amount_goes_to_update_not_insert():
    """regression: INSERT 바인딩 파라미터에 amount 들어가면 CHECK 제약 재발 위험."""
    db = _FakeDB()
    db.queue_first(None)
    db.queue_scalar(20)

    tokens_service.credit_tokens(
        db,
        user_id="u1",
        amount=-10,
        kind=tokens_service.KIND_CONSUME_VERDICT_V2,
        idempotency_key="verdict:u1:v1",
    )

    # INSERT token_balances (index 1) 파라미터에 amt 없어야 함
    insert_stmt, insert_params = db.executes[1]
    assert "INSERT INTO token_balances" in insert_stmt
    assert "amt" not in insert_params, (
        f"INSERT params must not include 'amt' — got {insert_params}"
    )
    # UPDATE (index 2) 파라미터에 amt 포함돼야 함
    update_stmt, update_params = db.executes[2]
    assert "UPDATE token_balances" in update_stmt
    assert update_params.get("amt") == -10
