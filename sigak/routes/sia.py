"""Sia conversation endpoints (v2 Priority 1 D3).

SPEC-ONBOARDING-V2 REQ-SIA-*.

Flow:
  POST /api/v1/sia/chat/start      session 생성 + 첫 Sia 메시지 (오프닝)
  POST /api/v1/sia/chat/message    유저 발화 수신 → Sia 응답 반환
  POST /api/v1/sia/chat/end        명시 종료 → DB INSERT (status="ended") + extraction 큐잉

Redis active 기간에는 DB write 없음 (contract #3).
Extraction 은 chat/end 또는 idle timeout 시점에 BackgroundTask 로 큐잉 (D4 구현).

2026-04-22 D5 보강:
  - StartResponse/MessageResponse 에 response_mode, choices 추가.
  - /chat/message 에서 primary Redis TTL 만료 시 24h backup snapshot 을 DB flush.
"""
from __future__ import annotations

import logging
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db_session, get_current_user
from schemas.user_profile import ConversationMessage, StructuredFields
from services import conversations as conv_service
from services import sia_llm, sia_session
from services.sia_parser import is_name_fallback_turn, parse_sia_output
from services.user_profiles import get_profile


# 응답 모드 — 프론트 UI 분기 (4지선다 / 주관식 / 호칭 확인).
ResponseMode = Literal["choices", "freetext", "name_fallback"]


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sia", tags=["sia"])


# ─────────────────────────────────────────────
#  Request / Response models
# ─────────────────────────────────────────────

class StartResponse(BaseModel):
    conversation_id: str
    opening_message: str                # body — trailing choice 블록 제거
    turn_count: int = 0
    response_mode: ResponseMode         # choices / freetext / name_fallback
    choices: list[str] = []             # mode=="choices" 일 때 정확히 4개


class MessageRequest(BaseModel):
    conversation_id: str
    user_message: str = Field(min_length=1, max_length=1000)


class MessageResponse(BaseModel):
    conversation_id: str
    assistant_message: str              # body — trailing choice 블록 제거
    turn_count: int
    status: str                         # active / ending_soon / closed
    response_mode: ResponseMode         # choices / freetext / name_fallback
    choices: list[str] = []


class EndRequest(BaseModel):
    conversation_id: str


class EndResponse(BaseModel):
    conversation_id: str
    status: str                         # "ended"
    messages_persisted: int
    extraction_queued: bool


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

V2_REQUIRED_FIELDS = [
    "desired_image",
    "reference_style",
    "current_concerns",
    "self_perception",
    "lifestyle_context",
    "height",
    "weight",
    "shoulder_width",
]


def _missing_from_profile(profile: Optional[dict]) -> list[str]:
    """user_profile.structured_fields 에서 아직 비어 있는 필드 목록."""
    if not profile:
        return list(V2_REQUIRED_FIELDS)
    structured = profile.get("structured_fields") or {}
    return [f for f in V2_REQUIRED_FIELDS if not structured.get(f)]


def _build_messages_for_llm(session_state: dict) -> list[dict]:
    """Redis session messages → Claude API messages 포맷.

    ts 제거 (API 는 role/content 만 수용). 빈 messages 일 때 dummy user prompt
    삽입 (Claude API 는 첫 메시지가 user 여야 함).
    """
    raw = session_state.get("messages") or []
    out = []
    for m in raw:
        if m["role"] in ("user", "assistant"):
            out.append({"role": m["role"], "content": m["content"]})

    # 첫 턴 오프닝 용 dummy — Claude messages 는 최소 1개 user 필요
    if not out:
        out = [{"role": "user", "content": "(대화 시작)"}]
    return out


def _resolve_opening_user_name(user: dict) -> Optional[str]:
    """카톡 user dict 에서 name 추출. 애플 로그인 등 None 가능."""
    return user.get("name") or None


# ─────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────

@router.post("/chat/start", response_model=StartResponse)
def chat_start(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> StartResponse:
    """신규 conversation 생성 + Sia 오프닝 메시지 반환.

    - Redis 세션 생성 (TTL 5분 sliding)
    - user_profile 에서 ig_feed_cache / structured_fields 복사
    - Haiku 4.5 첫 턴 호출 (오프닝)
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    profile = get_profile(db, user["id"])
    if profile is None:
        raise HTTPException(
            409,
            "user_profile not found — Step 0 폼 제출 먼저 완료해 주십시오.",
        )

    conv_id = uuid.uuid4().hex
    missing = _missing_from_profile(profile)

    # Redis 세션 생성
    state = sia_session.create_session(
        conversation_id=conv_id,
        user_id=user["id"],
        resolved_name=None,
        ig_feed_cache=profile.get("ig_feed_cache"),
        missing_fields=missing,
    )

    # Sia 첫 턴 생성
    system_prompt = sia_llm.build_system_prompt(
        user_name=_resolve_opening_user_name(user),
        resolved_name=None,
        collected_fields=profile.get("structured_fields") or {},
        missing_fields=missing,
        ig_feed_cache=profile.get("ig_feed_cache"),
    )
    opening = sia_llm.call_sia_turn_with_retry(
        system_prompt=system_prompt,
        messages_history=[{"role": "user", "content": "(대화 시작)"}],
    )

    # Redis 에 assistant 메시지 기록 — 원문 저장 (LLM 재전송 시 맥락 유지 필수).
    sia_session.append_message(
        conversation_id=conv_id,
        role="assistant",
        content=opening,
    )

    # 파서로 body/choices/mode 분리. name_fallback 은 호출부(여기) 가 오버라이드.
    body, choices, mode = parse_sia_output(opening)
    if is_name_fallback_turn(
        user_has_korean_name=sia_llm._has_korean(user.get("name") or ""),
        resolved_name=None,   # 첫 턴은 아직 fallback 응답 수신 전
        turn_count=0,
    ):
        mode = "name_fallback"
        choices = []

    return StartResponse(
        conversation_id=conv_id,
        opening_message=body,
        turn_count=0,
        response_mode=mode,
        choices=choices,
    )


@router.post("/chat/message", response_model=MessageResponse)
def chat_message(
    body: MessageRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> MessageResponse:
    """유저 발화 → Sia 응답. 세션이 만료/없으면 410.

    Flow:
      1. Redis 세션 로드.
         - primary 없음 + backup 도 없음 → 410 (단순 미존재)
         - primary 없음 + backup 있음 (TTL 만료 첫 probe) → backup 을 DB flush
           (status="ended_by_timeout") + extraction 큐잉 + backup 삭제 → 410
      2. 유저 메시지 append (primary TTL 리셋, 24h backup 도 갱신)
      3. Haiku 4.5 호출 (+retry)
      4. assistant 메시지 append
      5. turn_count 한계 체크 — 50 도달 시 status="ending_soon"
      6. 파서로 body/choices/mode 분리. name_fallback 은 호출부가 오버라이드.
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    turn_before_user = 0   # name_fallback 판정 (user append 전 turn_count)
    state = sia_session.get_session(body.conversation_id)
    if state is None:
        # Primary 만료. Backup 에 있으면 첫 probe → DB flush.
        backup = sia_session.get_backup(body.conversation_id)
        if backup is not None and backup.get("user_id") == user["id"]:
            _flush_expired_conversation(db, backup, background_tasks)
            sia_session.delete_backup(body.conversation_id)
        elif backup is not None:
            # 다른 유저의 conversation — 조용히 무시 (유출 방지).
            logger.warning(
                "backup probe: user_id mismatch cid=%s",
                body.conversation_id,
            )
        raise HTTPException(
            status_code=410,
            detail={
                "message": "지금까지 나눈 대화를 정리했습니다.",
                "next": "extracting",
                "redirect": "/extracting",
            },
        )
    if state["user_id"] != user["id"]:
        raise HTTPException(403, "not your conversation")
    if state["status"] != "active":
        raise HTTPException(409, f"session not active: status={state['status']}")

    turn_before_user = int(state.get("turn_count", 0))

    # 1. 유저 메시지 append (turn_count 증가)
    state = sia_session.append_message(
        conversation_id=body.conversation_id,
        role="user",
        content=body.user_message,
    )
    if state is None:
        raise HTTPException(410, "session expired during write")

    # 2. Sia 응답 생성
    profile = get_profile(db, user["id"]) or {}
    system_prompt = sia_llm.build_system_prompt(
        user_name=_resolve_opening_user_name(user),
        resolved_name=state.get("resolved_name"),
        collected_fields=state.get("collected_fields") or {},
        missing_fields=state.get("missing_fields") or V2_REQUIRED_FIELDS,
        ig_feed_cache=state.get("ig_feed_cache"),
    )
    history = _build_messages_for_llm(state)
    assistant_text = sia_llm.call_sia_turn_with_retry(
        system_prompt=system_prompt,
        messages_history=history,
    )

    # 3. assistant 메시지 append — 원문 저장 (LLM 재전송 맥락 유지).
    state = sia_session.append_message(
        conversation_id=body.conversation_id,
        role="assistant",
        content=assistant_text,
    )

    # 4. turn_count 한계 체크 (§4-5 soft limit)
    from config import get_settings
    limit = get_settings().sia_session_max_turns
    status = "ending_soon" if state["turn_count"] >= limit else "active"

    # 5. 파서로 body/choices/mode 분리.
    msg_body, choices, mode = parse_sia_output(assistant_text)
    if is_name_fallback_turn(
        user_has_korean_name=sia_llm._has_korean(user.get("name") or ""),
        resolved_name=state.get("resolved_name"),
        turn_count=turn_before_user,
    ):
        mode = "name_fallback"
        choices = []

    return MessageResponse(
        conversation_id=body.conversation_id,
        assistant_message=msg_body,
        turn_count=state["turn_count"],
        status=status,
        response_mode=mode,
        choices=choices,
    )


@router.post("/chat/end", response_model=EndResponse)
def chat_end(
    body: EndRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> EndResponse:
    """명시 종료 (유저 "이만하면 됐어요" 버튼).

    Contract #3 atomic sequence:
      1. conversations INSERT (status="ended")
      2. Redis session DELETE
      3. Extraction 백그라운드 큐잉 (D4 구현, 지금은 placeholder)
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    state = sia_session.get_session(body.conversation_id)
    if state is None:
        raise HTTPException(410, "session expired or not found")
    if state["user_id"] != user["id"]:
        raise HTTPException(403, "not your conversation")

    # Redis messages → ConversationMessage 리스트 (Pydantic validation)
    raw_msgs = state.get("messages") or []
    try:
        messages = [ConversationMessage.model_validate(m) for m in raw_msgs]
    except Exception as e:
        logger.exception("invalid messages in Redis: cid=%s", body.conversation_id)
        raise HTTPException(500, f"session payload corrupt: {e}")

    # 1. DB INSERT status="ended"
    conv_service.create_ended_conversation(
        db,
        user_id=user["id"],
        conversation_id=body.conversation_id,
        messages=messages,
        turn_count=state.get("turn_count", 0),
        started_at_iso=state.get("created_at"),
    )
    db.commit()

    # 2. Redis session DELETE
    sia_session.delete_session(body.conversation_id)

    # 3. Extraction 백그라운드 큐잉 (D4 구현 완료)
    extraction_queued = True
    background_tasks.add_task(
        _run_extraction_job,
        conversation_id=body.conversation_id,
        user_id=user["id"],
    )

    return EndResponse(
        conversation_id=body.conversation_id,
        status="ended",
        messages_persisted=len(messages),
        extraction_queued=extraction_queued,
    )


# ─────────────────────────────────────────────
#  TTL Expiry Recovery — backup snapshot → DB flush (D5 Task 3)
# ─────────────────────────────────────────────

def _flush_expired_conversation(
    db,
    state: dict,
    background_tasks: BackgroundTasks,
) -> None:
    """Timeout 만료 세션을 DB 로 flush + extraction 큐잉.

    `/chat/end` 와 동일한 atomic sequence 를 재사용하되 status="ended_by_timeout"
    로 저장해 manual /chat/end 와 구분한다.

    손상된 backup (Pydantic validation 실패) 은 조용히 drop — 유저에게는 동일한
    410 응답이 가므로 UX 영향 없음. 운영자는 로그에서 식별.
    """
    raw_msgs = state.get("messages") or []
    try:
        messages = [ConversationMessage.model_validate(m) for m in raw_msgs]
    except Exception:
        logger.exception(
            "backup snapshot corrupt: cid=%s",
            state.get("conversation_id"),
        )
        return

    conv_service.create_ended_conversation(
        db,
        user_id=state["user_id"],
        conversation_id=state["conversation_id"],
        messages=messages,
        turn_count=state.get("turn_count", 0),
        started_at_iso=state.get("created_at"),
        status="ended_by_timeout",
    )
    db.commit()
    background_tasks.add_task(
        _run_extraction_job,
        conversation_id=state["conversation_id"],
        user_id=state["user_id"],
    )


# ─────────────────────────────────────────────
#  Background: Extraction job (D4)
# ─────────────────────────────────────────────

def _run_extraction_job(conversation_id: str, user_id: str) -> None:
    """FastAPI BackgroundTask 에서 실행되는 Sonnet 4.6 extraction.

    Flow (contract #3):
      1. DB 에서 conversation 로드 (status="ended")
      2. messages → Pydantic 파싱
      3. extraction.extract_structured_fields() 호출 (Sonnet 1회 + 재시도 1회)
      4-a. 성공: mark_extracted (status="extracted" + structured_fields merge +
           onboarding_completed=TRUE)
      4-b. 실패: mark_failed (status="failed", user_profiles 변경 없음)

    BackgroundTask 는 독립 DB session 필요 (request session 은 이미 close 됨).
    session 생성/종료 명시 관리.
    """
    from services import conversations as conv_svc
    from services import extraction
    from db import get_db

    db = get_db()
    if db is None:
        logger.error(
            "extraction job: DB unavailable cid=%s (conversation stays status=ended)",
            conversation_id,
        )
        return

    try:
        conv = conv_svc.get_conversation(db, conversation_id)
        if conv is None:
            logger.error(
                "extraction job: conversation not found cid=%s", conversation_id,
            )
            return

        raw_msgs = conv.get("messages") or []
        try:
            messages = [ConversationMessage.model_validate(m) for m in raw_msgs]
        except Exception as e:
            logger.exception(
                "extraction job: invalid messages cid=%s — %s",
                conversation_id, e,
            )
            conv_svc.mark_failed(
                db, conversation_id=conversation_id,
                reason=f"invalid messages in DB: {e}",
            )
            db.commit()
            return

        try:
            result = extraction.extract_structured_fields(messages)
        except extraction.ExtractionError as e:
            logger.exception(
                "extraction job: Sonnet failure cid=%s", conversation_id,
            )
            conv_svc.mark_failed(
                db, conversation_id=conversation_id,
                reason=f"extraction failed: {e}",
            )
            db.commit()
            return

        # Success path — conversations UPDATE + user_profiles merge + completed=TRUE
        conv_svc.mark_extracted(
            db,
            conversation_id=conversation_id,
            user_id=user_id,
            result=result,
        )
        db.commit()
        logger.info(
            "extraction job: success cid=%s fallback_needed=%s",
            conversation_id, result.fallback_needed,
        )
    except Exception:
        # 안전망 — 예외 버블업으로 BackgroundTask 조용히 죽는 거 방지
        logger.exception(
            "extraction job: unexpected error cid=%s", conversation_id,
        )
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass
