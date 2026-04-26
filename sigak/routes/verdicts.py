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
from deps import db_session, get_current_user, get_optional_user
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
    diagnosis_unlocked: bool = False
    pro_data: Optional[dict] = None
    # 공유 링크 시 타유저에게는 False. 프론트는 이 값으로 kebab/진단 CTA 노출 제어.
    is_owner: bool = True


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


# v2 BM — 진단 해제 (10 토큰, verdict 단위)
class UnlockDiagnosisResponse(BaseModel):
    verdict_id: str
    diagnosis_unlocked: bool
    token_balance: int


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
            "SELECT id, ranked_photo_ids, blur_released, created_at, version, "
            "       preview_content, full_content "
            "FROM verdicts "
            "WHERE user_id = :uid "
            "ORDER BY created_at DESC "
            "LIMIT :lim OFFSET :off"
        ),
        {"uid": user["id"], "lim": limit, "off": offset},
    ).fetchall()

    items: list[VerdictListItem] = []
    for row in rows:
        # version 분기 — v2 verdict 도 같은 테이블에 저장되며 ranked_photo_ids
        # shape 가 다름 (v1: [{filename, ...}], v2: [{r2_key, photo_index, ...}]).
        # 2026-04-26 fix: 피드 그리드 썸네일 누락 (v2 verdict 가 v1 파서 통과 못 함).
        # 2026-04-26 fix2: 본인 보고 — 첫 사진 X, best_fit (가장 잘 맞는 한 장) 으로.
        ranked = row.ranked_photo_ids or []
        version = getattr(row, "version", None) or "v1"
        gold_url: Optional[str] = None
        if version == "v2":
            # v2: ranked_photo_ids 의 r2_key → public URL.
            # best_fit_photo_index (full > preview > 0 우선순위) 의 사진을 thumbnail.
            from routes.verdict_v2 import _photo_urls_from_ranked
            urls = _photo_urls_from_ranked(ranked)

            # full_content > preview_content > None
            best_fit_idx: Optional[int] = None
            for src in (row.full_content, row.preview_content):
                if isinstance(src, dict):
                    candidate = src.get("best_fit_photo_index")
                    if isinstance(candidate, int) and candidate >= 0:
                        best_fit_idx = candidate
                        break

            if best_fit_idx is not None and best_fit_idx < len(urls):
                gold_url = urls[best_fit_idx]
            else:
                gold_url = urls[0] if urls else None
        else:
            # v1 기존 로직
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
        coords = compute_coordinates(features, gender=(user_row.gender or "female"))
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
    # 9. Gold reading — placeholder for founder (insert 전에 생성해서 영속화)
    gold_reading = generate_gold_reading(
        winner_photo_coords=winner["coords"],
        chugumi_target=target_coords,
        reference_base=(interview_interp or {}).get("reference_base"),
    )

    db.execute(
        text(
            "INSERT INTO verdicts "
            "  (id, user_id, candidate_count, winner_photo_id, ranked_photo_ids, "
            "   coordinates_snapshot, reasoning_unlocked, blur_released, gold_reading) "
            "VALUES (:id, :uid, :cc, :wp, CAST(:ranked AS jsonb), "
            "        CAST(:coords AS jsonb), FALSE, FALSE, :reading)"
        ),
        {
            "id": verdict_id,
            "uid": user["id"],
            "cc": len(photo_records),
            "wp": winner["photo_id"],
            "ranked": json.dumps(ranked_for_storage, ensure_ascii=False),
            "coords": json.dumps(coords_snapshot, ensure_ascii=False),
            "reading": gold_reading or "",
        },
    )
    db.commit()

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
    user: Optional[dict] = Depends(get_optional_user),
    db=Depends(db_session),
):
    """verdict 재조회. 인증은 선택.

    - 본인(토큰의 sub == verdict.user_id): 전체 필드 반환. kebab/진단 CTA 노출용.
    - 타유저/비로그인: GOLD tier + gold_reading 만 공개. silver/bronze,
      pro_data, diagnosis_unlocked 는 감춤. is_owner=False로 구분.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT id, user_id, candidate_count, ranked_photo_ids, "
            "       coordinates_snapshot, blur_released, diagnosis_unlocked, "
            "       reasoning_data, gold_reading "
            "FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()
    if row is None:
        raise HTTPException(404, "verdict not found")

    is_owner = bool(user and row.user_id == user["id"])
    ranked = row.ranked_photo_ids or []
    tiers = verdict_util.assign_tiers(ranked)
    reading = row.gold_reading or ""

    if not is_owner:
        # 공유 공개 스코프: GOLD만. silver/bronze/pro_data/진단 상태 모두 비공개.
        return VerdictResponse(
            verdict_id=row.id,
            candidate_count=row.candidate_count,
            tiers={
                "gold": [
                    _photo_to_response(p, row.user_id, include_url=True)
                    for p in tiers["gold"]
                ],
                "silver": [],
                "bronze": [],
            },
            gold_reading=reading,
            blur_released=False,
            diagnosis_unlocked=False,
            pro_data=None,
            is_owner=False,
        )

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
        gold_reading=reading,
        blur_released=bool(row.blur_released),
        diagnosis_unlocked=bool(row.diagnosis_unlocked),
        pro_data=row.reasoning_data if row.blur_released else None,
        is_owner=True,
    )


# ─────────────────────────────────────────────
#  POST /api/v1/verdicts/{verdict_id}/unlock-diagnosis  (v2 BM, 10 토큰)
# ─────────────────────────────────────────────

@router.post("/{verdict_id}/unlock-diagnosis", response_model=UnlockDiagnosisResponse)
def unlock_diagnosis(
    verdict_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """10 토큰 차감 + verdicts.diagnosis_unlocked=TRUE.

    v2 BM에서 verdict 단위 해제. blur_released(50토큰)와 독립.
    idempotency_key=``diagnosis:{verdict_id}`` — 재시도 시 추가 차감 없음.

    상태 전환:
      - 이미 diagnosis_unlocked=TRUE면 409 already_unlocked (중복 호출 방지)
      - 잔액 < 10 이면 402 insufficient_balance
        (프론트가 intent=unlock_diagnosis&verdict_id=X 로 purchase 유도)
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT user_id, diagnosis_unlocked FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()
    if row is None:
        raise HTTPException(404, "verdict not found")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 verdict가 아닙니다")

    if row.diagnosis_unlocked:
        raise HTTPException(409, "already_unlocked")

    current_balance = tokens_service.get_balance(db, user["id"])
    if current_balance < tokens_service.COST_DIAGNOSIS_UNLOCK:
        raise HTTPException(
            402,
            f"토큰이 부족합니다. {tokens_service.COST_DIAGNOSIS_UNLOCK}토큰 필요, 현재 {current_balance}",
        )

    idempotency_key = f"diagnosis:{verdict_id}"
    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-tokens_service.COST_DIAGNOSIS_UNLOCK,
            kind=tokens_service.KIND_CONSUME_DIAGNOSIS,
            idempotency_key=idempotency_key,
            reference_id=verdict_id,
            reference_type="verdict",
        )
    except IntegrityError:
        db.rollback()
        balance_after = tokens_service.get_balance(db, user["id"])

    db.execute(
        text(
            "UPDATE verdicts SET diagnosis_unlocked = TRUE "
            "WHERE id = :id AND diagnosis_unlocked = FALSE"
        ),
        {"id": verdict_id},
    )
    db.commit()

    return UnlockDiagnosisResponse(
        verdict_id=verdict_id,
        diagnosis_unlocked=True,
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  DELETE /api/v1/verdicts/{verdict_id}
# ─────────────────────────────────────────────

@router.delete("/{verdict_id}")
def delete_verdict(
    verdict_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
):
    """본인 verdict 삭제.

    업로드 원본 + tier(GOLD/SILVER/BRONZE 뷰의 근거) 이미지가 모두 같은 파일이므로
    ranked_photo_ids[].filename 전체를 uploads/{user_id}/ 에서 제거.

    token_transactions.reference_id 는 verdict_id를 가리키지만 FK 강제는
    없으므로 verdicts row만 삭제해도 DB integrity OK. 감사 이력 보존용으로
    transactions는 남겨둠. diagnosis_unlocked=true였어도 환불 없음.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text("SELECT user_id, ranked_photo_ids FROM verdicts WHERE id = :id"),
        {"id": verdict_id},
    ).first()
    if not row:
        raise HTTPException(404, "verdict not found")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 verdict가 아닙니다")

    ranked = row.ranked_photo_ids or []
    user_dir = DATA_DIR / user["id"]
    for item in ranked:
        filename = item.get("filename") if isinstance(item, dict) else None
        if not filename:
            continue
        try:
            target = (user_dir / filename).resolve()
            if target.parent == user_dir.resolve() and target.is_file():
                target.unlink()
        except OSError as e:
            logger.warning(
                "[verdict %s] file unlink failed %s: %s", verdict_id, filename, e
            )

    db.execute(
        text("DELETE FROM verdicts WHERE id = :id"),
        {"id": verdict_id},
    )
    db.commit()
    return {"deleted": True, "verdict_id": verdict_id}


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
