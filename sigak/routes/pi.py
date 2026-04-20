"""PI (Personal Image) 리포트 엔드포인트 — v2 BM.

- GET  /api/v1/pi          현재 해제 상태 + 해제 시 report_data
- POST /api/v1/pi/unlock   50 토큰 차감 + pi_reports upsert (unlocked_at=NOW())

PI 리포트는 유저당 1회 영속 해제. 재설정 시에도 유지(기존 sigak_report와 달리).

설계:
- unlocked_at IS NULL → 잠김
- unlocked_at IS NOT NULL → 해제됨
- report_data 는 생성 완료된 리포트 페이로드. 최초 해제 시점에 stub 으로 시작
  (status='generating'). 실제 리포트 생성 로직은 본인 후속 지시 대기.
- 기지불자(sigak_report_released=TRUE)는 migration 20260424에서 이미 pi_reports로
  grandfathering됨.
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from deps import db_session, get_current_user
from services import tokens as tokens_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pi", tags=["pi"])


class PIStatusResponse(BaseModel):
    unlocked: bool
    cost: int
    unlocked_at: Optional[str] = None
    report_data: Optional[dict] = None


class PIUnlockResponse(BaseModel):
    unlocked: bool
    unlocked_at: str
    report_data: dict
    token_balance: int


def _stub_report_data() -> dict:
    """최초 해제 시 채워지는 placeholder. 실제 생성 로직은 후속 지시로 교체."""
    return {
        "status": "generating",
        "face_analysis": None,
        "skin_tone": None,
        "gap_analysis": None,
        "hair_recommendations": None,
        "makeup_guide": None,
    }


@router.get("", response_model=PIStatusResponse)
def get_pi(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """PI 해제 상태 조회."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT unlocked_at, report_data "
            "FROM pi_reports WHERE user_id = :uid"
        ),
        {"uid": user["id"]},
    ).first()

    if not row or row.unlocked_at is None:
        return PIStatusResponse(
            unlocked=False,
            cost=tokens_service.COST_PI_UNLOCK,
        )

    return PIStatusResponse(
        unlocked=True,
        cost=tokens_service.COST_PI_UNLOCK,
        unlocked_at=row.unlocked_at.isoformat() if row.unlocked_at else None,
        report_data=row.report_data or {},
    )


@router.post("/unlock", response_model=PIUnlockResponse)
def unlock_pi(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """50 토큰 차감 + pi_reports.unlocked_at=NOW().

    흐름:
      1. 이미 unlocked 상태면 idempotent 리턴 (차감 없이 기존 데이터 반환)
      2. 잔액 < 50 이면 402
      3. 토큰 차감 — idempotency_key=``pi_unlock:{user_id}``
      4. pi_reports UPSERT: unlocked_at=NOW(), report_data=stub
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    existing = db.execute(
        text(
            "SELECT unlocked_at, report_data "
            "FROM pi_reports WHERE user_id = :uid"
        ),
        {"uid": user["id"]},
    ).first()

    # 이미 해제됨 — idempotent
    if existing and existing.unlocked_at is not None:
        return PIUnlockResponse(
            unlocked=True,
            unlocked_at=existing.unlocked_at.isoformat(),
            report_data=existing.report_data or {},
            token_balance=tokens_service.get_balance(db, user["id"]),
        )

    # 잔액 체크
    current_balance = tokens_service.get_balance(db, user["id"])
    if current_balance < tokens_service.COST_PI_UNLOCK:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {tokens_service.COST_PI_UNLOCK}토큰 필요, 현재 {current_balance}",
        )

    # 차감 — idempotent
    idempotency_key = f"pi_unlock:{user['id']}"
    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-tokens_service.COST_PI_UNLOCK,
            kind=tokens_service.KIND_CONSUME_PI,
            idempotency_key=idempotency_key,
            reference_id=user["id"],
            reference_type="user",
        )
    except IntegrityError:
        db.rollback()
        balance_after = tokens_service.get_balance(db, user["id"])
        logger.info(
            "[pi/unlock] idempotent re-unlock for user=%s (no charge)",
            user["id"],
        )

    # UPSERT pi_reports
    import json
    stub = _stub_report_data()
    now = datetime.utcnow()
    db.execute(
        text(
            """
            INSERT INTO pi_reports (user_id, unlocked_at, report_data, created_at, updated_at)
            VALUES (:uid, :now, CAST(:data AS jsonb), :now, :now)
            ON CONFLICT (user_id) DO UPDATE SET
              unlocked_at = EXCLUDED.unlocked_at,
              report_data = EXCLUDED.report_data,
              updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "uid": user["id"],
            "now": now,
            "data": json.dumps(stub, ensure_ascii=False),
        },
    )
    db.commit()

    return PIUnlockResponse(
        unlocked=True,
        unlocked_at=now.isoformat(),
        report_data=stub,
        token_balance=balance_after,
    )
