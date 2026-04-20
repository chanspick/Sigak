"""시각 리포트 엔드포인트 (MVP v1.2).

시각 리포트 = 온보딩 답변 기반 유저 분석 요약. 30토큰 소비 시 해제.

- GET  /api/v1/sigak-report           현재 해제 상태 + (해제 시) onboarding_data
- POST /api/v1/sigak-report/release   30토큰 차감 + sigak_report_released=TRUE

설계 메모:
- 리포트 데이터 자체는 users.onboarding_data 그대로 반환 (프론트가 한글 라벨로 렌더).
- LLM 해석(interview_interpretation)은 이미 캐시 있음 — 추후 응답에 포함 가능.
- release는 idempotent — 시각 재설정 후 재해제 시도 시 추가 차감 없음
  (token_transactions.idempotency_key UNIQUE 제약이 보호).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from deps import db_session, get_current_user
from services import tokens as tokens_service


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sigak-report", tags=["sigak-report"])

COST_SIGAK_REPORT = 30
KIND_CONSUME_SIGAK_REPORT = "consume_sigak_report"


class SigakReportResponse(BaseModel):
    released: bool
    cost: int
    onboarding_data: Optional[dict] = None


class ReleaseSigakReportResponse(BaseModel):
    released: bool
    onboarding_data: dict
    balance_after: int


@router.get("", response_model=SigakReportResponse)
def get_sigak_report(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """현재 해제 상태 + (해제됐으면) 온보딩 데이터 반환."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT sigak_report_released, onboarding_data "
            "FROM users WHERE id = :uid"
        ),
        {"uid": user["id"]},
    ).first()
    if not row:
        raise HTTPException(404, "user not found")

    return SigakReportResponse(
        released=bool(row.sigak_report_released),
        cost=COST_SIGAK_REPORT,
        onboarding_data=row.onboarding_data if row.sigak_report_released else None,
    )


@router.post("/release", response_model=ReleaseSigakReportResponse)
def release_sigak_report(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """30토큰 차감 + sigak_report_released=TRUE.

    흐름:
      1. 온보딩 미완이면 409
      2. 이미 해제된 상태면 idempotent 리턴 (차감 없이 현재 상태 반환)
      3. 잔액 체크 — 부족하면 402
      4. credit_tokens(음수) — idempotency_key=`sigak_report:{user_id}`
         * 재설정 후 재해제 시 동일 key라 IntegrityError → 추가 차감 없음
      5. sigak_report_released=TRUE 플립
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT sigak_report_released, onboarding_data, onboarding_completed "
            "FROM users WHERE id = :uid"
        ),
        {"uid": user["id"]},
    ).first()
    if not row:
        raise HTTPException(404, "user not found")
    if not row.onboarding_completed:
        raise HTTPException(409, "온보딩을 먼저 완료해주세요")

    # 이미 해제됨 — idempotent return
    if row.sigak_report_released:
        return ReleaseSigakReportResponse(
            released=True,
            onboarding_data=row.onboarding_data or {},
            balance_after=tokens_service.get_balance(db, user["id"]),
        )

    # 잔액 선체크 (에러 메시지 품질 위해)
    current_balance = tokens_service.get_balance(db, user["id"])
    if current_balance < COST_SIGAK_REPORT:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {COST_SIGAK_REPORT}토큰 필요, 현재 {current_balance}",
        )

    # 토큰 차감. 재해제 시 idempotency_key 중복 → IntegrityError → 차감 없이 진행.
    idempotency_key = f"sigak_report:{user['id']}"
    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-COST_SIGAK_REPORT,
            kind=KIND_CONSUME_SIGAK_REPORT,
            idempotency_key=idempotency_key,
            reference_id=user["id"],
            reference_type="user",
        )
    except IntegrityError:
        db.rollback()
        balance_after = tokens_service.get_balance(db, user["id"])
        logger.info(
            "[sigak-report] idempotent re-release for user=%s (no charge)",
            user["id"],
        )

    # 플래그 set
    db.execute(
        text(
            "UPDATE users SET sigak_report_released = TRUE "
            "WHERE id = :uid AND sigak_report_released = FALSE"
        ),
        {"uid": user["id"]},
    )
    db.commit()

    return ReleaseSigakReportResponse(
        released=True,
        onboarding_data=row.onboarding_data or {},
        balance_after=balance_after,
    )
