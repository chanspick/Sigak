"""Token pack catalog + balance/transaction DB operations (MVP v1.1).

Catalog section matches brief 6.11. Balance ops are idempotent via the
``token_transactions.idempotency_key`` UNIQUE constraint — the primary
defense against double-credit when both the frontend ``/payments/confirm``
path and the ``/payments/webhook`` path fire for the same payment.
"""
from typing import NamedTuple, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


class TokenPack(NamedTuple):
    code: str           # URL-safe identifier stored in payment_orders.pack_code
    name_kr: str        # Display name on purchase screen
    amount_krw: int     # Price in KRW, sent to Toss as ``amount``
    tokens_granted: int # Credited to token_balances on successful payment


STARTER = TokenPack(code="starter", name_kr="Starter", amount_krw=10_000, tokens_granted=100)
REGULAR = TokenPack(code="regular", name_kr="Regular", amount_krw=25_000, tokens_granted=280)
PRO = TokenPack(code="pro",     name_kr="Pro",     amount_krw=50_000, tokens_granted=600)

PACKS: dict[str, TokenPack] = {
    STARTER.code: STARTER,
    REGULAR.code: REGULAR,
    PRO.code: PRO,
}


def get_pack(pack_code: str) -> TokenPack:
    """Raises KeyError on unknown code — endpoint layer translates to HTTP 400."""
    return PACKS[pack_code]


# Consumption prices
COST_REASONING_UNLOCK = 5       # /verdicts/{id}/unlock-reasoning (legacy)
COST_BLUR_RELEASE = 50          # /verdicts/{id}/release-blur (deprecated — v2 BM에서 분리)
COST_MONTHLY_REPORT = 30        # monthly re-run; endpoint TBD

# v2 BM (2026-04-24): 3단 구조
COST_DIAGNOSIS_UNLOCK = 10      # verdict 단위 진단 해제 — /verdicts/{id}/unlock-diagnosis
COST_PI_UNLOCK = 50             # 유저 1회 영속 PI 해제 — /pi/unlock

# v2 Verdict 2.0 (2026-04-27, SPEC-ONBOARDING-V2 REQ-VERDICT-003)
COST_VERDICT_V2_UNLOCK = 10     # full_content 해제 — /api/v2/verdict/{id}/unlock


# ─────────────────────────────────────────────
#  DB ops
# ─────────────────────────────────────────────

# kind values — brief section 5.2. Keep this in sync with CHECK-style docs.
KIND_PURCHASE = "purchase"
KIND_CONSUME_REASONING = "consume_reasoning"
KIND_CONSUME_BLUR_RELEASE = "consume_blur_release"
KIND_CONSUME_MONTHLY_REPORT = "consume_monthly_report"
KIND_CONSUME_OTHER = "consume_other"
KIND_CONSUME_DIAGNOSIS = "consume_diagnosis"     # v2 BM
KIND_CONSUME_PI = "consume_pi"                   # v2 BM
KIND_CONSUME_VERDICT_V2 = "consume_verdict_v2"   # v2 BM (Verdict 2.0 full unlock)
KIND_REFUND = "refund"
KIND_ADMIN_GRANT = "admin_grant"


def get_balance(db, user_id: str) -> int:
    """Return current balance for ``user_id``. Zero if no row yet."""
    row = db.execute(
        text("SELECT balance FROM token_balances WHERE user_id = :uid"),
        {"uid": user_id},
    ).first()
    return int(row[0]) if row else 0


def get_balance_updated_at(db, user_id: str) -> Optional[str]:
    """Return ISO-8601 timestamp of last balance update, or None."""
    row = db.execute(
        text("SELECT updated_at FROM token_balances WHERE user_id = :uid"),
        {"uid": user_id},
    ).first()
    if not row or not row[0]:
        return None
    return row[0].isoformat()


def credit_tokens(
    db,
    *,
    user_id: str,
    amount: int,
    kind: str,
    idempotency_key: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
) -> int:
    """Atomically credit (positive) or debit (negative) tokens with idempotency.

    Returns ``balance_after``. If ``idempotency_key`` has already been used,
    returns the stored ``balance_after`` without mutating state — so retrying
    the same payment confirm or webhook is safe and cheap.

    Transaction ownership: this function does NOT commit. Caller is responsible
    for commit/rollback. That lets a caller bundle "mark order paid + credit
    tokens" into one atomic unit when desired.

    Race condition handling: if two concurrent callers use the same
    ``idempotency_key``, the UNIQUE constraint on the transactions table makes
    one of them raise IntegrityError on INSERT. Caller should catch, rollback,
    and call again — the second attempt short-circuits on the existence check.

    Negative ``amount`` is allowed for debits (e.g. blur release, reasoning
    unlock). Caller must check balance beforehand to avoid the CHECK
    constraint violation on ``token_balances.balance >= 0``.
    """
    existing = db.execute(
        text(
            "SELECT balance_after FROM token_transactions "
            "WHERE idempotency_key = :k"
        ),
        {"k": idempotency_key},
    ).first()
    if existing is not None:
        return int(existing[0])

    new_balance = db.execute(
        text(
            "INSERT INTO token_balances (user_id, balance, updated_at) "
            "VALUES (:uid, :amt, NOW()) "
            "ON CONFLICT (user_id) DO UPDATE "
            "  SET balance = token_balances.balance + EXCLUDED.balance, "
            "      updated_at = NOW() "
            "RETURNING balance"
        ),
        {"uid": user_id, "amt": amount},
    ).scalar()

    db.execute(
        text(
            "INSERT INTO token_transactions "
            "  (user_id, kind, amount, balance_after, "
            "   reference_id, reference_type, idempotency_key) "
            "VALUES (:uid, :kind, :amt, :bal, :rid, :rtype, :idem)"
        ),
        {
            "uid": user_id,
            "kind": kind,
            "amt": amount,
            "bal": new_balance,
            "rid": reference_id,
            "rtype": reference_type,
            "idem": idempotency_key,
        },
    )
    return int(new_balance)


def credit_tokens_safe(
    db,
    *,
    user_id: str,
    amount: int,
    kind: str,
    idempotency_key: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
) -> int:
    """Convenience wrapper that catches the IntegrityError race window.

    Use this when the caller doesn't want to orchestrate the retry itself —
    e.g. inside a webhook handler where we just want "credit if not yet".
    Commits on success, rolls back on conflict then re-reads the winning row.
    """
    try:
        balance = credit_tokens(
            db,
            user_id=user_id,
            amount=amount,
            kind=kind,
            idempotency_key=idempotency_key,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        db.commit()
        return balance
    except IntegrityError:
        db.rollback()
        row = db.execute(
            text(
                "SELECT balance_after FROM token_transactions "
                "WHERE idempotency_key = :k"
            ),
            {"k": idempotency_key},
        ).first()
        if row is not None:
            return int(row[0])
        raise
