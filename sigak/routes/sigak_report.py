"""시각 리포트 엔드포인트 (MVP v1.2).

시각 리포트 = 온보딩 + LLM #2(interpret_interview) 결과 기반 유저 분석 요약.
30 토큰 소비 시 해제.

응답 구조:
  - onboarding_data: 체형/얼굴/추구미/자기인식 원본 답변 (프론트가 한글 라벨로 렌더)
  - interpretation: LLM 자연어 해석 — "시각이 본 당신" 문단
  - reference_base: 해석의 참조 앵커 (e.g., "따뜻한 첫사랑")
  - chugumi_coords: {shape, volume, age} -1..1 — 추구미 좌표

설계 메모:
- 첫 해제 시 get_or_compute_interview_interpretation 호출해 LLM 실행 + 캐시.
- 재해제 시 cache hit → LLM 호출 없음.
- release는 idempotent — 시각 재설정 후 재해제 시 추가 차감 없음.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import User as DBUser
from deps import db_session, get_current_user
from services import tokens as tokens_service
from services.llm_cache import get_or_compute_interview_interpretation


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sigak-report", tags=["sigak-report"])

COST_SIGAK_REPORT = 30
KIND_CONSUME_SIGAK_REPORT = "consume_sigak_report"


class AxisPoint(BaseModel):
    shape: float
    volume: float
    age: float


class SigakReportResponse(BaseModel):
    released: bool
    cost: int
    onboarding_data: Optional[dict] = None
    interpretation: Optional[str] = None
    reference_base: Optional[str] = None
    chugumi_coords: Optional[AxisPoint] = None


class ReleaseSigakReportResponse(BaseModel):
    released: bool
    onboarding_data: dict
    interpretation: Optional[str] = None
    reference_base: Optional[str] = None
    chugumi_coords: Optional[AxisPoint] = None
    balance_after: int


def _extract_interp_fields(interp: Optional[dict]) -> tuple[
    Optional[str], Optional[str], Optional[AxisPoint]
]:
    """llm_cache.get_or_compute_interview_interpretation 응답을 분해.
    파싱 실패(confidence=0.0) 케이스도 방어.
    """
    if not interp:
        return None, None, None
    interpretation = interp.get("interpretation") or None
    reference_base = interp.get("reference_base") or None
    coords_raw = interp.get("coordinates") or {}
    chugumi_coords = None
    if isinstance(coords_raw, dict):
        try:
            chugumi_coords = AxisPoint(
                shape=float(coords_raw.get("shape", 0.0)),
                volume=float(coords_raw.get("volume", 0.0)),
                age=float(coords_raw.get("age", 0.0)),
            )
        except (TypeError, ValueError):
            chugumi_coords = None
    return interpretation, reference_base, chugumi_coords


@router.get("", response_model=SigakReportResponse)
def get_sigak_report(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """현재 해제 상태 + (해제됐으면) 온보딩 데이터 + LLM 해석 반환."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_row = db.query(DBUser).filter(DBUser.id == user["id"]).first()
    if not user_row:
        raise HTTPException(404, "user not found")

    if not user_row.sigak_report_released:
        return SigakReportResponse(
            released=False,
            cost=COST_SIGAK_REPORT,
            onboarding_data=None,
        )

    # 해제된 상태 — 캐시된 interview_interpretation 로드 (있으면)
    interp = user_row.interview_interpretation or None
    interpretation, reference_base, chugumi_coords = _extract_interp_fields(interp)

    return SigakReportResponse(
        released=True,
        cost=COST_SIGAK_REPORT,
        onboarding_data=user_row.onboarding_data or {},
        interpretation=interpretation,
        reference_base=reference_base,
        chugumi_coords=chugumi_coords,
    )


@router.post("/release", response_model=ReleaseSigakReportResponse)
def release_sigak_report(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """30토큰 차감 + sigak_report_released=TRUE + LLM 해석 compute/cache.

    흐름:
      1. 온보딩 미완이면 409
      2. 이미 해제된 상태면 idempotent 리턴 (차감 없이 현재 interpretation 반환)
      3. 잔액 체크 — 부족하면 402
      4. credit_tokens(음수) — idempotency_key=`sigak_report:{user_id}`
         * 재설정 후 재해제 시 동일 key라 IntegrityError → 추가 차감 없음
      5. sigak_report_released=TRUE 플립
      6. LLM #2 호출 (cache hit면 compute skip)
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user_row = db.query(DBUser).filter(DBUser.id == user["id"]).first()
    if not user_row:
        raise HTTPException(404, "user not found")
    if not user_row.onboarding_completed:
        raise HTTPException(409, "온보딩을 먼저 완료해주세요")

    def _build_response(balance_after: int) -> ReleaseSigakReportResponse:
        """LLM 호출 + 응답 조립. 예외는 상위에서 처리하지 않고 옵션 필드로 nullable 반환."""
        interp: Optional[dict] = None
        try:
            interp = get_or_compute_interview_interpretation(
                db, user_row, gender=(user_row.gender or "female")
            )
        except Exception as e:
            logger.error(
                "[sigak-report] interview interpretation failed for user=%s: %s",
                user_row.id, e,
            )
        interpretation, reference_base, chugumi_coords = _extract_interp_fields(interp)
        return ReleaseSigakReportResponse(
            released=True,
            onboarding_data=user_row.onboarding_data or {},
            interpretation=interpretation,
            reference_base=reference_base,
            chugumi_coords=chugumi_coords,
            balance_after=balance_after,
        )

    # 이미 해제됨 — idempotent: 토큰 차감 없이 현재 상태 반환
    if user_row.sigak_report_released:
        return _build_response(tokens_service.get_balance(db, user_row.id))

    # 잔액 선체크
    current_balance = tokens_service.get_balance(db, user_row.id)
    if current_balance < COST_SIGAK_REPORT:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {COST_SIGAK_REPORT}토큰 필요, 현재 {current_balance}",
        )

    # 차감. 재해제 시 idempotency_key 중복 → IntegrityError → 차감 없이 진행.
    idempotency_key = f"sigak_report:{user_row.id}"
    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user_row.id,
            amount=-COST_SIGAK_REPORT,
            kind=KIND_CONSUME_SIGAK_REPORT,
            idempotency_key=idempotency_key,
            reference_id=user_row.id,
            reference_type="user",
        )
    except IntegrityError:
        db.rollback()
        balance_after = tokens_service.get_balance(db, user_row.id)
        logger.info(
            "[sigak-report] idempotent re-release for user=%s (no charge)",
            user_row.id,
        )

    # 플래그 set
    db.execute(
        text(
            "UPDATE users SET sigak_report_released = TRUE "
            "WHERE id = :uid AND sigak_report_released = FALSE"
        ),
        {"uid": user_row.id},
    )
    db.commit()

    # 재조회 (interview_interpretation 캐시 업데이트 반영)
    db.refresh(user_row)
    return _build_response(balance_after)
