"""Temporary diagnostic endpoints.

⚠️ TEMPORARY — 파이프라인 진단 목적 전용. 진단 종료 후 제거 예정.
Issue tracker: "remove _debug endpoint"

모든 엔드포인트는 JWT 인증 필수이며 본인 데이터만 반환. 서드파티/익명 접근 불가.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from db import User as DBUser
from deps import db_session, get_current_user


router = APIRouter(prefix="/api/v1/_debug", tags=["_debug"])


@router.get("/verdict-dump")
def verdict_dump(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """본인의 가장 최근 verdict 1건 + 관련 캐시 덤프.

    target 좌표가 실제 LLM 계산값인지 {0,0,0} fallback인지 확인용.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT id, created_at, candidate_count, "
            "       coordinates_snapshot, gold_reading "
            "FROM verdicts "
            "WHERE user_id = :uid "
            "ORDER BY created_at DESC "
            "LIMIT 1"
        ),
        {"uid": user["id"]},
    ).first()
    if row is None:
        raise HTTPException(404, "no verdicts for this user")

    user_row = db.query(DBUser).filter(DBUser.id == user["id"]).first()
    interview_interp = user_row.interview_interpretation if user_row else None
    onboarding_present = bool(
        user_row and user_row.onboarding_data
    )

    return {
        "verdict_id": row.id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "candidate_count": row.candidate_count,
        "coordinates_snapshot": row.coordinates_snapshot,
        "gold_reading": row.gold_reading or "",
        "user_interview_interpretation": interview_interp,
        "user_onboarding_data_present": onboarding_present,
    }
