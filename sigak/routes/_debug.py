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


@router.get("/schema-state")
def schema_state(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """프로덕션 DB 스키마와 alembic_version의 현재 상태 스냅샷.

    alembic upgrade 실패가 "이미 있는 컬럼을 또 추가" 패턴일 때 복구 케이스
    판정용. alembic_version이 DB에 기록한 상태와 실제 스키마 상태의 갭을
    한 눈에 보기.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    alembic_row = db.execute(text("SELECT version_num FROM alembic_version")).first()
    alembic_version = alembic_row.version_num if alembic_row else None

    probe = db.execute(
        text(
            "SELECT "
            "  EXISTS(SELECT 1 FROM information_schema.columns "
            "         WHERE table_name='users' AND column_name='consent_completed') AS u_consent_completed, "
            "  EXISTS(SELECT 1 FROM information_schema.columns "
            "         WHERE table_name='users' AND column_name='consent_data') AS u_consent_data, "
            "  EXISTS(SELECT 1 FROM information_schema.columns "
            "         WHERE table_name='users' AND column_name='sigak_report_released') AS u_sigak_report, "
            "  EXISTS(SELECT 1 FROM information_schema.columns "
            "         WHERE table_name='verdicts' AND column_name='diagnosis_unlocked') AS v_diagnosis_unlocked, "
            "  EXISTS(SELECT 1 FROM information_schema.columns "
            "         WHERE table_name='verdicts' AND column_name='gold_reading') AS v_gold_reading, "
            "  EXISTS(SELECT 1 FROM information_schema.tables "
            "         WHERE table_name='pi_reports') AS t_pi_reports"
        )
    ).first()

    return {
        "alembic_version": alembic_version,
        "columns": {
            "users.consent_completed": bool(probe.u_consent_completed),
            "users.consent_data": bool(probe.u_consent_data),
            "users.sigak_report_released": bool(probe.u_sigak_report),
            "verdicts.diagnosis_unlocked": bool(probe.v_diagnosis_unlocked),
            "verdicts.gold_reading": bool(probe.v_gold_reading),
            "pi_reports_table_exists": bool(probe.t_pi_reports),
        },
    }


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
