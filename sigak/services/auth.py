"""JWT issuance and verification for SIGAK MVP v1.1.

Implements brief section 4.3 claim structure:
    {sub: user_id, kid: kakao_id, iat, exp, ver: 1}

HS256 with JWT_SECRET env var. 7-day expiry, no refresh. Rotating the secret
invalidates all active sessions — acceptable for MVP.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError

from config import get_settings


JWT_ALGORITHM = "HS256"
JWT_CLAIM_VERSION = 1


def issue_jwt(user_id: str, kakao_id: str = "") -> str:
    """Sign a new JWT for the given user.

    Raises RuntimeError if JWT_SECRET is not configured — callers should treat
    that as a 500-class condition, not a user error.
    """
    settings = get_settings()
    if not settings.jwt_secret:
        raise RuntimeError("JWT_SECRET not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "kid": kakao_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.jwt_expiry_days)).timestamp()),
        "ver": JWT_CLAIM_VERSION,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def verify_jwt(token: str) -> Optional[dict]:
    """Return decoded claims if valid, None otherwise.

    Do not leak the failure reason to clients — always surface as generic 401.
    Version mismatch (claim structure change) is treated as invalid so older
    tokens cannot be reused after a structural upgrade.
    """
    settings = get_settings()
    if not settings.jwt_secret or not token:
        return None

    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None

    if claims.get("ver") != JWT_CLAIM_VERSION:
        return None

    return claims
