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
from services import user_history
from services.aspiration_common import (
    extract_user_posts_from_vault,
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

    # STEP 5g — 본인 IG 핸들 차단 (자기 자신 분석 방지)
    _own_handle = (vault.basic_info.ig_handle or "").strip().lstrip("@").lower()
    if _own_handle and handle == _own_handle:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "self_handle_rejected",
                "message": "본인 IG 는 추구미 분석 대상이 아니에요. 추구하는 다른 분의 IG 를 입력해주세요.",
            },
        )

    user_profile = vault.get_user_taste_profile()

    # STEP 5g — Sia 대화 미완 (current_position None) 차단
    if user_profile.current_position is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "sia_required",
                "message": "먼저 Sia 와 대화하면서 본인 결을 잡아둘게요. 그 다음 추구미와 비교해보면 정확해요.",
                "cta": {"label": "Sia 와 대화 시작", "href": "/sia"},
            },
        )

    # 본인 IG posts — photo_pairs 좌측 채움 (vault.ig_feed_cache.latest_posts)
    user_posts = extract_user_posts_from_vault(vault)

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

    # 엔진 실행 — Phase J5: profile (vault 5/5) + user_name 흘림
    result: AspirationRunResult = run_aspiration_ig(
        db,
        user_id=user["id"],
        user_gender=vault.basic_info.gender,
        user_coordinate=user_profile.current_position,
        target_handle_raw=handle,
        user_posts=user_posts,
        profile=user_profile,
        user_name=vault.basic_info.name,
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

    # 저장 + user_history append (STEP 4)
    # Phase J5 — narrative dict (raw_haiku_response / matched_trends_used /
    # action_hints / gap_summary / strength_score_at_time / user_original_phrases_at_time)
    # 를 result_data JSONB 에 합쳐 저장. 휘발 방지.
    persist_analysis(
        db, result.analysis, extra_result_data=result.narrative,
    )
    _append_aspiration_history(db, user_id=user["id"], analysis=result.analysis)
    db.commit()

    # STEP 11 — 응답에서도 matched_trends hydrate (첫 조회 CTA 노출)
    # v1.5: snapshot 우선 (분석 시점 동결), 없으면 KB hydrate fallback.
    result.analysis.matched_trends = _hydrate_matched_trends(
        result.analysis.matched_trend_ids,
        snapshot=result.analysis.matched_trends_snapshot,
    )

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

    # STEP 5g — Sia 대화 미완 (current_position None) 차단
    if user_profile.current_position is None:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "sia_required",
                "message": "먼저 Sia 와 대화하면서 본인 결을 잡아둘게요. 그 다음 추구미와 비교해보면 정확해요.",
                "cta": {"label": "Sia 와 대화 시작", "href": "/sia"},
            },
        )

    # 본인 IG posts — photo_pairs 좌측 채움
    user_posts = extract_user_posts_from_vault(vault)

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
        user_posts=user_posts,
        profile=user_profile,
        user_name=vault.basic_info.name,
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

    # Phase J5 — narrative 휘발 방지 보존
    persist_analysis(
        db, result.analysis, extra_result_data=result.narrative,
    )
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
    """소유자만 조회. 타 유저 → 403.

    STEP 11: matched_trend_ids 를 KB 에서 hydrate 해서 matched_trends 채움.
    """
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

    analysis = AspirationAnalysis.model_validate(row.result_data)
    # v1.5: snapshot 우선, 없으면 KB hydrate fallback (구 row 후방호환).
    analysis.matched_trends = _hydrate_matched_trends(
        analysis.matched_trend_ids,
        snapshot=analysis.matched_trends_snapshot,
    )
    return analysis


def _hydrate_matched_trends(
    trend_ids: list[str],
    *,
    snapshot: Optional[list[dict]] = None,
):
    """matched_trends 응답 hydrate — v1.5 후방호환.

    우선순위:
      1. snapshot 있으면 그것 사용 (분석 시점 동결, KB 변경 무관)
      2. snapshot None / 빈값 → KB hydrate fallback (구 row, KB 신뢰)

    KB 변경 시 과거 리포트 행동지침 보존 보장. 예외 전부 흡수.
    """
    # 1) Snapshot 우선 — 분석 시점 동결된 객체 그대로 복원
    if snapshot:
        try:
            from schemas.aspiration import MatchedTrendView
            return [
                MatchedTrendView.model_validate(d)
                for d in snapshot
                if isinstance(d, dict)
            ]
        except Exception:
            logger.exception(
                "matched_trends snapshot parse failed → falling back to KB hydrate"
            )
            # snapshot 깨졌어도 fallback 으로 진행

    # 2) KB hydrate fallback (snapshot 없는 구 row)
    if not trend_ids:
        return []
    try:
        from schemas.aspiration import MatchedTrendView
        from services.knowledge_base import load_trends
        # 전체 로드 (여성 + 남성 + 모든 시즌) 후 id 매칭 — KB 크기 작음 (~50 items)
        all_trends = load_trends()
        by_id = {t.trend_id: t for t in all_trends}
        views = []
        for tid in trend_ids:
            t = by_id.get(tid)
            if t is None:
                continue
            views.append(MatchedTrendView(
                trend_id=t.trend_id,
                title=t.title,
                category=str(t.category),
                detailed_guide=t.detailed_guide,
                action_hints=list(t.action_hints or []),
                score=None,
            ))
        return views
    except Exception:
        logger.exception("hydrate_matched_trends failed for ids=%s", trend_ids)
        return []


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _append_aspiration_history(db, *, user_id: str, analysis) -> None:
    """STEP 4 — user_history.aspiration_analyses 에 head prepend.

    예외 삼킴 — 메인 persist 플로우 영향 금지.
    """
    try:
        from schemas.user_history import (
            AspirationHistoryEntry,
            HistoryPhotoPair,
        )
        pairs = [
            HistoryPhotoPair(
                user_photo_r2_url=p.user_photo_url,
                target_photo_r2_url=p.target_photo_url,
                pair_comment=p.target_sia_comment or p.user_sia_comment or None,
            )
            for p in (analysis.photo_pairs or [])
        ]
        # Phase J5 — gap_vector dump 보존 (좌표 메타).
        gap_dump = (
            analysis.gap_vector.model_dump(mode="json")
            if getattr(analysis, "gap_vector", None) is not None
            else None
        )
        entry = AspirationHistoryEntry(
            analysis_id=analysis.analysis_id,
            created_at=analysis.created_at,
            source=(
                "pinterest" if analysis.target_type == "pinterest" else "instagram"
            ),
            target_handle=analysis.target_identifier,
            photo_pairs=pairs,
            gap_narrative=analysis.gap_narrative,
            sia_overall_message=analysis.sia_overall_message,
            target_analysis_snapshot=analysis.target_analysis_snapshot,
            aspiration_vector_snapshot=gap_dump,
        )
        user_history.append_history(
            db, user_id=user_id, category="aspiration_analyses", entry=entry,
        )
    except Exception:
        logger.exception("append_aspiration_history failed user=%s", user_id)


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
