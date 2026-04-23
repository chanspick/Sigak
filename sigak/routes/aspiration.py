"""Aspiration 엔드포인트 (Phase J5).

CLAUDE.md §3.5 / §3.6 / §10.1.

엔드포인트:
  POST /api/v2/aspiration/ig         — 20 토큰, IG 핸들
  POST /api/v2/aspiration/pinterest  — 20 토큰, Pinterest 보드 URL
  GET  /api/v2/aspiration/{id}       — 분석 결과 재조회

토큰 정책:
  - 요청마다 차감 (반복 구매 가능)
  - Idempotency key: f"aspiration_{type}:{user_id}:{target}:{timestamp}"
  - 차감 성공했는데 Apify 실패 시 status="failed_scrape" + 토큰 환불 (refund)
  - 블록리스트 차단 시 차감 전 차단
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from deps import db_session, get_current_user
from schemas.aspiration import (
    AspirationAnalysis,
    AspirationStartResponse,
    TargetType,
)
from services import tokens as tokens_service
from services.aspiration_common import (
    is_blocked,
    persist_analysis,
)
from services.aspiration_engine_ig import AspirationRunResult, run_aspiration_ig
from services.aspiration_engine_pinterest import run_aspiration_pinterest
from services.user_data_vault import load_vault


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/aspiration", tags=["aspiration"])


# ─────────────────────────────────────────────
#  Request bodies
# ─────────────────────────────────────────────

class IgRequest(BaseModel):
    target_handle: str


class PinterestRequest(BaseModel):
    board_url: str


# ─────────────────────────────────────────────
#  POST /ig
# ─────────────────────────────────────────────

@router.post("/ig", response_model=AspirationStartResponse)
def create_aspiration_ig(
    body: IgRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> AspirationStartResponse:
    """제3자 IG 핸들 추구미 분석 — 20 토큰 차감 + 수집/분석."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    handle = (body.target_handle or "").strip().lstrip("@").lower()
    if not handle:
        raise HTTPException(400, "target_handle 이 비었습니다.")

    if is_blocked(db, target_type="ig", target_identifier=handle):
        raise HTTPException(403, "해당 대상은 분석 차단 상태입니다.")

    # Vault 로드 (본인 맥락)
    vault = load_vault(db, user["id"])
    if vault is None:
        raise HTTPException(409, "onboarding 이 완료돼야 추구미 분석이 가능합니다.")
    user_profile = vault.get_user_taste_profile()

    # 토큰 차감 (반복 구매 가능 → idempotency 는 timestamp 포함)
    cost = tokens_service.COST_ASPIRATION_IG
    ts = int(time.time())
    idem = f"aspiration_ig:{user['id']}:{handle}:{ts}"

    balance = tokens_service.get_balance(db, user["id"])
    if balance < cost:
        raise HTTPException(
            402, f"토큰 부족 — 필요 {cost}, 보유 {balance}",
        )

    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-cost,
            kind=tokens_service.KIND_CONSUME_ASPIRATION_IG,
            idempotency_key=idem,
            reference_type="aspiration_target",
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(500, "토큰 차감 중복 경합 — 재시도 해주세요.")

    # 엔진 실행
    result: AspirationRunResult = run_aspiration_ig(
        db,
        user_id=user["id"],
        user_gender=vault.basic_info.gender,
        user_coordinate=user_profile.current_position,
        target_handle_raw=handle,
    )

    # 실패 정책 — 수집 실패면 환불
    if result.status != "completed" or result.analysis is None:
        _refund_aspiration(
            db, user_id=user["id"], cost=cost, idempotency_key=idem,
            kind=tokens_service.KIND_CONSUME_ASPIRATION_IG,
            reason=result.error_detail or result.status,
        )
        db.commit()
        return AspirationStartResponse(
            analysis_id="",
            status=result.status,  # type: ignore[arg-type]
            analysis=None,
            token_balance=tokens_service.get_balance(db, user["id"]),
        )

    # 저장
    persist_analysis(db, result.analysis)
    db.commit()

    return AspirationStartResponse(
        analysis_id=result.analysis.analysis_id,
        status="completed",
        analysis=result.analysis,
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  POST /pinterest
# ─────────────────────────────────────────────

@router.post("/pinterest", response_model=AspirationStartResponse)
def create_aspiration_pinterest(
    body: PinterestRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> AspirationStartResponse:
    """Pinterest 보드 URL 추구미 분석 — 20 토큰."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    if not body.board_url.strip():
        raise HTTPException(400, "board_url 이 비었습니다.")

    vault = load_vault(db, user["id"])
    if vault is None:
        raise HTTPException(409, "onboarding 이 완료돼야 추구미 분석이 가능합니다.")
    user_profile = vault.get_user_taste_profile()

    cost = tokens_service.COST_ASPIRATION_PINTEREST
    ts = int(time.time())
    idem = f"aspiration_pinterest:{user['id']}:{body.board_url}:{ts}"

    balance = tokens_service.get_balance(db, user["id"])
    if balance < cost:
        raise HTTPException(402, f"토큰 부족 — 필요 {cost}, 보유 {balance}")

    try:
        balance_after = tokens_service.credit_tokens(
            db,
            user_id=user["id"],
            amount=-cost,
            kind=tokens_service.KIND_CONSUME_ASPIRATION_PINTEREST,
            idempotency_key=idem,
            reference_type="aspiration_target",
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(500, "토큰 차감 중복 경합 — 재시도 해주세요.")

    result = run_aspiration_pinterest(
        db,
        user_id=user["id"],
        user_gender=vault.basic_info.gender,
        user_coordinate=user_profile.current_position,
        board_url=body.board_url,
    )

    if result.status != "completed" or result.analysis is None:
        _refund_aspiration(
            db, user_id=user["id"], cost=cost, idempotency_key=idem,
            kind=tokens_service.KIND_CONSUME_ASPIRATION_PINTEREST,
            reason=result.error_detail or result.status,
        )
        db.commit()
        return AspirationStartResponse(
            analysis_id="",
            status=result.status,  # type: ignore[arg-type]
            analysis=None,
            token_balance=tokens_service.get_balance(db, user["id"]),
        )

    persist_analysis(db, result.analysis)
    db.commit()

    return AspirationStartResponse(
        analysis_id=result.analysis.analysis_id,
        status="completed",
        analysis=result.analysis,
        token_balance=balance_after,
    )


# ─────────────────────────────────────────────
#  GET /{id}
# ─────────────────────────────────────────────

@router.get("/{analysis_id}", response_model=AspirationAnalysis)
def get_aspiration(
    analysis_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> AspirationAnalysis:
    """소유자만 조회. 타 유저 → 403."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT user_id, result_data FROM aspiration_analyses "
            "WHERE id = :id"
        ),
        {"id": analysis_id},
    ).first()
    if row is None:
        raise HTTPException(404, "분석 결과를 찾을 수 없습니다.")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 분석이 아닙니다.")

    return AspirationAnalysis.model_validate(row.result_data)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _refund_aspiration(
    db,
    *,
    user_id: str,
    cost: int,
    idempotency_key: str,
    kind: str,
    reason: str,
) -> None:
    """수집 실패 시 역방향 credit. refund idempotency 는 원 key + ':refund' 접미."""
    refund_key = f"{idempotency_key}:refund"
    try:
        tokens_service.credit_tokens(
            db,
            user_id=user_id,
            amount=+cost,
            kind=tokens_service.KIND_REFUND,
            idempotency_key=refund_key,
            reference_id=idempotency_key,
            reference_type="aspiration_refund",
        )
        logger.info(
            "aspiration refund: user=%s cost=%d reason=%s",
            user_id, cost, reason,
        )
    except IntegrityError:
        db.rollback()
        logger.warning(
            "aspiration refund race: user=%s key=%s", user_id, refund_key,
        )
