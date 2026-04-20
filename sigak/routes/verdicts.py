"""Verdict endpoints (MVP v1.2 Phase C).

Flow:
  POST /api/v1/verdicts                        create (photos + onboarding → tiers + gold_reading)
  POST /api/v1/verdicts/{id}/release-blur      unlock SILVER/BRONZE + pro_data for 50 tokens
  GET  /api/v1/verdicts/{id}                   re-fetch verdict (respects current blur state)

Behaviour matches brief section 3 of Phase C spec:
  - blur_released gates url exposure for silver/bronze tiers
  - LLM #1 (face_structure) and LLM #2 (interview) go through the cache
    wrappers in services.llm_cache
  - LLM #3 short (gold_reading) is a placeholder in services.gold_reading
  - LLM #3 full (generate_report) is NOT called in Phase C — pro_data is
    populated from cached interpretations + deterministic axis deltas.
    Founder will plug in the real call when the full prompt is ready.
"""
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import User as DBUser
from deps import db_session, get_current_user
from pipeline.coordinate import compute_coordinates
from pipeline.face import analyze_face
from services import tokens as tokens_service
from services import verdicts as verdict_util
from services.gold_reading import generate_gold_reading
from services.llm_cache import (
    get_or_compute_face_interpretation,
    get_or_compute_interview_interpretation,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/verdicts", tags=["verdicts"])


# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────

DATA_DIR = Path(os.getenv("SIGAK_DATA_DIR", Path(os.path.dirname(os.path.dirname(__file__))) / "uploads"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MIN_PHOTOS = 2
MAX_PHOTOS = 10


# ─────────────────────────────────────────────
#  Response shapes
# ─────────────────────────────────────────────

class TierPhoto(BaseModel):
    photo_id: str
    score: float
    url: Optional[str] = None


class VerdictResponse(BaseModel):
    verdict_id: str
    candidate_count: int
    tiers: dict[str, list[TierPhoto]]
    gold_reading: str
    blur_released: bool
    pro_data: Optional[dict] = None


class VerdictListItem(BaseModel):
    verdict_id: str
    gold_photo_url: Optional[str] = None
    blur_released: bool
    created_at: str  # ISO


class VerdictListResponse(BaseModel):
    verdicts: list[VerdictListItem]
    total: int
    has_more: bool


class ReleaseBlurRequest(BaseModel):
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Reuse-safe key. Omit → server defaults to 'blur:{verdict_id}'.",
    )


class ReleaseBlurResponse(BaseModel):
    verdict_id: str
    blur_released: bool
    pro_data: dict
    balance_after: int


# ─────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────

def _photo_url(user_id: str, filename: str) -> str:
    """Serving is via existing main.py::/api/v1/uploads/{user_id}/{filename}.
    True S3 signed URLs are a refactor-backlog item — for MVP, local disk +
    this path is 'semi-protected' (filename is random enough) and good enough.
    """
    return f"/api/v1/uploads/{user_id}/{filename}"


def _photo_to_response(photo: dict, user_id: str, include_url: bool) -> TierPhoto:
    return TierPhoto(
        photo_id=photo["photo_id"],
        score=round(photo["score"], 3),
        url=_photo_url(user_id, photo["filename"]) if include_url else None,
    )


def _build_pro_data(verdict_row, user: DBUser, db) -> dict:
    """Compose pro_data from cached interpretations + deterministic axis
    deltas. See module docstring about LLM #3 full — deferred to founder.
    """
    ranked = verdict_row.ranked_photo_ids or []
    coords_snapshot = verdict_row.coordinates_snapshot or {}
    target = coords_snapshot.get("target", {"shape": 0, "volume": 0, "age": 0})
    per_photo_coords = {
        p["photo_id"]: p["coords"]
        for p in coords_snapshot.get("photos", [])
    }

    silver_readings: list[dict] = []
    bronze_readings: list[dict] = []
    for i, p in enumerate(ranked):
        if i == 0:
            continue  # gold is free, already surfaced
        photo_coord = per_photo_coords.get(p["photo_id"], {})
        reading = {
            "photo_id": p["photo_id"],
            "axis_delta": verdict_util.axis_delta(photo_coord, target),
            # TODO(founder): replace with per-photo LLM reason. Placeholder below.
            "reason": "추구미 좌표와의 거리가 있어 후순위로 분류되었어요",
        }
        if i < 4:
            silver_readings.append(reading)
        elif i < 9:
            bronze_readings.append(reading)

    # Cached interview interpretation — free, already computed at create time
    interview_interp = get_or_compute_interview_interpretation(
        db, user, gender=(user.gender or "female")
    ) or {}

    full_analysis = {
        "interpretation": interview_interp.get("interpretation", ""),
        "reference_base": interview_interp.get("reference_base", ""),
        "chugumi_target": target,
        # TODO(founder): fill via generate_report(action_spec, user_ctx) LLM #3 full
        "action_spec": None,
        # TODO(founder): derive from user's prior verdicts (last 3 trend)
        "trajectory_signal": None,
    }

    return {
        "silver_readings": silver_readings,
        "bronze_readings": bronze_readings,
        "full_analysis": full_analysis,
    }


# ─────────────────────────────────────────────
#  GET /api/v1/verdicts  (list, user-scoped)
# ─────────────────────────────────────────────

@router.get("", response_model=VerdictListResponse)
def list_verdicts(
    limit: int = 30,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """유저 본인의 verdict 리스트. 피드 그리드용.

    created_at DESC 정렬. ranked_photo_ids[0]이 gold — 거기서 filename 추출해
    URL 재생성 (S3 signed URL 전환 시 매 호출마다 refresh되도록 설계).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # Clamp limit/offset
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    # Total count
    total_row = db.execute(
        text("SELECT COUNT(*) AS c FROM verdicts WHERE user_id = :uid"),
        {"uid": user["id"]},
    ).first()
    total = int(total_row.c) if total_row else 0

    rows = db.execute(
        text(
            "SELECT id, ranked_photo_ids, blur_released, created_at "
            "FROM verdicts "
            "WHERE user_id = :uid "
            "ORDER BY created_at DESC "
            "LIMIT :lim OFFSET :off"
        ),
        {"uid": user["id"], "lim": limit, "off": offset},
    ).fetchall()

    items: list[VerdictListItem] = []
    for row in rows:
        ranked = row.ranked_photo_ids or []
        gold_filename = (
            ranked[0].get("filename") if isinstance(ranked, list) and ranked else None
        )
        gold_url = _photo_url(user["id"], gold_filename) if gold_filename else None
        created_at_iso = (
            row.created_at.isoformat() if row.created_at else ""
        )
        items.append(
            VerdictListItem(
                verdict_id=row.id,
                gold_photo_url=gold_url,
                blur_released=bool(row.blur_released),
                created_at=created_at_iso,
            )
        )

    has_more = (offset + len(items)) < total
    return VerdictListResponse(verdicts=items, total=total, has_more=has_more)


# ─────────────────────────────────────────────
#  POST /api/v1/verdicts
# ─────────────────────────────────────────────

@router.post("", response_model=VerdictResponse)
async def create_verdict(
    files: list[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Create a new verdict from N photos against the user's current chugumi
    (onboarding_data → interview_interpretation).

    Onboarding is required — returns 409 if the user hasn't finished step 4.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 1. Onboarding gate
    user_row = db.query(DBUser).filter(DBUser.id == user["id"]).first()
    if user_row is None:
        raise HTTPException(404, "user not found")
    if not user_row.onboarding_completed:
        raise HTTPException(409, "onboarding을 먼저 완료해주세요")
    if not user_row.onboarding_data:
        raise HTTPException(409, "onboarding 데이터가 없습니다")

    # 2. Photo count validation
    if not (MIN_PHOTOS <= len(files) <= MAX_PHOTOS):
        raise HTTPException(400, f"사진은 {MIN_PHOTOS}~{MAX_PHOTOS}장까지 올릴 수 있어요")

    verdict_id = f"vrd_{uuid.uuid4().hex[:12]}"
    user_dir = DATA_DIR / user["id"]
    user_dir.mkdir(parents=True, exist_ok=True)

    # 3. Save photos + per-photo face analysis
    photo_records: list[dict] = []
    for i, f in enumerate(files):
        contents = await f.read()
        ext = Path(f.filename or "photo.jpg").suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png"}:
            ext = ".jpg"
        filename = f"{verdict_id}_{i}{ext}"
        save_path = user_dir / filename
        with open(save_path, "wb") as fp:
            fp.write(contents)

        face_result = analyze_face(contents)
        if face_result is None:
            logger.info("[verdict %s] face not detected on photo %d", verdict_id, i)
            continue

        features = face_result.to_dict()
        coords = compute_coordinates(features)
        photo_records.append({
            "photo_id": f"p_{uuid.uuid4().hex[:8]}",
            "filename": filename,
            "features": features,
            "coords": coords,
        })

    if len(photo_records) < MIN_PHOTOS:
        raise HTTPException(
            400,
            "얼굴 인식에 실패한 사진이 많아요. 밝은 곳에서 정면으로 다시 찍어주세요",
        )

    # 4. Interview interpretation (LLM #2, cached)
    interview_interp = get_or_compute_interview_interpretation(
        db, user_row, gender=(user_row.gender or "female")
    )
    target_coords = (interview_interp or {}).get(
        "coordinates", {"shape": 0.0, "volume": 0.0, "age": 0.0}
    )

    # 5. Score + rank
    for p in photo_records:
        p["score"] = verdict_util.score_photo(p["coords"], target_coords)
    photo_records.sort(key=lambda p: p["score"], reverse=True)

    # 6. Winner face interpretation (LLM #1, cached — feeds gold_reading context)
    winner = photo_records[0]
    try:
        get_or_compute_face_interpretation(db, user["id"], winner["features"])
    except Exception as e:
        # Cache write failure should not block verdict return; log and continue.
        logger.warning("[verdict %s] face interp cache error: %s", verdict_id, e)

    # 7. Tier assignment
    tiers = verdict_util.assign_tiers(photo_records)

    # 8. Persist verdict row
    ranked_for_storage = [
        {"photo_id": p["photo_id"], "score": p["score"], "filename": p["filename"]}
        for p in photo_records
    ]
    coords_snapshot = {
        "target": target_coords,
        "photos": [
            {"photo_id": p["photo_id"], "coords": p["coords"]}
            for p in photo_records
        ],
    }
    db.execute(
        text(
            "INSERT INTO verdicts "
            "  (id, user_id, candidate_count, winner_photo_id, ranked_photo_ids, "
            "   coordinates_snapshot, reasoning_unlocked, blur_released) "
            "VALUES (:id, :uid, :cc, :wp, CAST(:ranked AS jsonb), "
            "        CAST(:coords AS jsonb), FALSE, FALSE)"
        ),
        {
            "id": verdict_id,
            "uid": user["id"],
            "cc": len(photo_records),
            "wp": winner["photo_id"],
            "ranked": json.dumps(ranked_for_storage, ensure_ascii=False),
            "coords": json.dumps(coords_snapshot, ensure_ascii=False),
        },
    )
    db.commit()

    # 9. Gold reading — placeholder for founder
    gold_reading = generate_gold_reading(
        winner_photo_coords=winner["coords"],
        chugumi_target=target_coords,
        reference_base=(interview_interp or {}).get("reference_base"),
    )

    # 10. Response
    return VerdictResponse(
        verdict_id=verdict_id,
        candidate_count=len(photo_records),
        tiers={
            "gold": [_photo_to_response(p, user["id"], include_url=True) for p in tiers["gold"]],
            "silver": [_photo_to_response(p, user["id"], include_url=False) for p in tiers["silver"]],
            "bronze": [_photo_to_response(p, user["id"], include_url=False) for p in tiers["bronze"]],
        },
        gold_reading=gold_reading,
        blur_released=False,
        pro_data=None,
    )


# ─────────────────────────────────────────────
#  GET /api/v1/verdicts/{verdict_id}
# ─────────────────────────────────────────────

@router.get("/{verdict_id}", response_model=VerdictResponse)
def get_verdict(
    verdict_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT id, user_id, candidate_count, ranked_photo_ids, "
            "       coordinates_snapshot, blur_released, reasoning_data "
            "FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()
    if row is None:
        raise HTTPException(404, "verdict not found")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 verdict가 아닙니다")

    ranked = row.ranked_photo_ids or []
    tiers = verdict_util.assign_tiers(ranked)

    return VerdictResponse(
        verdict_id=row.id,
        candidate_count=row.candidate_count,
        tiers={
            "gold": [_photo_to_response(p, user["id"], include_url=True) for p in tiers["gold"]],
            "silver": [
                _photo_to_response(p, user["id"], include_url=row.blur_released)
                for p in tiers["silver"]
            ],
            "bronze": [
                _photo_to_response(p, user["id"], include_url=row.blur_released)
                for p in tiers["bronze"]
            ],
        },
        # GET doesn't re-run gold_reading — it's ephemeral per create.
        # TODO: persist gold_reading on create so re-fetch keeps it.
        gold_reading="",
        blur_released=bool(row.blur_released),
        pro_data=row.reasoning_data if row.blur_released else None,
    )


# ─────────────────────────────────────────────
#  DELETE /api/v1/verdicts/{verdict_id}
# ─────────────────────────────────────────────

@router.delete("/{verdict_id}", status_code=204)
def delete_verdict(
    verdict_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """본인 verdict 삭제. 업로드 파일(uploads/)은 orphan으로 남음 —
    cleanup job은 refactor backlog.

    token_transactions.reference_id 는 verdict_id를 가리키지만 FK 강제는
    없으므로 verdicts row만 삭제해도 DB integrity OK. 감사 이력 보존용으로
    transactions는 남겨둠.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text("SELECT user_id FROM verdicts WHERE id = :id"),
        {"id": verdict_id},
    ).first()
    if not row:
        raise HTTPException(404, "verdict not found")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 verdict가 아닙니다")

    db.execute(
        text("DELETE FROM verdicts WHERE id = :id"),
        {"id": verdict_id},
    )
    db.commit()
    return None


# ─────────────────────────────────────────────
#  POST /api/v1/verdicts/{verdict_id}/release-blur
# ─────────────────────────────────────────────

@router.post("/{verdict_id}/release-blur", response_model=ReleaseBlurResponse)
def release_blur(
    verdict_id: str,
    body: ReleaseBlurRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """Burn 50 tokens to unlock SILVER/BRONZE URLs + pro_data on this verdict.

    Idempotent via ``token_transactions.idempotency_key`` UNIQUE constraint.
    Retried calls return the existing state without double-charging.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 1. Load verdict, verify ownership
    row = db.execute(
        text(
            "SELECT id, user_id, blur_released, reasoning_data "
            "FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()
    if row is None:
        raise HTTPException(404, "verdict not found")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 verdict가 아닙니다")

    # 2. Short-circuit if already released — return stored pro_data + current balance
    if row.blur_released:
        return ReleaseBlurResponse(
            verdict_id=row.id,
            blur_released=True,
            pro_data=row.reasoning_data or {},
            balance_after=tokens_service.get_balance(db, user["id"]),
        )

    # 3. Balance pre-check (CHECK constraint would fire on debit, but error
    #    message quality is better with explicit 402)
    current_balance = tokens_service.get_balance(db, user["id"])
    if current_balance < tokens_service.COST_BLUR_RELEASE:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {tokens_service.COST_BLUR_RELEASE}토큰 필요, 현재 {current_balance}",
        )

    # 4. Debit tokens (idempotent)
    idempotency_key = body.idempotency_key or f"blur:{verdict_id}"
    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-tokens_service.COST_BLUR_RELEASE,
            kind=tokens_service.KIND_CONSUME_BLUR_RELEASE,
            idempotency_key=idempotency_key,
            reference_id=verdict_id,
            reference_type="verdict",
        )
    except IntegrityError:
        # Race: concurrent release-blur won. Re-read.
        db.rollback()
        balance_after = tokens_service.get_balance(db, user["id"])

    # 5. Re-load verdict row with full coords so build_pro_data works
    full_row = db.execute(
        text(
            "SELECT id, user_id, ranked_photo_ids, coordinates_snapshot "
            "FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()

    user_row = db.query(DBUser).filter(DBUser.id == user["id"]).first()
    pro_data = _build_pro_data(full_row, user_row, db)

    # 6. Flip blur_released + persist pro_data
    db.execute(
        text(
            "UPDATE verdicts SET "
            "  blur_released = TRUE, "
            "  reasoning_unlocked = TRUE, "
            "  reasoning_unlocked_at = NOW(), "
            "  reasoning_data = CAST(:pd AS jsonb) "
            "WHERE id = :id AND blur_released = FALSE"
        ),
        {"pd": json.dumps(pro_data, ensure_ascii=False), "id": verdict_id},
    )
    db.commit()

    return ReleaseBlurResponse(
        verdict_id=verdict_id,
        blur_released=True,
        pro_data=pro_data,
        balance_after=balance_after,
    )
