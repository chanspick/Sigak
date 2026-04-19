"""Shared FastAPI dependencies (MVP v1.1).

`get_current_user` is the canonical JWT-based auth dependency. Apply it to
every route except: /health, /auth/kakao/*, /payments/webhook (brief 4.4).

`get_current_user_mock` is the TEMPORARY stand-in used until JWT is wired
through /auth/kakao/token. Remove once phase B completes.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

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


# ─────────────────────────────────────────────
#  TEMPORARY: mock auth (remove once JWT is wired)
# ─────────────────────────────────────────────

def get_current_user_mock(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
) -> dict:
    """Accept a user id directly via ``X-User-Id`` header.

    SECURITY: this bypasses all authentication. Use ONLY for local testing
    and CI until the Kakao→JWT flow is wired. The target state is to replace
    every ``Depends(get_current_user_mock)`` with ``Depends(get_current_user)``
    in a single PR when phase B completes.
    """
    if not x_user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-User-Id 헤더가 필요합니다 (mock auth)")

    db = get_db()
    if db is None:
        return {"id": x_user_id, "kakao_id": "", "name": "", "email": ""}
    try:
        user = db.query(DBUser).filter(DBUser.id == x_user_id).first()
        if not user:
            # Mock auth does NOT auto-create users — the kakao flow owns user creation.
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"user_id {x_user_id}를 찾을 수 없습니다 (먼저 /auth/kakao/token로 유저를 만드세요)",
            )
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
