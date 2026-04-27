"""JWT-related auth routes (MVP v1.1 phase B + v2.0 consent).

Existing Kakao OAuth flow lives in main.py — we don't move it to avoid
touching legacy endpoints. This file provides:

  - POST /api/v1/auth/dev-issue-jwt   test-only JWT minting, ADMIN_KEY gated
  - GET  /api/v1/auth/me              JWT-authenticated self lookup (3-stage gate flags)
  - POST /api/v1/auth/consent         v2.0 약관 동의 저장 (온보딩 welcome에서 호출)

2026-04-23: Toss PG 심사 통과 후 test-login / email-login 엔드포인트 완전 제거.
  Railway env (TEST_LOGIN_ENABLED 등) 도 대시보드에서 정리 필요.

The legacy ``GET /auth/me?user_id=X`` in main.py stays for backward compat
during the frontend migration window. Refactor backlog #3 tracks removal.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

from db import User as DBUser
from deps import db_session, get_current_user
from services.auth import issue_jwt


logger = logging.getLogger(__name__)

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
    # 게이트 플래그 — 프론트 useOnboardingGuard 가 참조.
    #   consent_completed     : v2.0 약관 5+1 동의
    #   essentials_completed  : Step 0 구조화 입력 (gender/birth_date/ig_handle) 저장됨
    #                           판정: users.birth_date IS NOT NULL
    #   onboarding_completed  : Sia 대화 종료 (v2) 또는 4스텝 완료 (v1 legacy)
    consent_completed: bool
    essentials_completed: bool
    onboarding_completed: bool
    # 2026-04-26 fix: /profile/edit 가 현재 핸들 표시용으로 사용.
    # null = 등록된 IG 핸들 없음.
    ig_handle: Optional[str] = None
    # 2026-04-27: 프론트 male v1.1 차단 UI 분기용. 권위 = user_profiles.gender
    # (vault 와 동일 source). NULL/미설정 시 None — UI 가 통과 처리.
    gender: Optional[str] = None


@router.get("/me", response_model=MeResponse)
def get_me(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Return the current user based on the Bearer JWT.

    consent_completed / essentials_completed / onboarding_completed 플래그는
    프론트 useOnboardingGuard 가 3단계 라우팅 분기에 사용.
    DB 미가용 시 False 폴백 (게이트가 안전 방향으로 걸림).
    """
    consent_completed = False
    essentials_completed = False
    onboarding_completed = False
    ig_handle: Optional[str] = None
    gender: Optional[str] = None
    if db is not None:
        # ig_handle 의 신뢰 source 우선순위 (3-tier fallback):
        #   1) user_profiles.ig_handle           — 분석 path (vault) 가 보는 값
        #   2) users.ig_handle                   — v1/legacy primary, dual-write
        #   3) ig_feed_cache.profile_basics.username
        #                                         — Apify 가 실제 fetch 한 핸들.
        #                                            컬럼이 NULL 이어도 cache 가
        #                                            있으면 회복 가능.
        # essentials 와 update-ig 가 (1)+(2) dual-write 하지만 partial write /
        # v1→v2 마이그레이션으로 어긋난 경우, (3) 으로 자가 회복.
        # gender 는 vault 권위 = user_profiles.gender 우선. fallback users.gender.
        row = db.execute(
            text(
                "SELECT u.consent_completed, u.onboarding_completed, u.birth_date, "
                "       u.ig_handle AS u_ig, "
                "       u.gender    AS u_gender, "
                "       p.ig_handle AS p_ig, "
                "       p.gender    AS p_gender, "
                "       (p.ig_feed_cache #>> '{profile_basics,username}') AS cache_ig "
                "FROM users u "
                "LEFT JOIN user_profiles p ON p.user_id = u.id "
                "WHERE u.id = :uid"
            ),
            {"uid": user["id"]},
        ).first()
        if row is not None:
            consent_completed = bool(row.consent_completed)
            onboarding_completed = bool(row.onboarding_completed)
            essentials_completed = row.birth_date is not None
            # 3-tier fallback
            ig_handle = (
                (row.p_ig or None)
                or (row.u_ig or None)
                or (row.cache_ig or None)
            )
            # gender — vault 권위 (p.gender) 우선, fallback users.gender. 비표준은 None.
            _g = (row.p_gender or row.u_gender or "").strip() or None
            gender = _g if _g in ("female", "male") else None
            # 어디서 회복됐는지 진단용 한 줄 — 두 dual-write 컬럼이 어긋났거나
            # cache 로만 회복한 케이스를 식별 (정합 모니터링).
            if ig_handle is None:
                logger.info(
                    "[me] ig_handle absent: user=%s u_ig=%r p_ig=%r cache_ig=%r",
                    user["id"], row.u_ig, row.p_ig, row.cache_ig,
                )
            elif (row.p_ig != row.u_ig) or (row.p_ig is None and ig_handle):
                logger.info(
                    "[me] ig_handle mismatch — recovered via fallback: "
                    "user=%s u_ig=%r p_ig=%r cache_ig=%r resolved=%r",
                    user["id"], row.u_ig, row.p_ig, row.cache_ig, ig_handle,
                )

    return MeResponse(
        id=user["id"],
        kakao_id=user.get("kakao_id", ""),
        email=user.get("email", ""),
        name=user.get("name", ""),
        tier=user.get("tier", "standard"),
        consent_completed=consent_completed,
        essentials_completed=essentials_completed,
        onboarding_completed=onboarding_completed,
        ig_handle=ig_handle,
        gender=gender,
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
#  Toss PG 심사용 테스트 로그인 — 2026-04-23 제거
# ─────────────────────────────────────────────
#  PG 심사 통과 후 test-login / email-login 엔드포인트 + 관련 helper 전체 삭제.
#  Railway env (TEST_LOGIN_ENABLED / TEST_LOGIN_EMAIL / TEST_LOGIN_PASSWORD /
#  TEST_USER_ID) 도 대시보드에서 제거 필요.


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
