"""Sia conversation endpoints (v2 Priority 1 D3).

SPEC-ONBOARDING-V2 REQ-SIA-*.

Flow:
  POST /api/v1/sia/chat/start      session 생성 + 첫 Sia 메시지 (오프닝)
  POST /api/v1/sia/chat/message    유저 발화 수신 → Sia 응답 반환
  POST /api/v1/sia/chat/end        명시 종료 → DB INSERT (status="ended") + extraction 큐잉

Redis active 기간에는 DB write 없음 (contract #3).
Extraction 은 chat/end 또는 idle timeout 시점에 BackgroundTask 로 큐잉 (D4 구현).
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db_session, get_current_user
from schemas.user_profile import ConversationMessage, StructuredFields
from services import conversations as conv_service
from services import sia_llm, sia_session
from services.user_profiles import get_profile


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sia", tags=["sia"])


# ─────────────────────────────────────────────
#  Request / Response models
# ─────────────────────────────────────────────

class StartResponse(BaseModel):
    conversation_id: str
    opening_message: str
    turn_count: int = 0


class MessageRequest(BaseModel):
    conversation_id: str
    user_message: str = Field(min_length=1, max_length=1000)


class MessageResponse(BaseModel):
    conversation_id: str
    assistant_message: str
    turn_count: int
    status: str                         # active / ending_soon / closed


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

    # Redis 에 assistant 메시지 기록
    sia_session.append_message(
        conversation_id=conv_id,
        role="assistant",
        content=opening,
    )

    return StartResponse(
        conversation_id=conv_id,
        opening_message=opening,
        turn_count=0,
    )


@router.post("/chat/message", response_model=MessageResponse)
def chat_message(
    body: MessageRequest,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> MessageResponse:
    """유저 발화 → Sia 응답. 세션이 만료/없으면 410.

    Flow:
      1. Redis 세션 로드. 없으면 410 Gone (TTL expired 또는 미존재)
      2. 유저 메시지 append
      3. Haiku 4.5 호출 (+retry)
      4. assistant 메시지 append
      5. turn_count 한계 체크 — 50 도달 시 status="ending_soon"
    """
    if db is None:
        raise HTTPException(500, "DB unavailable")

    state = sia_session.get_session(body.conversation_id)
    if state is None:
        raise HTTPException(410, "session expired or not found")
    if state["user_id"] != user["id"]:
        raise HTTPException(403, "not your conversation")
    if state["status"] != "active":
        raise HTTPException(409, f"session not active: status={state['status']}")

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

    # 3. assistant 메시지 append
    state = sia_session.append_message(
        conversation_id=body.conversation_id,
        role="assistant",
        content=assistant_text,
    )

    # 4. turn_count 한계 체크 (§4-5 soft limit)
    from config import get_settings
    limit = get_settings().sia_session_max_turns
    status = "ending_soon" if state["turn_count"] >= limit else "active"

    return MessageResponse(
        conversation_id=body.conversation_id,
        assistant_message=assistant_text,
        turn_count=state["turn_count"],
        status=status,
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

    # 3. Extraction 백그라운드 큐잉 (placeholder — D4 구현)
    extraction_queued = True
    background_tasks.add_task(
        _extract_conversation_placeholder,
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
#  Background: Extraction placeholder (D4 구현 예정)
# ─────────────────────────────────────────────

def _extract_conversation_placeholder(conversation_id: str, user_id: str) -> None:
    """D4 에서 Sonnet 4.6 extraction 로 대체.

    현재는 로그만 찍고 no-op. conversations.status="ended" 인 상태로 남음.
    """
    logger.info(
        "TODO(D4): Sonnet extraction for cid=%s user_id=%s",
        conversation_id, user_id,
    )
