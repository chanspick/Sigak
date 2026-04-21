"""Shared FastAPI dependencies (MVP v1.1).

`get_current_user` is the canonical JWT-based auth dependency. Apply it to
every route except: /health, /auth/kakao/*, /payments/webhook (brief 4.4).

For local testing without going through Kakao OAuth, use
``POST /api/v1/auth/dev-issue-jwt`` (ADMIN_KEY gated) to mint a JWT for any
existing user id.
"""
from typing import Optional

from fastapi import Header, HTTPException, status

from db import get_db, User as DBUser
from services.auth import verify_jwt


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Validate Bearer JWT, return user dict.

    Returns a plain dict (not the SQLAlchemy model) so downstream code doesn't
    hold a session open. DB is opened/closed within this dependency.

    Raises 401 on any failure mode — missing header, invalid token, unknown user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "인증이 필요합니다")

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_jwt(token)
    if not claims:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "유효하지 않은 토큰입니다")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "잘못된 토큰입니다")

    db = get_db()
    if db is None:
        # DB 미초기화 상태 — 토큰 claim만으로 최소 식별 정보 반환.
        # 이 경로로는 DB 조회가 필요한 엔드포인트는 개별적으로 500 처리해야 함.
        return {"id": user_id, "kakao_id": claims.get("kid", "")}

    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "사용자를 찾을 수 없습니다")
        return {
            "id": user.id,
            "kakao_id": user.kakao_id or "",
            "email": user.email or "",
            "name": user.name or "",
            "tier": user.tier or "standard",
        }
    finally:
        db.close()


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Best-effort JWT 검증. 토큰 없거나 무효해도 401 없이 None 반환.

    공유 링크 등 익명 접근이 허용되는 엔드포인트에서 사용. 라우트는 반환값이
    None인지 여부로 익명/본인을 분기하고, 본인 전용 데이터를 가드해야 함.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_jwt(token)
    if not claims:
        return None

    user_id = claims.get("sub")
    if not user_id:
        return None

    db = get_db()
    if db is None:
        return {"id": user_id, "kakao_id": claims.get("kid", "")}

    try:
        user = db.query(DBUser).filter(DBUser.id == user_id).first()
        if not user:
            return None
        return {
            "id": user.id,
            "kakao_id": user.kakao_id or "",
            "email": user.email or "",
            "name": user.name or "",
            "tier": user.tier or "standard",
        }
    finally:
        db.close()


def db_session():
    """FastAPI dependency that yields a DB session and closes it on teardown.

    Use with ``db: Session = Depends(db_session)``. Returns None if DB is
    unavailable; callers must handle that case explicitly.
    """
    db = get_db()
    try:
        yield db
    finally:
        if db is not None:
            db.close()
