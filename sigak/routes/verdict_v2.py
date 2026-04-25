"""Verdict 2.0 endpoints (v2 Priority 1 D5 Phase 2).

SPEC-ONBOARDING-V2 REQ-VERDICT-001~005, REQ-NAMING-003/004.

3 endpoints:
  POST /api/v2/verdict/create
    사진 3-10장 업로드 → Sonnet 4.6 cross-analysis → verdict row 생성 (v2)
    preview_content + full_content JSONB 즉시 저장 (full_unlocked=FALSE)
    응답: verdict_id + preview 부분만

  POST /api/v2/verdict/{verdict_id}/unlock
    atomic transaction:
      1. verdict 검증 (owner, version=v2, not already unlocked)
      2. tokens 10개 차감 (idempotency_key=verdict_id, 중복 결제 방지)
      3. full_unlocked = TRUE 업데이트
    응답: full_content + 새 balance

  GET /api/v2/verdict/{verdict_id}
    preview 는 항상 반환. full_content 는 full_unlocked=TRUE 시에만.
    owner check (403).

v1 공존:
  version='v1' verdict 는 이 라우터에서 404 취급 (기존 /api/v1/verdicts 로).
"""
from __future__ import annotations

import base64
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from deps import db_session, get_current_user
from schemas.verdict_v2 import FullContent, PreviewContent, VerdictV2Result
from services import r2_client, tokens as tokens_service
from services.knowledge_matcher import match_trends_for_user
from services.user_data_vault import load_vault
from services.user_profiles import get_profile
from services.verdict_v2 import (
    PhotoInput,
    VerdictV2Error,
    build_verdict_v2,
    downscale_image,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/verdict", tags=["verdict-v2"])


# ─────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────

MIN_PHOTOS = 3
MAX_PHOTOS = 10
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_BYTES = 10 * 1024 * 1024   # 10 MB per photo


# ─────────────────────────────────────────────
#  Response models
# ─────────────────────────────────────────────

class CreateResponse(BaseModel):
    verdict_id: str
    version: str
    preview: PreviewContent
    full_unlocked: bool
    photo_count: int
    # R2 public URLs — photo_index 0-based 순서. None 항목 = 저장 실패(로컬 fallback 또는 public_url 미설정).
    photo_urls: list[Optional[str]] = []
    # WTP 가설 — best_fit 1 장 풀 노출용 URL. preview.best_fit_photo_index 매핑.
    # None = best_fit 미선정 또는 R2 저장 실패.
    best_fit_photo_url: Optional[str] = None


class UnlockResponse(BaseModel):
    verdict_id: str
    full_unlocked: bool
    full_content: FullContent
    balance: int
    photo_urls: list[Optional[str]] = []
    best_fit_photo_url: Optional[str] = None


class GetResponse(BaseModel):
    verdict_id: str
    version: str
    full_unlocked: bool
    preview: PreviewContent
    full_content: Optional[FullContent] = None
    photo_urls: list[Optional[str]] = []
    best_fit_photo_url: Optional[str] = None


# ─────────────────────────────────────────────
#  POST /create
# ─────────────────────────────────────────────

@router.post("/create", response_model=CreateResponse)
async def create_verdict_v2(
    photos: list[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> CreateResponse:
    """사진 3-10장 업로드 → Sonnet 4.6 분석 → verdict v2 row 생성.

    비용: 0 토큰 (preview 는 무료, full 은 /unlock 에서 10 토큰).
    full_content 는 생성 시점에 미리 만들어 저장하되 full_unlocked=FALSE 로 gating.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 1. Photo count validation
    if len(photos) < MIN_PHOTOS:
        raise HTTPException(
            400, f"사진은 최소 {MIN_PHOTOS}장 필요합니다 (현재 {len(photos)}장).",
        )
    if len(photos) > MAX_PHOTOS:
        raise HTTPException(
            400, f"사진은 최대 {MAX_PHOTOS}장까지 업로드 가능합니다 (현재 {len(photos)}장).",
        )

    # 2. Photo read + content_type validation + 다운스케일 (Sonnet + R2 공통)
    #
    #    Anthropic API 413 방어: 원본 그대로 보내면 10장 × 10MB = 100MB → base64
    #    133MB 로 요청 한계(~32MB) 초과. 1568px / JPEG q=85 로 축소하면 장당
    #    ~300KB, 10장 총 ~3MB 수준으로 안정. R2 저장도 같은 downscaled bytes
    #    사용 (썸네일/카드 용도라 충분한 해상도).
    photo_inputs: list[PhotoInput] = []
    raw_photo_blobs: list[tuple[bytes, str]] = []   # (data, content_type) photo_index 순
    for idx, pf in enumerate(photos):
        ct = pf.content_type or "image/jpeg"
        if ct not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                400,
                f"지원하지 않는 형식 ({ct}). JPEG/PNG/WebP 만 허용.",
            )
        data = await pf.read()
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(
                400,
                f"사진 {idx+1}번 크기 초과 ({len(data)} > {MAX_PHOTO_BYTES} 바이트).",
            )
        if not data:
            raise HTTPException(400, f"사진 {idx+1}번 비어있음.")
        downscaled, ct_out = downscale_image(data)
        b64 = base64.b64encode(downscaled).decode("ascii")
        photo_inputs.append({
            "base64": b64,
            "media_type": ct_out,
            "index": idx,
        })
        raw_photo_blobs.append((downscaled, ct_out))

    # 3. Fetch user_profile (onboarding 완료된 유저만 verdict 가능)
    profile = get_profile(db, user["id"])
    if profile is None:
        raise HTTPException(
            409,
            "user_profile 이 없습니다. Onboarding 먼저 완료해 주십시오.",
        )

    # 4. Knowledge Base 매칭 + UserTasteProfile 로드 (Phase L)
    #    profile.gender 기준으로 현 시즌 매칭. vault 실패 시 조용히 None 진행.
    matched_trends = None
    taste_profile = None
    try:
        vault = load_vault(db, user["id"])
        if vault is not None:
            taste_profile = vault.get_user_taste_profile()
            gender = (vault.basic_info.gender or profile.get("gender") or "female")
            if gender in ("female", "male"):
                matched_trends = match_trends_for_user(
                    taste_profile,
                    gender=gender,   # type: ignore[arg-type]
                    season=None,     # 현 시즌 자동 선정 (env/config 연결은 Phase P)
                    limit=5,
                )
    except Exception:
        logger.exception(
            "verdict v2 KB/vault load failed — degrading to no-trend mode: user_id=%s",
            user["id"],
        )

    # STEP 5i — cross-session history 주입 (Sia / BS / Aspiration 이전분)
    history_context = ""
    try:
        from services.history_injector import build_history_context
        history_context = build_history_context(
            db, user["id"],
            include=[
                "conversations", "best_shot_sessions", "aspiration_analyses",
                "pi_history",
            ],
            max_per_type=1,
        )
    except Exception:
        logger.exception(
            "verdict v2 create: history_injector failed user=%s", user["id"]
        )

    # 5. Sonnet 4.6 cross-analysis
    try:
        result = build_verdict_v2(
            user_profile=profile,
            photos=photo_inputs,
            trend_data=None,       # Phase 1 에선 trend_data (legacy 벡터) 미주입
            matched_trends=matched_trends,   # Phase L 확장
            taste_profile=taste_profile,     # Phase L 확장
            history_context=history_context,
        )
    except VerdictV2Error as e:
        logger.exception("verdict v2 build failed: user_id=%s", user["id"])
        raise HTTPException(500, f"피드 분석 생성 실패: {e}")
    except ValueError as e:
        # photo count mismatch 등 input validation
        raise HTTPException(400, str(e))

    # 5. R2 업로드 — 영구 보관. ranked_photo_ids 컬럼에 photo_index + r2_key 기록.
    verdict_id = f"vrd_{uuid.uuid4().hex[:24]}"
    photo_records: list[dict] = []       # DB 저장용: {photo_index, r2_key, content_type}
    photo_urls: list[Optional[str]] = [] # 응답용
    for idx, (data, ct) in enumerate(raw_photo_blobs):
        ext = _ext_from_content_type(ct)
        key = r2_client.user_photo_key(
            user["id"], f"verdicts/{verdict_id}/photo_{idx}{ext}",
        )
        try:
            r2_client.put_bytes(key, data, content_type=ct)
            photo_records.append({
                "photo_index": idx,
                "r2_key": key,
                "content_type": ct,
            })
            photo_urls.append(r2_client.public_url(key))
        except Exception:
            logger.exception(
                "verdict v2 R2 upload failed: verdict_id=%s idx=%d", verdict_id, idx,
            )
            # 저장 실패해도 verdict 생성 계속 — 응답에선 해당 slot None.
            photo_records.append({
                "photo_index": idx,
                "r2_key": None,
                "content_type": ct,
            })
            photo_urls.append(None)

    # v1 NOT NULL columns 에 v2 sensible defaults
    synthetic_photo_ids = [f"p_{verdict_id}_{i}" for i in range(len(photos))]
    db.execute(
        text(
            "INSERT INTO verdicts ("
            "  id, user_id, candidate_count, winner_photo_id, ranked_photo_ids, "
            "  coordinates_snapshot, reasoning_unlocked, blur_released, gold_reading, "
            "  preview_shown, full_unlocked, preview_content, full_content, "
            "  user_profile_snapshot, version"
            ") VALUES ("
            "  :id, :uid, :cc, :wp, CAST(:ranked AS jsonb), "
            "  NULL, FALSE, FALSE, '', "
            "  TRUE, FALSE, CAST(:pc AS jsonb), CAST(:fc AS jsonb), "
            "  CAST(:ps AS jsonb), 'v2'"
            ")"
        ),
        {
            "id": verdict_id,
            "uid": user["id"],
            "cc": len(photos),
            "wp": synthetic_photo_ids[0],
            # v2: ranked_photo_ids 컬럼에 R2 key 기록한 리스트. (v1 과는 shape 다름 —
            # version='v2' 필드로 구분. GET 시 version 분기로 파싱.)
            "ranked": json.dumps(photo_records, ensure_ascii=False),
            "pc": json.dumps(result.preview.model_dump(mode="json"), ensure_ascii=False),
            "fc": json.dumps(result.full_content.model_dump(mode="json"), ensure_ascii=False),
            "ps": json.dumps(
                _sanitize_profile_snapshot(profile), default=str, ensure_ascii=False,
            ),
        },
    )
    db.commit()

    logger.info(
        "verdict v2 created: verdict_id=%s user_id=%s photos=%d",
        verdict_id, user["id"], len(photos),
    )

    best_fit_idx = _resolve_best_fit_index(result.preview, result.full_content)
    return CreateResponse(
        verdict_id=verdict_id,
        version="v2",
        preview=result.preview,
        full_unlocked=False,
        photo_count=len(photos),
        photo_urls=photo_urls,
        best_fit_photo_url=_best_fit_url(photo_urls, best_fit_idx),
    )


# ─────────────────────────────────────────────
#  POST /{verdict_id}/unlock
# ─────────────────────────────────────────────

@router.post("/{verdict_id}/unlock", response_model=UnlockResponse)
def unlock_verdict_v2(
    verdict_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> UnlockResponse:
    """full_content 해제 — 10 토큰 차감 + full_unlocked=TRUE.

    Atomic:
      1. verdict 검증 (owner, version=v2, not already unlocked)
      2. balance >= 10 확인
      3. BEGIN; token debit (idempotent) + full_unlocked=TRUE; COMMIT
      4. 응답: full_content + 새 balance

    Idempotency: idempotency_key=verdict_id → 중복 unlock 요청 시 같은 응답.
    토큰 2번 차감 방지 (token_transactions.idempotency_key UNIQUE).
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    # 1. Verdict 조회 + 검증
    row = db.execute(
        text(
            "SELECT id, user_id, version, full_unlocked, preview_content, "
            "       full_content, ranked_photo_ids "
            "FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()
    if row is None:
        raise HTTPException(404, "피드 분석을 찾을 수 없습니다.")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 피드 분석이 아닙니다.")
    if row.version != "v2":
        raise HTTPException(
            409,
            "v1 피드 분석은 v2 해제 경로를 사용할 수 없습니다.",
        )
    if row.full_content is None:
        # 생성 오류로 full_content 빠진 edge case
        raise HTTPException(500, "피드 분석 내용이 손상되어 해제 불가합니다.")

    photo_urls = _photo_urls_from_ranked(row.ranked_photo_ids)

    # 2. Already unlocked — idempotent return (추가 과금 없음)
    if row.full_unlocked:
        balance = tokens_service.get_balance(db, user["id"])
        full = FullContent.model_validate(row.full_content)
        preview_existing = (
            PreviewContent.model_validate(row.preview_content)
            if row.preview_content is not None
            else None
        )
        return UnlockResponse(
            verdict_id=verdict_id,
            full_unlocked=True,
            full_content=full,
            balance=balance,
            photo_urls=photo_urls,
            best_fit_photo_url=_best_fit_url(
                photo_urls,
                _resolve_best_fit_index(preview_existing, full),
            ),
        )

    # 3. Balance check
    balance = tokens_service.get_balance(db, user["id"])
    cost = tokens_service.COST_VERDICT_V2_UNLOCK
    if balance < cost:
        raise HTTPException(
            402,
            f"토큰 부족 — 필요 {cost}, 보유 {balance}.",
        )

    # 4. Atomic transaction — token debit + full_unlocked=TRUE
    try:
        # credit_tokens with negative amount = debit. idempotency_key 는 verdict_id.
        # 이미 동일 idempotency_key 로 차감됐다면 기존 balance_after 반환 (no double-charge).
        new_balance = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-cost,
            kind=tokens_service.KIND_CONSUME_VERDICT_V2,
            idempotency_key=verdict_id,
            reference_id=verdict_id,
            reference_type="verdict_v2",
        )
        # full_unlocked = TRUE. idempotent (이미 TRUE 면 no-op)
        db.execute(
            text(
                "UPDATE verdicts SET full_unlocked = TRUE "
                "WHERE id = :id AND full_unlocked = FALSE"
            ),
            {"id": verdict_id},
        )
        # STEP 4 — user_history.verdict_sessions append
        _append_verdict_history(
            db,
            user_id=user["id"],
            verdict_id=verdict_id,
            full_content=row.full_content,
            photo_urls=photo_urls,
        )
        db.commit()
    except IntegrityError as e:
        # Race condition: 동일 verdict_id 로 동시 unlock 요청 2개
        db.rollback()
        # 재조회로 상태 확인
        balance = tokens_service.get_balance(db, user["id"])
        recheck = db.execute(
            text("SELECT full_unlocked FROM verdicts WHERE id = :id"),
            {"id": verdict_id},
        ).first()
        if recheck and recheck.full_unlocked:
            # 다른 thread 가 unlock 완료 — idempotent 응답
            full = FullContent.model_validate(row.full_content)
            preview_existing = (
                PreviewContent.model_validate(row.preview_content)
                if row.preview_content is not None
                else None
            )
            return UnlockResponse(
                verdict_id=verdict_id,
                full_unlocked=True,
                full_content=full,
                balance=balance,
                photo_urls=photo_urls,
                best_fit_photo_url=_best_fit_url(
                    photo_urls,
                    _resolve_best_fit_index(preview_existing, full),
                ),
            )
        raise HTTPException(500, f"해제 처리 중 race condition 발생: {e}")

    # 5. 응답
    full = FullContent.model_validate(row.full_content)
    preview_existing = (
        PreviewContent.model_validate(row.preview_content)
        if row.preview_content is not None
        else None
    )
    return UnlockResponse(
        verdict_id=verdict_id,
        full_unlocked=True,
        full_content=full,
        balance=new_balance,
        photo_urls=photo_urls,
        best_fit_photo_url=_best_fit_url(
            photo_urls,
            _resolve_best_fit_index(preview_existing, full),
        ),
    )


def _append_verdict_history(
    db,
    *,
    user_id: str,
    verdict_id: str,
    full_content,
    photo_urls: list,
) -> None:
    """STEP 4 — user_history.verdict_sessions 에 head prepend.

    예외 전부 흡수 — unlock 메인 플로우 영향 금지.
    """
    try:
        from datetime import datetime, timezone
        from services import user_history
        from schemas.user_history import VerdictHistoryEntry

        fc = full_content if isinstance(full_content, dict) else {}
        photo_insights = fc.get("photo_insights") if isinstance(fc, dict) else None
        recommendation = fc.get("recommendation") if isinstance(fc, dict) else None

        entry = VerdictHistoryEntry(
            session_id=verdict_id,
            created_at=datetime.now(timezone.utc),
            photos_r2_urls=list(photo_urls or []),
            photo_insights=(photo_insights or []),
            recommendation=(recommendation or None),
        )
        user_history.append_history(
            db, user_id=user_id, category="verdict_sessions", entry=entry,
        )
    except Exception:
        logger.exception("append_verdict_history failed user=%s", user_id)


# ─────────────────────────────────────────────
#  GET /{verdict_id}
# ─────────────────────────────────────────────

@router.get("/{verdict_id}", response_model=GetResponse)
def get_verdict_v2(
    verdict_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> GetResponse:
    """Verdict 재조회. preview 는 항상, full_content 는 unlock 된 경우만."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT id, user_id, version, full_unlocked, preview_content, "
            "       full_content, ranked_photo_ids "
            "FROM verdicts WHERE id = :id"
        ),
        {"id": verdict_id},
    ).first()
    if row is None:
        raise HTTPException(404, "피드 분석을 찾을 수 없습니다.")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 피드 분석이 아닙니다.")
    if row.version != "v2":
        raise HTTPException(
            409,
            "v1 피드 분석은 v2 조회 경로를 사용할 수 없습니다. "
            "/api/v1/verdicts/{id} 를 사용하십시오.",
        )
    if row.preview_content is None:
        raise HTTPException(500, "피드 분석 preview 가 손상되어 조회 불가합니다.")

    preview = PreviewContent.model_validate(row.preview_content)
    full = None
    if row.full_unlocked and row.full_content is not None:
        full = FullContent.model_validate(row.full_content)

    photo_urls = _photo_urls_from_ranked(row.ranked_photo_ids)
    best_fit_idx = _resolve_best_fit_index(preview, full)
    return GetResponse(
        verdict_id=verdict_id,
        version="v2",
        full_unlocked=bool(row.full_unlocked),
        preview=preview,
        full_content=full,
        photo_urls=photo_urls,
        best_fit_photo_url=_best_fit_url(photo_urls, best_fit_idx),
    )


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _sanitize_profile_snapshot(profile: dict) -> dict:
    """user_profile 에서 snapshot 에 저장할 필드만 선별.

    제외: 불필요한 meta (created_at / updated_at / user_id 중복).
    보존: 분석에 쓰인 구조적 입력 + IG cache.
    """
    return {
        "gender": profile.get("gender"),
        "birth_date": str(profile.get("birth_date")) if profile.get("birth_date") else None,
        "structured_fields": profile.get("structured_fields") or {},
        "ig_feed_cache": profile.get("ig_feed_cache"),
        "ig_fetch_status": profile.get("ig_fetch_status"),
    }


_EXT_BY_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _ext_from_content_type(ct: str) -> str:
    return _EXT_BY_CT.get(ct, ".jpg")


def _best_fit_url(
    photo_urls: list[Optional[str]],
    best_fit_index: Optional[int],
) -> Optional[str]:
    """photo_urls[best_fit_index] 안전 접근.

    None 처리:
      - best_fit_index 가 None → None 반환
      - 인덱스 범위 밖 → None 반환
      - photo_urls[idx] 자체가 None (R2 저장 실패) → None 반환
    """
    if best_fit_index is None:
        return None
    if 0 <= best_fit_index < len(photo_urls):
        return photo_urls[best_fit_index]
    return None


def _resolve_best_fit_index(
    preview: Optional[PreviewContent],
    full: Optional[FullContent],
) -> Optional[int]:
    """best_fit_photo_index source of truth 결정.

    우선순위:
      1. full_content.best_fit_photo_index (있으면 정답)
      2. preview.best_fit_photo_index (full 누락 시 fallback)
      3. None
    """
    if full is not None and full.best_fit_photo_index is not None:
        return full.best_fit_photo_index
    if preview is not None and preview.best_fit_photo_index is not None:
        return preview.best_fit_photo_index
    return None


def _photo_urls_from_ranked(ranked) -> list[Optional[str]]:
    """verdicts.ranked_photo_ids JSONB (v2 shape) → public URL list.

    v2 shape: [{photo_index, r2_key, content_type}, ...]
    v1 shape (fallback): [{photo_id, filename, score}, ...] — photo_urls 비움.
    저장 실패 slot / public_url 미설정 → None.
    """
    if not isinstance(ranked, list):
        return []
    # v1 레거시 shape 감지 — r2_key 키가 전혀 없으면 빈 리스트 반환.
    has_r2_key = any(isinstance(e, dict) and "r2_key" in e for e in ranked)
    if not has_r2_key:
        return []

    urls: list[Optional[str]] = []
    # photo_index 순서 정렬
    sorted_entries = sorted(
        (e for e in ranked if isinstance(e, dict)),
        key=lambda e: e.get("photo_index", 0),
    )
    for entry in sorted_entries:
        key = entry.get("r2_key")
        if not key:
            urls.append(None)
            continue
        urls.append(r2_client.public_url(key))
    return urls
