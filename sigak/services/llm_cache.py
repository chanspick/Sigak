"""LLM #1 / #2 caching wrappers (MVP v1.2 Phase C).

Non-negotiable: existing ``pipeline.llm.interpret_face_structure`` and
``pipeline.llm.interpret_interview`` functions are untouched. These wrappers
compute a content hash, check the cache, and only call through on miss.

Invalidation rules:
  - Face interpretation: keyed by user_id. Invalidates when ``features_hash``
    changes (i.e. a new verdict produces a differently-shaped FaceFeatures
    dict for the winner). Stored in ``face_interpretations`` table.
  - Interview interpretation: keyed by user_id inline on ``users``.
    Invalidates when the user re-edits onboarding_data (save-step or reset
    followed by new saves). ``interview_interpretation_hash`` guards this.

Both wrappers commit their own writes so callers don't have to care.
"""
import hashlib
import json
import logging
from typing import Optional

from sqlalchemy import text

from db import User as DBUser
from pipeline.llm import interpret_face_structure, interpret_interview


logger = logging.getLogger(__name__)


def _stable_hash(obj: dict) -> str:
    """SHA-256 of JSON with sorted keys. ``default=str`` handles datetime/etc
    so we don't crash on unexpected types."""
    raw = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────
#  LLM #1 — face structure
# ─────────────────────────────────────────────

def get_or_compute_face_interpretation(db, user_id: str, face_features: dict) -> dict:
    """Return cached interpretation if ``features_hash`` matches, else call
    ``interpret_face_structure`` and upsert the cache row.
    """
    features_hash = _stable_hash(face_features)

    cached = db.execute(
        text(
            "SELECT features_hash, interpretation FROM face_interpretations "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    ).first()
    if cached and cached.features_hash == features_hash:
        logger.info("[LLM#1 cache HIT] user=%s", user_id)
        return cached.interpretation

    logger.info("[LLM#1 cache MISS] user=%s", user_id)
    interpretation = interpret_face_structure(face_features)

    db.execute(
        text(
            "INSERT INTO face_interpretations (user_id, features_hash, interpretation, updated_at) "
            "VALUES (:uid, :fh, CAST(:interp AS jsonb), NOW()) "
            "ON CONFLICT (user_id) DO UPDATE "
            "  SET features_hash = EXCLUDED.features_hash, "
            "      interpretation = EXCLUDED.interpretation, "
            "      updated_at = NOW()"
        ),
        {
            "uid": user_id,
            "fh": features_hash,
            "interp": json.dumps(interpretation, ensure_ascii=False),
        },
    )
    db.commit()
    return interpretation


# ─────────────────────────────────────────────
#  LLM #2 — interview interpretation
# ─────────────────────────────────────────────

def get_or_compute_interview_interpretation(
    db, user: DBUser, gender: str = "female"
) -> Optional[dict]:
    """Return cached interview interpretation if the hash of the current
    ``onboarding_data`` matches what we stored. Else call LLM and upsert
    both columns on the user row.

    Returns None if the user has no onboarding_data yet (nothing to interpret).
    The caller should gate verdict creation on ``onboarding_completed`` before
    getting here, so None should be rare in practice.
    """
    if not user.onboarding_data:
        return None

    current_hash = _stable_hash(user.onboarding_data)
    if (
        user.interview_interpretation
        and user.interview_interpretation_hash == current_hash
    ):
        logger.info("[LLM#2 cache HIT] user=%s", user.id)
        return user.interview_interpretation

    logger.info("[LLM#2 cache MISS] user=%s", user.id)
    interpretation = interpret_interview(user.onboarding_data, gender=gender)

    # Raw SQL for the UPDATE — the ORM-bound user object on this session
    # may be stale after we flush; we read from the returned interpretation
    # rather than trusting ORM state.
    db.execute(
        text(
            "UPDATE users "
            "SET interview_interpretation = CAST(:interp AS jsonb), "
            "    interview_interpretation_hash = :h "
            "WHERE id = :uid"
        ),
        {
            "interp": json.dumps(interpretation, ensure_ascii=False),
            "h": current_hash,
            "uid": user.id,
        },
    )
    db.commit()
    return interpretation
