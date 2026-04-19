"""JWT-related auth routes (MVP v1.1 phase B).

Existing Kakao OAuth flow lives in main.py — we don't move it to avoid
touching legacy endpoints. This file adds:

  - POST /api/v1/auth/dev-issue-jwt   test-only JWT minting, ADMIN_KEY gated
  - GET  /api/v1/auth/me              JWT-authenticated self lookup

The legacy ``GET /auth/me?user_id=X`` in main.py stays for backward compat
during the frontend migration window. Refactor backlog #3 tracks removal.
"""
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from db import User as DBUser
from deps import db_session, get_current_user
from services.auth import issue_jwt


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class DevIssueJwtRequest(BaseModel):
    user_id: str


class DevIssueJwtResponse(BaseModel):
    jwt: str
    user_id: str
    kakao_id: str


@router.post("/dev-issue-jwt", response_model=DevIssueJwtResponse)
def dev_issue_jwt(
    body: DevIssueJwtRequest,
    x_admin_key: str = Header(None, alias="X-Admin-Key"),
    db=Depends(db_session),
):
    """Mint a JWT for an existing user id without going through Kakao OAuth.

    For local/curl testing only — guarded by ``ADMIN_KEY`` env var. The user
    must already exist (we do not auto-create to keep Kakao as the single
    source of user identity).

    This endpoint is safe to keep in prod because the admin key never ships
    to clients. If a key rotation is needed, update ``ADMIN_KEY`` in Railway.
    """
    expected = os.getenv("ADMIN_KEY", "")
    if not expected or x_admin_key != expected:
        raise HTTPException(403, "invalid admin key")
    if db is None:
        raise HTTPException(500, "DB unavailable")

    user = db.query(DBUser).filter(DBUser.id == body.user_id).first()
    if not user:
        raise HTTPException(404, f"user_id {body.user_id} not found")

    token = issue_jwt(user.id, user.kakao_id or "")
    return DevIssueJwtResponse(
        jwt=token,
        user_id=user.id,
        kakao_id=user.kakao_id or "",
    )


class MeResponse(BaseModel):
    id: str
    kakao_id: str
    email: str
    name: str
    tier: str


@router.get("/me", response_model=MeResponse)
def get_me(user: dict = Depends(get_current_user)):
    """Return the current user based on the Bearer JWT.

    Note: legacy ``GET /auth/me?user_id=X`` in main.py is a separate path
    (no /api/v1 prefix on that older route? — check main.py) and stays
    untouched for backward compat.
    """
    return MeResponse(
        id=user["id"],
        kakao_id=user.get("kakao_id", ""),
        email=user.get("email", ""),
        name=user.get("name", ""),
        tier=user.get("tier", "standard"),
    )
