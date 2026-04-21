"""Temporary diagnostic endpoints.

⚠️ TEMPORARY — 파이프라인 진단 목적 전용. 진단 종료 후 제거 예정.
Issue tracker: "remove _debug endpoint"

모든 엔드포인트는 JWT 인증 필수이며 본인 데이터만 반환. 서드파티/익명 접근 불가.
schema-repair 는 추가로 X-Admin-Key 헤더 검증 (ALTER TABLE/UPDATE 수행).
"""
import os

from fastapi import APIRouter, Depends, Header, HTTPException
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


@router.post("/schema-repair")
def schema_repair(
    user: dict = Depends(get_current_user),
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    db=Depends(db_session),
):
    """Case B 복구: gold_reading 컬럼만 누락 + alembic_version 뒤처진 상태.

    실행 SQL (단일 트랜잭션):
      ALTER TABLE verdicts ADD COLUMN IF NOT EXISTS gold_reading TEXT;
      UPDATE alembic_version SET version_num = '20260425_verdicts_gold_reading';

    JWT + X-Admin-Key 둘 다 필요. ADMIN_KEY 미설정 env 에서는 무조건 403.
    """
    expected = os.getenv("ADMIN_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(403, "admin key required")
    if db is None:
        raise HTTPException(500, "DB unavailable")

    before_row = db.execute(text("SELECT version_num FROM alembic_version")).first()
    version_before = before_row.version_num if before_row else None

    target_version = "20260425_verdicts_gold_reading"
    try:
        db.execute(
            text("ALTER TABLE verdicts ADD COLUMN IF NOT EXISTS gold_reading TEXT")
        )
        db.execute(
            text("UPDATE alembic_version SET version_num = :v"),
            {"v": target_version},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"repair failed: {e}")

    after_row = db.execute(text("SELECT version_num FROM alembic_version")).first()
    version_after = after_row.version_num if after_row else None

    return {
        "repaired": True,
        "column_added": "verdicts.gold_reading",
        "alembic_version_before": version_before,
        "alembic_version_after": version_after,
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
