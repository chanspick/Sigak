"""Best Shot 엔드포인트 (Phase K6).

본인 확정:
  - 50장 미만 업로드 시도 → 피드 추천 유도 (UI 블록 + CTA)
  - strength_score < 0.3 시 경고 모달 + 진행 선택
  - 업로드 resume, best_shot_sessions 기록
  - 실패 처리 3종: quality all reject / Sonnet fail / cost cap → refund

엔드포인트:
  POST /api/v2/best-shot/init
       expected_count 검증 (50-500) + strength_score 계산 + 경고 gate
  POST /api/v2/best-shot/upload/{session_id}
       multipart 업로드. 파일 당 1개 / 배치 N개 (프론트 설계에 따라)
  POST /api/v2/best-shot/run/{session_id}
       토큰 30 차감 + heuristic + Sonnet + 결과 저장
  GET  /api/v2/best-shot/{session_id}
       세션 + 결과 조회
  POST /api/v2/best-shot/{session_id}/abort
       업로드 중단 + R2 원본 삭제

토큰 정책:
  run 단계에서 차감. abort 는 차감 전이므로 refund 불필요.
  실패 3종은 refund — aspiration 와 동일 패턴 (`{key}:refund`).
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from config import get_settings
from deps import db_session, get_current_user
from schemas.best_shot import (
    BestShotResult,
    BestShotSession,
    BestShotStatus,
    GetSessionResponse,
    InitRequest,
    InitResponse,
    RunResponse,
    UploadAck,
)
from services import cost_monitor, r2_client, tokens as tokens_service
from services.best_shot_engine import (
    BestShotEngineError,
    generate_session_id,
    run_best_shot,
)
from services.user_data_vault import load_vault


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/best-shot", tags=["best-shot"])


# ─────────────────────────────────────────────
#  POST /init
# ─────────────────────────────────────────────

@router.post("/init", response_model=InitResponse)
def init_session(
    body: InitRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> InitResponse:
    """업로드 세션 시작.

    - expected_count 범위 검증 (pydantic 단계 + 메시지 커스텀)
    - strength_score 경고 (< 0.3, not acknowledged → 409)
    - best_shot_sessions INSERT (status='uploading')
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    settings = get_settings()
    # 범위는 pydantic Field 가 이미 50~500 검증. 범위 초과 시 메시지 친절히.
    if body.expected_count < settings.best_shot_min_upload:
        raise HTTPException(
            400,
            {
                "code": "too_few_photos",
                "message": f"Best Shot 은 {settings.best_shot_min_upload}장 이상에서 엄선하는 상품입니다.",
                "suggestion": "10장 이하 판독은 피드 추천(₩1,000)을 이용해 주십시오.",
                "redirect": "/verdict/new",
            },
        )
    if body.expected_count > settings.best_shot_max_upload:
        raise HTTPException(
            400,
            f"사진은 최대 {settings.best_shot_max_upload}장까지 업로드 가능합니다.",
        )

    # strength_score 계산
    vault = load_vault(db, user["id"])
    if vault is None:
        raise HTTPException(409, "onboarding 이 완료돼야 Best Shot 이용 가능합니다.")
    profile = vault.get_user_taste_profile()
    strength = float(profile.strength_score or 0.0)

    if strength < 0.3 and not body.acknowledge_strength_warning:
        # 경고 단계 — 프론트가 모달 띄우고 acknowledge_strength_warning=true 로 재요청.
        raise HTTPException(
            409,
            {
                "code": "strength_low",
                "message": "수집된 정보가 아직 적어 선별 정확도가 떨어질 수 있습니다.",
                "strength_score": round(strength, 3),
                "suggestion": "시각이 본 당신 첫 리포트 + 추구미 분석 1~2 회 이후 재이용 권장.",
                "acknowledge_required": True,
            },
        )

    # Session INSERT
    session_id = generate_session_id()
    target_count = body.expected_count // 15
    max_count = body.expected_count // 10

    try:
        db.execute(
            text(
                "INSERT INTO best_shot_sessions "
                "  (session_id, user_id, status, uploaded_count, "
                "   target_count, max_count, strength_score_snapshot, "
                "   strength_warning_acknowledged, created_at, updated_at) "
                "VALUES (:sid, :uid, 'uploading', 0, :tgt, :mx, :ss, :ack, NOW(), NOW())"
            ),
            {
                "sid": session_id,
                "uid": user["id"],
                "tgt": target_count,
                "mx": max_count,
                "ss": strength,
                "ack": bool(body.acknowledge_strength_warning),
            },
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(500, "세션 생성 실패.")

    return InitResponse(
        session_id=session_id,
        status="uploading",
        target_count=target_count,
        max_count=max_count,
        strength_score=round(strength, 3),
        strength_warning_required=(strength < 0.3 and not body.acknowledge_strength_warning),
        upload_limit=settings.best_shot_max_upload,
        upload_minimum=settings.best_shot_min_upload,
    )


# ─────────────────────────────────────────────
#  POST /upload/{session_id}
# ─────────────────────────────────────────────

@router.post("/upload/{session_id}", response_model=UploadAck)
async def upload_batch(
    session_id: str,
    photos: list[UploadFile] = File(...),
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> UploadAck:
    """다수 사진 배치 업로드. resume 가능 — 반복 호출 시 uploaded_count 증가."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    session = _load_session(db, session_id, user["id"])
    if session.status not in ("uploading", "ready_to_run"):
        raise HTTPException(
            409, f"이 세션은 현재 업로드 불가 상태입니다: status={session.status}",
        )
    if not photos:
        raise HTTPException(400, "업로드 파일이 비었습니다.")

    settings = get_settings()
    allowed_ct = {"image/jpeg", "image/png", "image/webp"}
    max_bytes = 15 * 1024 * 1024   # per file

    added = 0
    for uf in photos:
        if session.uploaded_count + added >= settings.best_shot_max_upload:
            break
        ct = uf.content_type or "image/jpeg"
        if ct not in allowed_ct:
            logger.warning("skip unsupported content_type=%s", ct)
            continue
        data = await uf.read()
        if not data:
            continue
        if len(data) > max_bytes:
            logger.warning("skip oversize file (%d > %d)", len(data), max_bytes)
            continue
        photo_id = f"{uuid.uuid4().hex[:20]}.jpg"
        key = r2_client.best_shot_upload_key(user["id"], session_id, photo_id)
        try:
            r2_client.put_bytes(key, data, content_type=ct)
            added += 1
        except Exception:
            logger.exception("R2 put failed: key=%s", key)

    # 카운트 반영
    new_count = session.uploaded_count + added
    new_status: BestShotStatus = (
        "ready_to_run" if new_count >= settings.best_shot_min_upload else "uploading"
    )
    db.execute(
        text(
            "UPDATE best_shot_sessions "
            "SET uploaded_count = :c, status = :s, updated_at = NOW() "
            "WHERE session_id = :sid"
        ),
        {"c": new_count, "s": new_status, "sid": session_id},
    )
    db.commit()

    remaining = max(0, settings.best_shot_max_upload - new_count)
    return UploadAck(
        session_id=session_id,
        status=new_status,
        uploaded_count=new_count,
        remaining_to_upload=remaining,
    )


# ─────────────────────────────────────────────
#  POST /run/{session_id}
# ─────────────────────────────────────────────

@router.post("/run/{session_id}", response_model=RunResponse)
def run_selection(
    session_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> RunResponse:
    """30 토큰 차감 + heuristic + Sonnet 선별 → 결과 저장."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    settings = get_settings()
    session = _load_session(db, session_id, user["id"])
    if session.status != "ready_to_run":
        if session.status == "ready":
            # 이미 완료된 세션 — idempotent 조회
            balance = tokens_service.get_balance(db, user["id"])
            return RunResponse(
                session_id=session_id,
                status="ready",
                result=session.result,
                token_balance=balance,
            )
        raise HTTPException(
            409,
            f"이 세션은 실행 불가 상태입니다: status={session.status} "
            f"(uploaded {session.uploaded_count}, min {settings.best_shot_min_upload} 필요)",
        )
    if session.uploaded_count < settings.best_shot_min_upload:
        raise HTTPException(
            400,
            f"업로드 {session.uploaded_count} 장 — 최소 {settings.best_shot_min_upload} 필요.",
        )

    # 토큰 차감
    cost = tokens_service.COST_BEST_SHOT
    idem = f"best_shot:{user['id']}:{session_id}"
    balance = tokens_service.get_balance(db, user["id"])
    if balance < cost:
        raise HTTPException(402, f"토큰 부족 — 필요 {cost}, 보유 {balance}")

    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-cost,
            kind=tokens_service.KIND_CONSUME_BEST_SHOT,
            idempotency_key=idem,
            reference_id=session_id,
            reference_type="best_shot_session",
        )
        # status='running' 전환
        db.execute(
            text(
                "UPDATE best_shot_sessions "
                "SET status='running', updated_at=NOW() WHERE session_id=:sid"
            ),
            {"sid": session_id},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        # 이미 idempotency key 로 차감된 상태 — 조회로 대응
        balance_after = tokens_service.get_balance(db, user["id"])

    # Vault + profile
    vault = load_vault(db, user["id"])
    profile = vault.get_user_taste_profile() if vault else None

    # 유저 호명용 이름 — users.name 우선, 없으면 onboarding_data.name, 최종 빈 문자열
    user_name = _resolve_user_name(db, user)

    # 업로드된 key 목록 (prefix list — R2 get_bytes 은 key 필요)
    uploaded_keys = _list_uploaded_keys(user["id"], session_id, session.uploaded_count)

    try:
        result = run_best_shot(
            user_id=user["id"],
            session_id=session_id,
            uploaded_photo_keys=uploaded_keys,
            profile=profile,
            gender=(vault.basic_info.gender if vault else None),
            user_name=user_name,
        )
    except cost_monitor.CostLimitExceeded as e:
        _mark_failed_and_refund(
            db, session_id=session_id, user_id=user["id"],
            cost=cost, idempotency_key=idem,
            reason=f"cost_cap: {e}",
        )
        db.commit()
        return RunResponse(
            session_id=session_id, status="failed",
            result=None, token_balance=tokens_service.get_balance(db, user["id"]),
            failure_reason="일일 운영 비용 한도 초과 — 토큰은 환불됐습니다.",
        )
    except BestShotEngineError as e:
        _mark_failed_and_refund(
            db, session_id=session_id, user_id=user["id"],
            cost=cost, idempotency_key=idem,
            reason=f"engine: {e}",
        )
        db.commit()
        return RunResponse(
            session_id=session_id, status="failed",
            result=None, token_balance=tokens_service.get_balance(db, user["id"]),
            failure_reason=f"선별 실패 — 토큰은 환불됐습니다. ({e})",
        )
    except Exception as e:
        logger.exception("best_shot unexpected error: session=%s", session_id)
        _mark_failed_and_refund(
            db, session_id=session_id, user_id=user["id"],
            cost=cost, idempotency_key=idem,
            reason=f"unexpected: {type(e).__name__}",
        )
        db.commit()
        return RunResponse(
            session_id=session_id, status="failed",
            result=None, token_balance=tokens_service.get_balance(db, user["id"]),
            failure_reason="선별 처리 중 오류 — 토큰은 환불됐습니다.",
        )

    # 결과 저장 + status='ready'
    db.execute(
        text(
            "UPDATE best_shot_sessions "
            "SET status='ready', result_data = CAST(:rd AS jsonb), updated_at = NOW() "
            "WHERE session_id = :sid"
        ),
        {
            "sid": session_id,
            "rd": json.dumps(result.model_dump(mode="json"), ensure_ascii=False),
        },
    )
    db.commit()

    return RunResponse(
        session_id=session_id,
        status="ready",
        result=result,
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  GET /{session_id}
# ─────────────────────────────────────────────

@router.get("/{session_id}", response_model=GetSessionResponse)
def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> GetSessionResponse:
    if db is None:
        raise HTTPException(500, "DB unavailable")
    session = _load_session(db, session_id, user["id"])
    return GetSessionResponse(session=session)


# ─────────────────────────────────────────────
#  POST /{session_id}/abort
# ─────────────────────────────────────────────

@router.post("/{session_id}/abort")
def abort_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> dict:
    """업로드 중단 + R2 원본 prefix 삭제. 차감 전 단계만 허용."""
    if db is None:
        raise HTTPException(500, "DB unavailable")
    session = _load_session(db, session_id, user["id"])
    if session.status in ("running", "ready"):
        raise HTTPException(
            409, f"이미 실행/완료된 세션은 취소 불가: status={session.status}",
        )

    # R2 원본 삭제 (uploads prefix)
    prefix = r2_client.user_photo_key(
        user["id"], f"best_shot/uploads/{session_id}/",
    )
    deleted = 0
    try:
        deleted = r2_client.delete_prefix(prefix)
    except Exception:
        logger.exception("abort: R2 delete failed: prefix=%s", prefix)

    db.execute(
        text(
            "UPDATE best_shot_sessions "
            "SET status='aborted', updated_at=NOW() WHERE session_id=:sid"
        ),
        {"sid": session_id},
    )
    db.commit()

    return {
        "session_id": session_id,
        "status": "aborted",
        "deleted_photos": deleted,
    }


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _resolve_user_name(db, user: dict) -> str:
    """SiaWriter 호명용 이름 — users.name 우선, 없으면 onboarding_data.name, 최종 빈 문자열."""
    name = (user.get("name") or "").strip()
    if name:
        return name
    try:
        row = db.execute(
            text("SELECT onboarding_data FROM users WHERE id = :uid"),
            {"uid": user["id"]},
        ).first()
        if row and row.onboarding_data:
            raw = row.onboarding_data.get("name") if isinstance(row.onboarding_data, dict) else None
            if raw and isinstance(raw, str):
                return raw.strip()
    except Exception:
        logger.debug("user name lookup skipped for user=%s", user["id"])
    return ""


def _load_session(db, session_id: str, user_id: str) -> BestShotSession:
    row = db.execute(
        text(
            "SELECT session_id, user_id, status, uploaded_count, "
            "       target_count, max_count, strength_score_snapshot, "
            "       strength_warning_acknowledged, result_data, failure_reason, "
            "       created_at, updated_at "
            "FROM best_shot_sessions WHERE session_id = :sid"
        ),
        {"sid": session_id},
    ).first()
    if row is None:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    if row.user_id != user_id:
        raise HTTPException(403, "본인 세션이 아닙니다.")

    result: Optional[BestShotResult] = None
    if row.result_data:
        try:
            result = BestShotResult.model_validate(row.result_data)
        except Exception:
            logger.exception("result_data parse failed: session=%s", session_id)

    return BestShotSession(
        session_id=row.session_id,
        user_id=row.user_id,
        status=row.status,
        uploaded_count=row.uploaded_count,
        target_count=row.target_count,
        max_count=row.max_count,
        strength_score_snapshot=row.strength_score_snapshot or 0.0,
        strength_warning_acknowledged=row.strength_warning_acknowledged,
        result=result,
        failure_reason=row.failure_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _list_uploaded_keys(user_id: str, session_id: str, expected_count: int) -> list[str]:
    """R2 prefix list — best_shot/uploads/{session_id}/ 하위 keys.

    prod 에선 R2 list_objects_v2. local fallback 에서는 디렉터리 스캔.
    """
    # Pragmatic approach: run_best_shot 가 key 리스트만 기대. Prefix 기반 list 를
    # r2_client 에 별도 유틸로 추가하는 것보단, 실 배포 시 DB 에 key 리스트를
    # 기록하는 방식이 안전. MVP 는 prefix 디렉토리 스캔 (local) + R2 list.
    from services.r2_client import _client, _client_mode, _init_client
    _init_client()
    prefix = r2_client.user_photo_key(
        user_id, f"best_shot/uploads/{session_id}/",
    )
    keys: list[str] = []
    if _client_mode == "r2":
        try:
            settings = get_settings()
            paginator = _client.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=settings.r2_bucket_user_photos, Prefix=prefix,
            ):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
        except Exception:
            logger.exception("list uploaded keys failed (R2)")
    else:
        from pathlib import Path
        settings = get_settings()
        base: Path = _client["base_dir"] / settings.r2_bucket_user_photos
        full = base / prefix
        if full.exists():
            for fp in sorted(full.iterdir()):
                if fp.is_file():
                    keys.append(
                        str(fp.relative_to(base)).replace("\\", "/")
                    )
    return keys


def _mark_failed_and_refund(
    db,
    *,
    session_id: str,
    user_id: str,
    cost: int,
    idempotency_key: str,
    reason: str,
) -> None:
    """실패 3종 공통 처리: status='failed' + 토큰 refund."""
    try:
        tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=+cost,
            kind=tokens_service.KIND_REFUND,
            idempotency_key=f"{idempotency_key}:refund",
            reference_id=session_id,
            reference_type="best_shot_refund",
        )
        logger.info(
            "best_shot refund: user=%s session=%s reason=%s", user_id, session_id, reason,
        )
    except IntegrityError:
        db.rollback()
        logger.warning("best_shot refund race: session=%s", session_id)

    db.execute(
        text(
            "UPDATE best_shot_sessions "
            "SET status='failed', failure_reason=:r, updated_at=NOW() "
            "WHERE session_id=:sid"
        ),
        {"sid": session_id, "r": reason[:500]},
    )
