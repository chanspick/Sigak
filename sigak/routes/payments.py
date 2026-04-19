"""Payment endpoints: frontend confirm + Toss webhook.

Two paths can credit tokens for the same payment (brief 8.2 belt+suspenders).
Both use ``idempotency_key = "credit:{order_id}"`` so only one succeeds; the
other short-circuits via ``credit_tokens``'s existence check.

``/payments/webhook`` is mounted at the root, not under ``/api/v1``, because
that's the URL registered in the Toss console. Toss v2 does NOT sign webhook
payloads — we re-verify every incoming event via ``services.payments.get_payment``
(see services/payments.py::get_payment docstring).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from deps import db_session, get_current_user
from services import payments as payments_service
from services import tokens as tokens_service


logger = logging.getLogger(__name__)

# Two separate routers: one under /api/v1/payments, one at root for the webhook.
confirm_router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
webhook_router = APIRouter(tags=["payments"])


class ConfirmRequest(BaseModel):
    payment_key: str
    amount: int


class ConfirmResponse(BaseModel):
    order_id: str
    status: str   # 'paid' | 'failed'
    balance_after: int


# ─────────────────────────────────────────────
#  POST /api/v1/payments/confirm/{order_id}
# ─────────────────────────────────────────────

@confirm_router.post("/confirm/{order_id}", response_model=ConfirmResponse)
async def confirm_payment(
    order_id: str,
    body: ConfirmRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Approve a payment after the frontend Toss SDK redirects with success.

    Flow:
      1. Load our ``payment_orders`` row, verify ownership and amount
      2. If already paid → short-circuit with current balance (idempotent)
      3. Call Toss confirm; treat ``ALREADY_PROCESSED_PAYMENT`` as success
      4. Mark order paid + credit tokens in one DB transaction
      5. Return new balance
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    order = db.execute(
        text(
            "SELECT id, user_id, amount_krw, tokens_granted, status, pg_order_id "
            "FROM payment_orders WHERE id = :id"
        ),
        {"id": order_id},
    ).first()
    if not order:
        raise HTTPException(404, "주문을 찾을 수 없습니다")
    if order.user_id != user["id"]:
        raise HTTPException(403, "본인 주문이 아닙니다")

    # Idempotent short-circuit: order already marked paid (webhook beat us).
    if order.status == "paid":
        return ConfirmResponse(
            order_id=order_id,
            status="paid",
            balance_after=tokens_service.get_balance(db, user["id"]),
        )

    if order.status != "pending":
        raise HTTPException(400, f"주문 상태가 결제 불가입니다: {order.status}")

    if order.amount_krw != body.amount:
        raise HTTPException(400, "결제 금액이 일치하지 않습니다")

    try:
        toss_payment = await payments_service.confirm_payment(
            payment_key=body.payment_key,
            order_id=order.pg_order_id,
            amount=body.amount,
        )
    except payments_service.TossError as e:
        if e.code == "ALREADY_PROCESSED_PAYMENT":
            # Webhook or earlier confirm already got there; fetch current state.
            toss_payment = await payments_service.get_payment(body.payment_key)
        else:
            # Persist failure reason for ops debugging. Amount check was already
            # validated above, so this is PG-side rejection (bad card, insufficient
            # funds, network error on Toss end, etc).
            db.execute(
                text(
                    "UPDATE payment_orders SET status='failed', failed_reason=:r "
                    "WHERE id=:id AND status='pending'"
                ),
                {"r": f"{e.code}: {e.message}"[:500], "id": order_id},
            )
            db.commit()
            raise HTTPException(402, f"결제 승인 실패: {e.code}")

    if toss_payment.get("status") != "DONE":
        raise HTTPException(
            402,
            f"결제가 완료되지 않았습니다 (toss status={toss_payment.get('status')})",
        )

    # Mark order paid (idempotent via WHERE clause) + credit tokens.
    # credit_tokens is idempotent via its own idempotency_key — so even if the
    # UPDATE below affects 0 rows (webhook beat us), the credit still dedupes.
    db.execute(
        text(
            "UPDATE payment_orders SET "
            "  status='paid', pg_payment_key=:pk, paid_at=NOW() "
            "WHERE id=:id AND status='pending'"
        ),
        {"pk": body.payment_key, "id": order_id},
    )
    balance_after = tokens_service.credit_tokens(
        db,
        user_id=user["id"],
        amount=order.tokens_granted,
        kind=tokens_service.KIND_PURCHASE,
        idempotency_key=f"credit:{order_id}",
        reference_id=order_id,
        reference_type="order",
    )
    db.commit()

    return ConfirmResponse(order_id=order_id, status="paid", balance_after=balance_after)


# ─────────────────────────────────────────────
#  POST /payments/webhook  (root, no /api/v1 prefix)
# ─────────────────────────────────────────────

def _extract_payment_key(body: dict) -> Optional[str]:
    """Toss v2 nests the payment under ``data``; older callbacks may be flat."""
    data = body.get("data")
    if isinstance(data, dict):
        pk = data.get("paymentKey")
        if pk:
            return pk
    return body.get("paymentKey")


@webhook_router.post("/payments/webhook")
async def payments_webhook(request: Request, db=Depends(db_session)):
    """Receive PAYMENT_STATUS_CHANGED / CANCEL_STATUS_CHANGED from Toss.

    We do NOT trust the payload beyond extracting paymentKey — Toss v2 has no
    signature. Authoritative status comes from a fresh ``get_payment`` call
    using our secret key.

    Response policy:
      - 200 on parse failures → Toss does NOT retry (we log and give up)
      - 500 on Toss API / DB errors → Toss retries on its schedule
      - 200 on unknown paymentKey → not our order, nothing to do
      - 200 on successful processing
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("webhook: json parse failed: %s", e)
        return {"ok": True}

    payment_key = _extract_payment_key(body)
    if not payment_key:
        logger.warning("webhook: paymentKey missing in body keys=%s", list(body.keys()))
        return {"ok": True}

    # Authoritative lookup — this is our auth.
    try:
        toss_payment = await payments_service.get_payment(payment_key)
    except payments_service.TossError as e:
        logger.error("webhook: get_payment failed code=%s msg=%s", e.code, e.message)
        if e.code in ("NOT_FOUND_PAYMENT", "INVALID_REQUEST"):
            # Toss says no such payment — forged webhook or misrouted. Don't retry.
            return {"ok": True}
        # Network / 5xx / unknown → let Toss retry by returning an error.
        raise HTTPException(500, "toss lookup failed")

    toss_order_id = toss_payment.get("orderId")
    toss_status = toss_payment.get("status")
    if not toss_order_id:
        logger.warning("webhook: toss response missing orderId: %s", toss_payment)
        return {"ok": True}

    if db is None:
        raise HTTPException(500, "DB unavailable")

    order = db.execute(
        text(
            "SELECT id, user_id, amount_krw, tokens_granted, status "
            "FROM payment_orders WHERE pg_order_id = :pg"
        ),
        {"pg": toss_order_id},
    ).first()
    if not order:
        # Someone else's order or a test event against our URL. Not an error.
        logger.info("webhook: no payment_orders row for pg_order_id=%s", toss_order_id)
        return {"ok": True}

    if toss_status == "DONE":
        # Mark paid (noop if already paid), credit tokens idempotently.
        db.execute(
            text(
                "UPDATE payment_orders SET "
                "  status='paid', pg_payment_key=:pk, paid_at=NOW() "
                "WHERE id=:id AND status='pending'"
            ),
            {"pk": payment_key, "id": order.id},
        )
        db.commit()
        tokens_service.credit_tokens_safe(
            db,
            user_id=order.user_id,
            amount=order.tokens_granted,
            kind=tokens_service.KIND_PURCHASE,
            idempotency_key=f"credit:{order.id}",
            reference_id=order.id,
            reference_type="order",
        )
        return {"ok": True}

    if toss_status in ("CANCELED", "PARTIAL_CANCELED"):
        # Full refund path: mark order refunded. Token debit via manual ops
        # for MVP — brief doesn't spec automatic clawback and consumed tokens
        # may already be spent. Flag for staff review.
        db.execute(
            text(
                "UPDATE payment_orders SET status='refunded' "
                "WHERE id=:id AND status IN ('paid', 'pending')"
            ),
            {"id": order.id},
        )
        db.commit()
        logger.warning(
            "webhook: cancel received for order=%s user=%s — manual token review required",
            order.id, order.user_id,
        )
        return {"ok": True}

    if toss_status in ("ABORTED", "EXPIRED"):
        db.execute(
            text(
                "UPDATE payment_orders SET status='failed', failed_reason=:r "
                "WHERE id=:id AND status='pending'"
            ),
            {"r": f"toss:{toss_status}", "id": order.id},
        )
        db.commit()
        return {"ok": True}

    # READY / IN_PROGRESS / WAITING_FOR_DEPOSIT — in-flight states, nothing to do.
    logger.info("webhook: in-flight status=%s order=%s (noop)", toss_status, order.id)
    return {"ok": True}
