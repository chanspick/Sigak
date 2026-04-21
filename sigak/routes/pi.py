"""PI (Personal Image) 리포트 엔드포인트 — v1 + v2 (D5 Phase 3).

v1 (unchanged):
  GET  /api/v1/pi          현재 해제 상태 + 해제 시 report_data
  POST /api/v1/pi/unlock   50 토큰 차감 + pi_reports upsert (unlocked_at=NOW())

v2 (D5 Phase 3):
  GET  /api/v2/pi          동일 계약, user_profiles row 전제
  POST /api/v2/pi/unlock   50 토큰 차감 + user_profile seed 를 report_data 에 반영

PI 리포트는 유저당 1회 영속 해제. 재설정 시에도 유지.

v1 / v2 공존 전략:
- pi_reports 테이블은 동일 (user_id PK).
- v2 는 user_profiles row 필수. 없으면 409 → 유저는 v2 온보딩 선행 필요.
- 기 v1 해제자는 v1 payload 유지, v2 로 덮어쓰지 않음 (idempotent 해제 로직).
- v2 해제 후 v1 GET 을 호출해도 동일 row 를 읽으므로 report_data 는 v2 payload.
"""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from deps import db_session, get_current_user
from services import pi as pi_service
from services import tokens as tokens_service
from services import user_profiles as user_profiles_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pi", tags=["pi"])
router_v2 = APIRouter(prefix="/api/v2/pi", tags=["pi-v2"])


# ─────────────────────────────────────────────
#  Response schemas (공용)
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
#  공용 DB helpers
# ─────────────────────────────────────────────

def _select_report(db, user_id: str):
    return db.execute(
        text(
            "SELECT unlocked_at, report_data "
            "FROM pi_reports WHERE user_id = :uid"
        ),
        {"uid": user_id},
    ).first()


def _upsert_report(db, user_id: str, data: dict, now: datetime) -> None:
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
            "uid": user_id,
            "now": now,
            "data": json.dumps(data, ensure_ascii=False),
        },
    )


def _debit_tokens_for_unlock(db, user_id: str) -> int:
    """50 토큰 차감. IntegrityError 시 idempotent 재계산.

    Returns balance_after (차감 성공 또는 기존 잔액).
    Raises HTTPException(402) 잔액 부족 시.
    """
    current_balance = tokens_service.get_balance(db, user_id)
    if current_balance < tokens_service.COST_PI_UNLOCK:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {tokens_service.COST_PI_UNLOCK}토큰 필요, "
            f"현재 {current_balance}",
        )

    idempotency_key = f"pi_unlock:{user_id}"
    try:
        return tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=-tokens_service.COST_PI_UNLOCK,
            kind=tokens_service.KIND_CONSUME_PI,
            idempotency_key=idempotency_key,
            reference_id=user_id,
            reference_type="user",
        )
    except IntegrityError:
        db.rollback()
        logger.info("[pi/unlock] idempotent re-unlock user=%s (no charge)", user_id)
        return tokens_service.get_balance(db, user_id)


# ─────────────────────────────────────────────
#  v1 endpoints — unchanged behavior
# ─────────────────────────────────────────────

@router.get("", response_model=PIStatusResponse)
def get_pi(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """PI 해제 상태 조회 (v1)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = _select_report(db, user["id"])
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
    """50 토큰 차감 + pi_reports.unlocked_at=NOW() (v1 stub)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    existing = _select_report(db, user["id"])
    if existing and existing.unlocked_at is not None:
        return PIUnlockResponse(
            unlocked=True,
            unlocked_at=existing.unlocked_at.isoformat(),
            report_data=existing.report_data or {},
            token_balance=tokens_service.get_balance(db, user["id"]),
        )

    balance_after = _debit_tokens_for_unlock(db, user["id"])

    stub = pi_service.build_v1_report_data()
    now = datetime.utcnow()
    _upsert_report(db, user["id"], stub, now)
    db.commit()

    return PIUnlockResponse(
        unlocked=True,
        unlocked_at=now.isoformat(),
        report_data=stub,
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  v2 endpoints — user_profile 통합
# ─────────────────────────────────────────────

@router_v2.get("", response_model=PIStatusResponse)
def get_pi_v2(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """v2 해제 상태. GET 은 user_profiles 요구 없음 (해제 여부만 판정)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = _select_report(db, user["id"])
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


@router_v2.post("/unlock", response_model=PIUnlockResponse)
def unlock_pi_v2(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """50 토큰 차감 + user_profile seed 반영된 report_data 저장.

    전제: user_profiles row 존재 (v2 온보딩 완료).

    흐름:
      1. user_profile 로드 (없으면 409)
      2. 이미 unlocked → idempotent 리턴 (재저장 없음, 기존 payload 유지)
      3. 잔액 체크 + 차감 (v1 과 동일 idempotency_key)
      4. services.pi.build_v2_report_data(user_profile) 로 payload 생성
      5. pi_reports UPSERT
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    profile = user_profiles_service.get_profile(db, user["id"])
    if profile is None:
        raise HTTPException(
            409,
            "시각이 본 나 리포트를 여시려면 온보딩이 먼저 필요합니다.",
        )

    existing = _select_report(db, user["id"])
    if existing and existing.unlocked_at is not None:
        return PIUnlockResponse(
            unlocked=True,
            unlocked_at=existing.unlocked_at.isoformat(),
            report_data=existing.report_data or {},
            token_balance=tokens_service.get_balance(db, user["id"]),
        )

    balance_after = _debit_tokens_for_unlock(db, user["id"])

    payload = pi_service.build_v2_report_data(profile)
    now = datetime.utcnow()
    _upsert_report(db, user["id"], payload, now)
    db.commit()

    return PIUnlockResponse(
        unlocked=True,
        unlocked_at=now.isoformat(),
        report_data=payload,
        token_balance=balance_after,
    )
