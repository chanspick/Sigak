"""JWT-related auth routes (MVP v1.1 phase B + v2.0 consent).

Existing Kakao OAuth flow lives in main.py — we don't move it to avoid
touching legacy endpoints. This file adds:

  - POST /api/v1/auth/dev-issue-jwt   test-only JWT minting, ADMIN_KEY gated
  - GET  /api/v1/auth/me              JWT-authenticated self lookup
  - POST /api/v1/auth/consent         v2.0 약관 동의 저장 (온보딩 welcome에서 호출)
  - POST /api/v1/auth/test-login      Toss PG 심사용 email/password 임시 로그인
                                      (PG 승인 후 TEST_LOGIN_ENABLED=false로 비활성)

The legacy ``GET /auth/me?user_id=X`` in main.py stays for backward compat
during the frontend migration window. Refactor backlog #3 tracks removal.
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from db import User as DBUser
from deps import db_session, get_current_user
from services.auth import issue_jwt


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ─────────────────────────────────────────────
#  Dev JWT (ADMIN_KEY gated, test only)
# ─────────────────────────────────────────────

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

    For local/curl testing only — guarded by ``ADMIN_KEY`` env var.
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


# ─────────────────────────────────────────────
#  /auth/me — self-lookup with gate flags
# ─────────────────────────────────────────────

class MeResponse(BaseModel):
    id: str
    kakao_id: str
    email: str
    name: str
    tier: str
    # v1.2 게이트 플래그 — 프론트 라우팅 가드가 참조.
    consent_completed: bool
    onboarding_completed: bool


@router.get("/me", response_model=MeResponse)
def get_me(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Return the current user based on the Bearer JWT.

    consent_completed / onboarding_completed 플래그는 프론트의 useOnboardingGuard가
    라우팅 분기에 사용. DB 미가용 시 False로 폴백 (게이트가 안전 방향으로 걸림).
    """
    consent_completed = False
    onboarding_completed = False
    if db is not None:
        row = db.execute(
            text(
                "SELECT consent_completed, onboarding_completed "
                "FROM users WHERE id = :uid"
            ),
            {"uid": user["id"]},
        ).first()
        if row is not None:
            consent_completed = bool(row.consent_completed)
            onboarding_completed = bool(row.onboarding_completed)

    return MeResponse(
        id=user["id"],
        kakao_id=user.get("kakao_id", ""),
        email=user.get("email", ""),
        name=user.get("name", ""),
        tier=user.get("tier", "standard"),
        consent_completed=consent_completed,
        onboarding_completed=onboarding_completed,
    )


# ─────────────────────────────────────────────
#  /auth/consent — v2.0 약관 동의 저장
# ─────────────────────────────────────────────

TERMS_VERSION = "2.1"

# 필수 동의 5개. 하나라도 false면 400.
REQUIRED_CONSENTS = (
    "terms",                # 이용약관
    "privacy",              # 개인정보 수집·이용
    "sensitive",            # 민감정보(얼굴·생체)
    "overseas_transfer",    # 국외 이전 (Railway/Vercel/Anthropic)
    "age_confirmed",        # 만 14세 이상
)


class ConsentRequest(BaseModel):
    terms: bool
    privacy: bool
    sensitive: bool
    overseas_transfer: bool
    age_confirmed: bool
    # 선택 동의 — False여도 진행 가능.
    marketing: bool = False


class ConsentResponse(BaseModel):
    consent_completed: bool
    consent_data: dict


# ─────────────────────────────────────────────
#  Toss PG 심사용 테스트 로그인 (임시)
#
#  - 기본 활성화. PG 승인 후 Railway env에 TEST_LOGIN_ENABLED=false 추가하거나
#    이 엔드포인트 블록 전체 삭제.
#  - 테스트 유저는 DB에 자동 upsert되며 consent + onboarding 완료 상태로 세팅되어
#    로그인 직후 /tokens/purchase 결제 플로우 바로 진입 가능.
# ─────────────────────────────────────────────

TEST_LOGIN_ENABLED = os.getenv("TEST_LOGIN_ENABLED", "true").lower() != "false"
TEST_LOGIN_EMAIL = os.getenv("TEST_LOGIN_EMAIL", "test@naver.com")
TEST_LOGIN_PASSWORD = os.getenv("TEST_LOGIN_PASSWORD", "test1234")
TEST_USER_ID = os.getenv("TEST_USER_ID", "test-user-tossdemo")


class TestLoginRequest(BaseModel):
    email: str
    password: str


class TestLoginResponse(BaseModel):
    jwt: str
    user_id: str
    name: str
    email: str


def _test_onboarding_data() -> dict:
    """테스트 유저 온보딩 답변 (완료 상태). Skip onboarding 목적."""
    return {
        "height": "160_165",
        "weight": "50_55",
        "shoulder_width": "medium",
        "neck_length": "medium",
        "face_concerns": "none",
        "style_image_keywords": "modern,natural",
        "desired_image": "깔끔하고 자연스러운 이미지",
        "makeup_level": "basic",
        "self_perception": "평범하다는 말을 자주 듣습니다",
    }


def _test_consent_data() -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": "test-login",
        "terms_version": TERMS_VERSION,
        "terms": True,
        "privacy": True,
        "sensitive": True,
        "overseas_transfer": True,
        "age_confirmed": True,
        "marketing": False,
    }


def _ensure_test_user(db) -> DBUser:
    """테스트 유저 upsert — consent + onboarding 완료 상태 보장."""
    user = db.query(DBUser).filter(DBUser.id == TEST_USER_ID).first()
    if user is None:
        user = DBUser(
            id=TEST_USER_ID,
            email=TEST_LOGIN_EMAIL,
            name="테스터",
            phone="",
            gender="female",
            status="authenticated",
            onboarding_completed=True,
            onboarding_data=_test_onboarding_data(),
            consent_completed=True,
            consent_data=_test_consent_data(),
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        return user

    # 기존 유저 — 필수 상태 유지 (누군가 수동으로 건드린 경우 복구)
    dirty = False
    if not user.consent_completed:
        user.consent_completed = True
        user.consent_data = _test_consent_data()
        dirty = True
    if not user.onboarding_completed:
        user.onboarding_completed = True
        user.onboarding_data = _test_onboarding_data()
        dirty = True
    if user.email != TEST_LOGIN_EMAIL:
        user.email = TEST_LOGIN_EMAIL
        dirty = True
    if dirty:
        db.commit()
    return user


@router.post("/test-login", response_model=TestLoginResponse)
def test_login(
    body: TestLoginRequest,
    db=Depends(db_session),
):
    """Toss PG 심사용 테스트 로그인. email/password 일치 시 JWT 발급.

    보안:
      - TEST_LOGIN_ENABLED=false 시 404 (운영 비활성)
      - 자격증명 불일치 시 401
      - 일치 시 TEST_USER_ID 의 JWT 발급 — 이 유저는 미리 consent + onboarding
        완료 상태로 세팅되어 있어 로그인 즉시 피드 → /tokens/purchase 가능.
    """
    if not TEST_LOGIN_ENABLED:
        raise HTTPException(404, "Not Found")
    if db is None:
        raise HTTPException(500, "DB unavailable")

    if body.email != TEST_LOGIN_EMAIL or body.password != TEST_LOGIN_PASSWORD:
        raise HTTPException(401, "이메일 또는 비밀번호가 일치하지 않습니다")

    user = _ensure_test_user(db)
    token = issue_jwt(user.id, user.kakao_id or "")

    return TestLoginResponse(
        jwt=token,
        user_id=user.id,
        name=user.name or "테스터",
        email=user.email or TEST_LOGIN_EMAIL,
    )


def _client_ip(request: Request) -> str:
    """X-Forwarded-For 우선(Railway/Vercel 프록시 뒤), 없으면 client host."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # "client, proxy1, proxy2" 중 가장 왼쪽이 원래 client.
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


@router.post("/consent", response_model=ConsentResponse)
def save_consent(
    body: ConsentRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """v2.0 약관 동의 저장.

    - 필수 5개 (terms, privacy, sensitive, overseas_transfer, age_confirmed) 중
      하나라도 False면 400.
    - consent_data JSONB에 timestamp(UTC ISO), ip, terms_version 포함해서 저장.
    - consent_completed = True 플립.
    - 이미 completed 상태에서 재호출해도 idempotent (새 동의 데이터로 갱신).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    incoming = body.model_dump()
    missing = [k for k in REQUIRED_CONSENTS if not incoming.get(k)]
    if missing:
        raise HTTPException(
            400,
            f"필수 동의 항목 누락: {', '.join(missing)}",
        )

    consent_data = {
        **incoming,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip_address": _client_ip(request),
        "terms_version": TERMS_VERSION,
    }

    db.execute(
        text(
            "UPDATE users SET "
            "  consent_completed = TRUE, "
            "  consent_data = CAST(:cd AS jsonb) "
            "WHERE id = :uid"
        ),
        {"cd": json.dumps(consent_data, ensure_ascii=False), "uid": user["id"]},
    )
    db.commit()

    return ConsentResponse(
        consent_completed=True,
        consent_data=consent_data,
    )
