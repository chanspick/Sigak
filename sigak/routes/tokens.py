"""Token endpoints: balance + purchase intent.

Brief sections 7.1. Auth uses ``get_current_user_mock`` until JWT is wired —
swap to ``get_current_user`` in one pass when phase B completes.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from deps import db_session, get_current_user_mock
from services import tokens as tokens_service


router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


class BalanceResponse(BaseModel):
    balance: int
    updated_at: str | None


class PurchaseIntentRequest(BaseModel):
    pack_code: Literal["starter", "regular", "pro"]


class PurchaseIntentResponse(BaseModel):
    order_id: str
    amount_krw: int
    tokens_granted: int
    pg_order_id: str
    pg_amount: int
    pg_order_name: str


@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    user: dict = Depends(get_current_user_mock),
    db=Depends(db_session),
):
    if db is None:
        raise HTTPException(500, "DB unavailable")
    return BalanceResponse(
        balance=tokens_service.get_balance(db, user["id"]),
        updated_at=tokens_service.get_balance_updated_at(db, user["id"]),
    )


@router.post("/purchase-intent", response_model=PurchaseIntentResponse)
def create_purchase_intent(
    body: PurchaseIntentRequest,
    user: dict = Depends(get_current_user_mock),
    db=Depends(db_session),
):
    """Create a pending ``payment_orders`` row and return the identifiers
    the client will pass to the Toss SDK.

    We generate one id used both as our internal PK and as the Toss ``orderId``
    — brief keeps them separate column-wise for future provider flexibility,
    but sharing the value keeps MVP simple.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    try:
        pack = tokens_service.get_pack(body.pack_code)
    except KeyError:
        raise HTTPException(400, f"unknown pack_code: {body.pack_code}")

    order_id = f"pay_{uuid.uuid4().hex[:12]}"
    pg_order_id = order_id
    pg_order_name = f"SIGAK Token Pack — {pack.name_kr}"

    db.execute(
        text(
            "INSERT INTO payment_orders "
            "  (id, user_id, pack_code, amount_krw, tokens_granted, "
            "   status, pg_provider, pg_order_id) "
            "VALUES (:id, :uid, :pack, :amt, :tokens, "
            "        'pending', 'toss', :pg_order_id)"
        ),
        {
            "id": order_id,
            "uid": user["id"],
            "pack": pack.code,
            "amt": pack.amount_krw,
            "tokens": pack.tokens_granted,
            "pg_order_id": pg_order_id,
        },
    )
    db.commit()

    return PurchaseIntentResponse(
        order_id=order_id,
        amount_krw=pack.amount_krw,
        tokens_granted=pack.tokens_granted,
        pg_order_id=pg_order_id,
        pg_amount=pack.amount_krw,
        pg_order_name=pg_order_name,
    )
