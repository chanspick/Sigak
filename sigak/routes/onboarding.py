"""Onboarding endpoints (MVP v1.2).

Three endpoints backed by ``users.onboarding_data`` (JSONB) and
``users.onboarding_completed`` (BOOL):

  POST /api/v1/onboarding/save-step   shallow-merge fields, auto-flip completed on step 4
  GET  /api/v1/onboarding/state       current progress + next_step hint
  POST /api/v1/onboarding/reset       unset completed; preserve onboarding_data for pre-fill

Data shape is flat — keys match Pydantic ``SubmitRequest`` in main.py — so the
existing pipeline entrypoint ``_run_analysis_pipeline`` can read onboarding_data
directly as the interview payload without transformation.
"""
import json
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from deps import db_session, get_current_user


router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


# ─────────────────────────────────────────────
#  Required fields per step (spec: Q-V2-3)
# ─────────────────────────────────────────────

# ``reference_celebs`` and ``current_concerns`` are optional — excluded here.
REQUIRED_FIELDS_BY_STEP: dict[int, list[str]] = {
    1: ["height", "weight", "shoulder_width", "neck_length"],
    2: ["face_concerns"],
    3: ["style_image_keywords", "desired_image", "makeup_level"],
    4: ["self_perception"],
}

ALL_REQUIRED_FIELDS: list[str] = [
    f for fields in REQUIRED_FIELDS_BY_STEP.values() for f in fields
]


# ─────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────

class SaveStepRequest(BaseModel):
    step: Literal[1, 2, 3, 4]
    fields: Dict[str, Any] = Field(default_factory=dict)


class SaveStepResponse(BaseModel):
    onboarding_data: Dict[str, Any]
    completed: bool


class StateResponse(BaseModel):
    onboarding_completed: bool
    onboarding_data: Optional[Dict[str, Any]]
    next_step: Optional[int]


class ResetResponse(BaseModel):
    onboarding_completed: bool


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _compute_next_step(data: Dict[str, Any], completed: bool) -> Optional[int]:
    """Returns first step whose required field is missing. None if completed."""
    if completed:
        return None
    for step in (1, 2, 3, 4):
        for field in REQUIRED_FIELDS_BY_STEP[step]:
            if not data.get(field):
                return step
    # All required present but completion not flipped — nudge to step 4
    # so the next save-step call triggers the auto-completion check.
    return 4


def _load_user_onboarding(db, user_id: str) -> tuple[Dict[str, Any], bool]:
    row = db.execute(
        text(
            "SELECT onboarding_data, onboarding_completed "
            "FROM users WHERE id = :uid"
        ),
        {"uid": user_id},
    ).first()
    if row is None:
        raise HTTPException(404, "user not found")
    data = row.onboarding_data or {}
    return data, bool(row.onboarding_completed)


# ─────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────

@router.post("/save-step", response_model=SaveStepResponse)
def save_step(
    body: SaveStepRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Shallow-merge incoming ``fields`` into ``onboarding_data``.

    Step ordering is NOT enforced server-side — frontend routing decides what
    screen to show. We accept any step's fields and just merge them.

    Auto-completion fires only when ``step=4`` is saved AND all 9 required
    fields (REQUIRED_FIELDS_BY_STEP flattened) are present in the merged
    result. Once flipped, stays True until ``/reset`` is called.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 1. Shallow-merge via PG JSONB concat. COALESCE handles NULL start state.
    db.execute(
        text(
            "UPDATE users "
            "SET onboarding_data = COALESCE(onboarding_data, '{}'::jsonb) || CAST(:fields AS jsonb) "
            "WHERE id = :uid"
        ),
        {"fields": json.dumps(body.fields), "uid": user["id"]},
    )

    # 2. Re-read merged state.
    merged, already_completed = _load_user_onboarding(db, user["id"])
    completed = already_completed

    # 3. Step 4 auto-complete check.
    if body.step == 4 and not already_completed:
        if all(merged.get(f) for f in ALL_REQUIRED_FIELDS):
            db.execute(
                text("UPDATE users SET onboarding_completed = TRUE WHERE id = :uid"),
                {"uid": user["id"]},
            )
            completed = True

    db.commit()
    return SaveStepResponse(onboarding_data=merged, completed=completed)


@router.get("/state", response_model=StateResponse)
def get_state(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Return current progress so frontend can route user to the right step."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    data, completed = _load_user_onboarding(db, user["id"])
    return StateResponse(
        onboarding_completed=completed,
        onboarding_data=data if data else None,
        next_step=_compute_next_step(data, completed),
    )


@router.post("/reset", response_model=ResetResponse)
def reset(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Flip ``onboarding_completed`` back to False. Keep ``onboarding_data``
    intact so the user can edit rather than re-enter from scratch.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 시각 재설정 시 리포트도 다시 잠기게 (release는 idempotent라 재해제 시 추가 차감 없음)
    db.execute(
        text(
            "UPDATE users SET "
            "  onboarding_completed = FALSE, "
            "  sigak_report_released = FALSE "
            "WHERE id = :uid"
        ),
        {"uid": user["id"]},
    )
    db.commit()
    return ResetResponse(onboarding_completed=False)
