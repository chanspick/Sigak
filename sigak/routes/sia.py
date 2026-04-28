"""Sia conversation endpoints — Phase H v4 cutover.

SPEC 출처: .moai/specs/SPEC-SIA/ 세션 #4 v2 + #6 v2 + #7 + SPEC-ONBOARDING-V2.

Flow:
  POST /api/v1/sia/chat/start      세션 생성 + M1 결합 출력 (OPENING + OBSERVATION)
  POST /api/v1/sia/chat/message    유저 발화 수신 → decide() → v4 렌더러 → 응답
  POST /api/v1/sia/chat/end        명시 종료 → DB INSERT (status="ended") + extraction 큐잉

v4 재배선 (STEP 2-G):
  - sia_session → sia_session_v4 (ConversationState JSON round-trip)
  - sia_llm.build_system_prompt → sia_prompts_v4.load_haiku_prompt + sia_hardcoded.render_hardcoded
  - parse_sia_output (choices[4] + mode) 제거 — 100% 주관식 (세션 #4 v2, 페르소나 B 원칙)
  - 응답 스키마에서 choices / response_mode 제거
  - Composition 플래그 (is_combined / secondary / block / range_mode / exit_confirmed /
    apply_self_pr_prefix) 를 Haiku 프롬프트 + validator 로 전달

Redis active 기간에는 DB write 없음 (contract #3). Extraction 은 chat/end 또는 TTL
만료 첫 probe 시 BackgroundTask 로 Sonnet 4.6 호출.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db_session, get_current_user
from schemas.sia_state import (
    HARDCODED_TYPES,
    AssistantTurn,
    ConversationState,
    MsgType,
    UserTurn,
)
from schemas.user_history import UserHistory
from schemas.user_profile import ConversationMessage
from services import conversations as conv_service
from services import sia_llm, sia_session_v4
from services import user_history
from services.sia_decision import (
    Composition,
    decide,
    update_state_from_user_turn,
)
from services.sia_flag_extractor import extract_flags
from services.sia_hardcoded import render_hardcoded
from services.sia_llm import _render_ig_summary
from services.sia_prompts_v4 import load_haiku_prompt
from services.sia_session import _backup_key, session_key  # Redis 키 재사용
from services.sia_validators_v4 import populate_turn_counts, validate
from services.user_data_vault import load_vault
from services.user_profiles import get_profile


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sia", tags=["sia"])


# ─────────────────────────────────────────────
#  Request / Response models (v4 — choices 제거)
# ─────────────────────────────────────────────

class StartResponse(BaseModel):
    conversation_id: str
    opening_message: str                # M1 결합 출력 (OPENING + OBSERVATION 1문장)
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
#  Helpers — state / message conversion
# ─────────────────────────────────────────────

def _resolve_user_name(user: dict, profile: Optional[dict]) -> str:
    """호명에 사용할 이름 — users.name 우선, 없으면 빈 문자열."""
    name = (user.get("name") or "").strip()
    if name:
        return name
    return ""


# 최종 상태 (safety net 발동 안 함) — Sia 가 곧장 대화 진입 가능
_IG_TERMINAL_STATUSES = {"success", "private", "skipped", "failed"}


def _ensure_ig_cache_ready(db, user_id: str, profile: dict) -> dict:
    """IG 수집 상태 + 24h 스냅샷 캐시 보장 (STEP 2 전환).

    정상 흐름 (cache fresh):
      status 최종 + ig_last_snapshot_at < 24h → no-op (기존 cache 사용).

    24h 초과 재스크랩:
      status 최종이어도 스냅샷 > 24h 면 동기 refresh → R2 새 디렉토리.
      R2 URL 이 CDN 만료 무관하게 영구 보존.

    Safety net (비정상):
      status in {None, 'pending', 'pending_vision'} + ig_handle → 동기 refresh.
      최대 ~45s 블로킹.
    """
    from services import user_profiles

    status = profile.get("ig_fetch_status")
    ig_handle = profile.get("ig_handle")

    if not ig_handle:
        return profile

    # 최종 상태 + 24h 캐시 hit → cache 그대로 사용
    if status in _IG_TERMINAL_STATUSES:
        if not user_profiles.should_refresh_ig_snapshot(db, user_id):
            return profile
        logger.info(
            "chat_start: IG snapshot > 24h — rescraping user=%s (status=%s)",
            user_id, status,
        )
    else:
        # pending / pending_vision / None — 백그라운드 미완
        logger.info(
            "chat_start safety net: sync IG refresh for user=%s (status=%s)",
            user_id, status,
        )

    try:
        user_profiles.refresh_ig_feed(db, user_id, force=True)
        db.commit()
        refreshed = user_profiles.get_profile(db, user_id)
        if refreshed is not None:
            return refreshed
    except Exception:
        logger.exception(
            "chat_start IG refresh failed for user=%s — proceeding without Vision",
            user_id,
        )
    return profile


def _history_for_haiku(state: ConversationState) -> list[dict]:
    """ConversationState.turns → Claude API messages history (role/content).

    첫 턴일 때는 dummy user prompt 삽입 (Claude API 첫 메시지 = user 필수).
    """
    out: list[dict] = []
    for t in state.turns:
        if isinstance(t, UserTurn):
            out.append({"role": "user", "content": t.text})
        elif isinstance(t, AssistantTurn):
            out.append({"role": "assistant", "content": t.text})
    if not out:
        out = [{"role": "user", "content": "(대화 시작)"}]
    return out


def _append_sia_history(
    db,
    *,
    user_id: str,
    conversation_id: str,
    state: "ConversationState",
    messages: list,
) -> None:
    """STEP 4 — user_history.conversations 에 head prepend.

    IG 스냅샷은 vault.ig_feed_cache 의 현재 스냅샷을 연결 (R2 URL + analysis).
    예외 전부 흡수 — 메인 persist 플로우 영향 금지.
    """
    try:
        from schemas.user_history import (
            ConversationHistoryEntry,
            HistoryIgSnapshot,
            HistoryMessage,
        )
        from services import user_profiles

        # 메시지 변환 — ConversationMessage → HistoryMessage
        hist_msgs: list[HistoryMessage] = []
        for m in (messages or []):
            role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else None)
            content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else None)
            if not role or content is None:
                continue
            if role not in ("user", "assistant", "system"):
                continue
            hist_msgs.append(HistoryMessage(
                role=role, content=str(content), msg_type=None,
            ))

        # IG 스냅샷 — vault.ig_feed_cache 에서 참조 (R2 URL 이면 영구, CDN 이면 TTL 있음)
        ig_snapshot = None
        try:
            profile = user_profiles.get_profile(db, user_id)
            cache = profile.get("ig_feed_cache") if profile else None
            if cache and cache.get("latest_posts"):
                posts = cache.get("latest_posts") or []
                photo_urls = [
                    p.get("display_url") for p in posts
                    if isinstance(p, dict) and p.get("display_url")
                ]
                ig_snapshot = HistoryIgSnapshot(
                    r2_dir=cache.get("r2_snapshot_dir") or "",
                    photo_r2_urls=photo_urls,
                    analysis=cache.get("analysis"),
                )
        except Exception:
            logger.exception("sia history: IG snapshot attach failed user=%s", user_id)

        # started_at 파싱
        try:
            started_at = datetime.fromisoformat(
                (state.created_at or "").replace("Z", "+00:00")
            )
        except (ValueError, TypeError, AttributeError):
            started_at = None

        entry = ConversationHistoryEntry(
            session_id=conversation_id,
            started_at=started_at,
            ended_at=datetime.now(timezone.utc),
            messages=hist_msgs,
            ig_snapshot=ig_snapshot,
        )
        user_history.append_history(
            db, user_id=user_id, category="conversations", entry=entry,
        )
    except Exception:
        logger.exception("append_sia_history failed user=%s", user_id)


def _state_to_persist_messages(state: ConversationState) -> list[ConversationMessage]:
    """ConversationState.turns → conversations.messages JSONB 리스트.

    ts 는 state.created_at 을 baseline 으로 턴 인덱스에 따라 약간 증가시켜 생성.
    (저장용 근사치 — 정확한 per-turn ts 는 schema 확장 없이 불가. MVP 로 충분.)
    """
    try:
        base = datetime.fromisoformat((state.created_at or "").replace("Z", "+00:00"))
    except (ValueError, TypeError):
        base = datetime.now(timezone.utc)

    msgs: list[ConversationMessage] = []
    for idx, t in enumerate(state.turns):
        ts = base.replace(microsecond=(idx * 1000) % 1_000_000)
        if isinstance(t, UserTurn):
            msgs.append(ConversationMessage(role="user", content=t.text, ts=ts))
        elif isinstance(t, AssistantTurn):
            msgs.append(ConversationMessage(role="assistant", content=t.text, ts=ts))
    return msgs


def _update_counters_for_assistant(
    state: ConversationState,
    msg_type: MsgType,
    composition: Composition,
) -> None:
    """AssistantTurn append 후 집계 카운터 업데이트.

    세션 #6 v2 §8.1 + 세션 #7 반영:
    - type_counts: primary_type += 1
    - observation_count: primary=OBSERVATION 또는 M1 secondary=OBSERVATION → +1
    - collection_streak: 수집 타입 (OBS/PROBE/EXT) → +1 / 그 외 → 0
    - observations_since_recognition: OBS → +1 / RECOG → 0
    - meta_rebuttal_used / evidence_defense_used: 세션 1회 플래그
    - self_pr_prefix_used: A-13 prefix 사용 시 +1
    """
    state.type_counts[msg_type] = state.type_counts.get(msg_type, 0) + 1

    # OBSERVATION 효과 카운트 — primary 또는 M1/EMPATHY 결합 secondary
    obs_delivered = (
        msg_type == MsgType.OBSERVATION
        or composition.secondary_type == MsgType.OBSERVATION
    )
    if obs_delivered:
        state.observation_count += 1
        state.observations_since_recognition += 1

    # 수집 버킷 연속 카운트
    if msg_type in {MsgType.OBSERVATION, MsgType.PROBE, MsgType.EXTRACTION}:
        state.collection_streak += 1
    else:
        state.collection_streak = 0

    # RECOGNITION 누적 시 since_recognition 리셋
    if msg_type == MsgType.RECOGNITION:
        state.observations_since_recognition = 0

    # 세션 1회 한정 플래그
    if msg_type == MsgType.META_REBUTTAL:
        state.meta_rebuttal_used = True
    if msg_type == MsgType.EVIDENCE_DEFENSE:
        state.evidence_defense_used = True

    # A-13 prefix 카운터
    if composition.apply_self_pr_prefix:
        state.self_pr_prefix_used += 1


def _load_vault_for_sia(
    db, user_id: str,
) -> tuple[Optional[UserHistory], Optional[list[str]]]:
    """Sia 재대화 vault 주입용 — UserHistory + user_original_phrases 추출.

    DB 부재 / vault row 없음 / 어떤 단계 실패도 None 반환 → caller 는
    "vault 없음 = 첫 진입 유저" 와 동일하게 회귀 0 처리.

    매 turn 호출 (단일 SELECT, 1-3ms). ConversationState string 캐싱은 v1.5 백로그.
    """
    try:
        vault = load_vault(db, user_id)
    except Exception:
        logger.exception("sia vault load failed user=%s — proceeding without", user_id)
        return None, None
    if vault is None:
        return None, None

    history = vault.user_history
    try:
        phrases = vault.get_user_taste_profile().user_original_phrases or None
    except Exception:
        logger.exception(
            "sia vault.get_user_taste_profile failed user=%s — phrases=None", user_id,
        )
        phrases = None
    return history, phrases


def _render_assistant_message(
    composition: Composition,
    state: ConversationState,
    *,
    history_context: str = "",
    vault_history: Optional[UserHistory] = None,
    user_phrases: Optional[list[str]] = None,
) -> str:
    """Composition → assistant 메시지 텍스트.

    HARDCODED_TYPES 는 sia_hardcoded.render_hardcoded, HAIKU_TYPES 는
    sia_prompts_v4.load_haiku_prompt + sia_llm.call_sia_turn_with_retry.

    M1 결합 출력 (OPENING + OBSERVATION) 은 OPENING 하드코딩 + OBSERVATION Haiku
    두 호출의 결과를 한 문자열로 합쳐서 반환.

    history_context: STEP 5i — chat_start 에서만 non-empty (이전 대화 맥락 markdown).
      first turn Haiku prompt 앞에 prepend.
    vault_history / user_phrases: 재대화 시 본인 누적 데이터 (4 기능) → Haiku
      `_build_context` 의 "## 본인 누적 데이터 (재대화 시)" 블록으로 주입.
    """
    msg_type = composition.primary_type

    # M1 결합 — OPENING 하드코딩 + secondary=OBSERVATION Haiku
    is_m1_combined = (
        msg_type == MsgType.OPENING_DECLARATION
        and composition.is_combined
        and composition.secondary_type == MsgType.OBSERVATION
    )
    if is_m1_combined:
        opening_text = render_hardcoded(MsgType.OPENING_DECLARATION, state)
        obs_text = _call_haiku(
            MsgType.OBSERVATION, state, composition,
            is_first_turn=True,
            history_context=history_context,
            vault_history=vault_history,
            user_phrases=user_phrases,
        )
        # M1 호명/행위 중복 방지 — Haiku 가 observation.md HARD 지시 무시 시 후처리
        obs_text = _strip_m1_meta_preamble(obs_text, state.user_name)
        return f"{opening_text} {obs_text}".strip()

    # HARDCODED 단독
    if msg_type in HARDCODED_TYPES:
        return render_hardcoded(
            msg_type, state,
            range_mode=composition.range_mode,
            exit_confirmed=composition.exit_confirmed,
            # user_meta_raw / observation_evidence / last_diagnosis / feed_count 은
            # 상위 orchestrator 가 필요 시 주입. v4 cutover 최소 스코프에선 빈값.
        )

    # HAIKU 단독 or EMPATHY 결합
    return _call_haiku(
        msg_type, state, composition,
        is_first_turn=False,
        history_context=history_context,
        vault_history=vault_history,
        user_phrases=user_phrases,
    )


# M1 결합 시 OBSERVATION 앞부분이 OPENING 의 meta 선언과 중복되는 경우 제거.
# 패턴 예시 (Haiku 실 출력):
#   "{name}님 피드 한번 봤어요. 포스트가 한 장인데..."
#   "{name}님 인스타 살펴봤어요. 최근 올리신..."
#   "피드를 보니 최근 5장이..."
# 목표: 구체 관찰 시작부만 남김.
_M1_META_PREAMBLE_TEMPLATE = (
    r"^(?P<name_prefix>{name}님\s+)?"
    r"(?P<target>피드|인스타|올리신\s+(?:것|사진|거|사진들))"
    r"[^.!?\n]*?"
    r"(?:봤어요|들여다봤어요|훑어봤어요|살펴봤어요|돌아봤어요|보니까?)"
    r"[.,]*\s*"
)


def _strip_m1_meta_preamble(obs_text: str, user_name: str) -> str:
    """M1 OBSERVATION 앞부분의 meta 선언 (피드/인스타 재-봤어요 류) 제거.

    Haiku 가 observation.md HARD 지시 준수 시 이 함수는 no-op.
    지시 불이행 시 band-aid 로 깨끗한 옵닝 결합 출력 보장.

    user_name 이 빈 문자열이면 name_prefix 부분 optional 로 매칭.
    """
    if not obs_text:
        return obs_text
    name = re.escape(user_name) if user_name else ""
    pattern = re.compile(
        _M1_META_PREAMBLE_TEMPLATE.format(name=name),
        flags=re.IGNORECASE,
    )
    stripped = pattern.sub("", obs_text, count=1).lstrip()
    return stripped or obs_text   # 전부 지워지면 원본 반환 (안전망)


# Hard reject 시 fallback 카피 — A-17/A-20 금지 어휘 회피 + 친구 톤.
_HARD_REJECT_FALLBACK = (
    "잠깐, 제가 생각을 다시 정리해봐야겠어요. 한 마디만 더 해주실래요?"
)


def _call_haiku(
    msg_type: MsgType,
    state: ConversationState,
    composition: Composition,
    *,
    is_first_turn: bool,
    max_reject_retries: int = 1,
    history_context: str = "",
    vault_history: Optional[UserHistory] = None,
    user_phrases: Optional[list[str]] = None,
) -> str:
    """load_haiku_prompt 조립 + Haiku 호출 + validator hard error 시 재시도.

    Hard reject 발생 시 (A-17 영업어휘 / A-20 추상칭찬 / A-18 300자+ / markdown) :
      1회 재시도 후에도 violate 하면 fallback 카피로 대체. Haiku 가 또 영업/추상
      찬사 뱉는 경우 유저에게 그걸 보여주는 것보다 짧은 fallback 이 안전.

    history_context: STEP 5i — 첫 턴 (is_first_turn=True) + non-empty 시
      prompt 앞에 이전 대화/분석 맥락 prepend.
    vault_history / user_phrases: load_haiku_prompt 로 forward — `_build_context`
      에서 "## 본인 누적 데이터 (재대화 시)" 블록 주입.
    """
    last_user = state.last_user()
    user_flags = last_user.flags if last_user else None

    vision_summary = _render_ig_summary(state.ig_feed_cache)

    prompt = load_haiku_prompt(
        msg_type,
        state,
        user_flags=user_flags,
        vision_summary=vision_summary,
        is_first_turn=is_first_turn,
        is_combined=composition.is_combined,
        secondary_type=composition.secondary_type,
        confrontation_block=composition.confrontation_block,
        apply_self_pr_prefix=composition.apply_self_pr_prefix,
        range_mode=composition.range_mode,
        vault_history=vault_history,
        user_phrases=user_phrases,
    )
    # STEP 5i — 첫 턴에만 history 맥락 prepend (cross-session)
    if is_first_turn and history_context:
        prompt = history_context + "---\n\n" + prompt
    history = _history_for_haiku(state)

    last_text = ""
    for attempt in range(max_reject_retries + 1):
        text = sia_llm.call_sia_turn_with_retry(
            system_prompt=prompt,
            messages_history=history,
        )
        last_text = text
        v = validate(
            text, msg_type, state=state,
            range_mode=composition.range_mode,
            confrontation_block=composition.confrontation_block,
            is_combined=composition.is_combined,
            exit_confirmed=composition.exit_confirmed,
        )
        # Hard reject 대상만 검사 (rhythm warning 등 soft 는 통과)
        hard_rejects = _filter_hard_rejects(v.errors)
        if not hard_rejects:
            return text
        logger.warning(
            "Haiku hard-reject attempt %d msg_type=%s errors=%s",
            attempt + 1, msg_type.value, hard_rejects,
        )

    # 재시도 전부 실패 → fallback
    logger.error(
        "Haiku hard-reject exhausted retries — fallback. last=%r",
        last_text[:120],
    )
    return _HARD_REJECT_FALLBACK


# Hard reject 대상 prefix. rhythm / A-2 cross-turn 등 soft warning 은 제외.
_HARD_REJECT_PREFIXES = (
    "A-17:", "A-18:", "A-20:", "마크다운",
)


def _filter_hard_rejects(errors: list[str]) -> list[str]:
    return [
        e for e in errors
        if any(e.startswith(p) for p in _HARD_REJECT_PREFIXES)
    ]


def _record_assistant_turn(
    state: ConversationState,
    text: str,
    composition: Composition,
) -> AssistantTurn:
    """AssistantTurn 생성 + 어미 카운트 populate + state.turns append + 집계 업데이트."""
    turn = AssistantTurn(
        text=text,
        msg_type=composition.primary_type,
        turn_idx=len(state.turns),
    )
    populate_turn_counts(turn)
    state.turns.append(turn)
    _update_counters_for_assistant(state, composition.primary_type, composition)
    return turn


# ─────────────────────────────────────────────
#  v4 Maintenance Gate (Phase 1, 2026-04-28)
# ─────────────────────────────────────────────

def _maintenance_gate() -> None:
    """SIA_V4_MAINTENANCE=true 시 /sia/chat/* 엔드포인트 503 차단.

    페르소나 C → v4 "미감 비서" 재작성 진입 (베타 hotfix Final).
    v4 완성 (Phase 7) 후 SIA_V4_MAINTENANCE=false 로 복귀.

    Railway env override: SIA_V4_MAINTENANCE="true"/"false".
    """
    from config import get_settings
    if get_settings().sia_v4_maintenance:
        raise HTTPException(
            status_code=503,
            detail="Sia 점검 중입니다. 잠시 후 다시 시도해주세요.",
        )


# ─────────────────────────────────────────────
#  Endpoints
# ─────────────────────────────────────────────

@router.post("/chat/start", response_model=StartResponse)
def chat_start(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> StartResponse:
    """신규 conversation 생성 + Sia 오프닝 (M1 결합 출력).

    - Redis 세션 생성 (primary 5m sliding + backup 24h, v4 shape)
    - user_profile 에서 gender / ig_feed_cache 주입
    - decide(state) → M1 결합 Composition
    - OPENING 하드코딩 + OBSERVATION Haiku 합쳐서 한 메시지 전송
    """
    _maintenance_gate()
    if db is None:
        raise HTTPException(500, "DB unavailable")

    profile = get_profile(db, user["id"])
    if profile is None:
        raise HTTPException(
            409,
            "user_profile not found — Step 0 폼 제출 먼저 완료해 주십시오.",
        )

    # IG wiring safety net (STEP IG-Wiring Q2):
    #   정상 경로: /onboarding/essentials 직후 BackgroundTask 가 Apify+Vision 돌리고
    #             프론트가 /ig-status 폴링 완료 후에만 chat/start 호출.
    #   safety net: 프론트가 폴링 스킵하고 chat/start 직진한 경우만 보호.
    #               ig_handle 있고 최종 상태 아니면 동기 재시도 (45s 감수).
    profile = _ensure_ig_cache_ready(db, user["id"], profile)

    conv_id = uuid.uuid4().hex
    user_name = _resolve_user_name(user, profile)

    state = sia_session_v4.create_conversation_state(
        session_id=conv_id,
        user_id=user["id"],
        user_name=user_name,
    )
    state.gender = profile.get("gender") if profile.get("gender") in ("female", "male") else None
    state.ig_feed_cache = profile.get("ig_feed_cache")

    composition = decide(state)
    if composition.primary_type != MsgType.OPENING_DECLARATION:
        # decide() 가 첫 턴에서 M1 결합을 보장하는데, 다른 타입이 나오면 로직 버그.
        logger.error(
            "chat_start: decide returned %s instead of OPENING_DECLARATION",
            composition.primary_type,
        )

    # STEP 5i — 이전 대화/분석 맥락 주입 (cross-session, markdown prepend)
    history_context = ""
    try:
        from services.history_injector import build_history_context
        history_context = build_history_context(
            db, user["id"],
            include=[
                "conversations", "aspiration_analyses", "best_shot_sessions",
                "verdict_sessions", "pi_history",
            ],
            max_per_type=1,
        )
    except Exception:
        logger.exception("chat_start: history_injector failed user=%s", user["id"])

    # 재대화 vault 주입 (4 기능 누적 데이터 + user_original_phrases) → Haiku
    # _build_context "## 본인 누적 데이터 (재대화 시)" 블록.
    vault_history, user_phrases = _load_vault_for_sia(db, user["id"])

    opening_message = _render_assistant_message(
        composition, state,
        history_context=history_context,
        vault_history=vault_history,
        user_phrases=user_phrases,
    )
    _record_assistant_turn(state, opening_message, composition)
    sia_session_v4.save_conversation_state(state)

    return StartResponse(
        conversation_id=conv_id,
        opening_message=opening_message,
        turn_count=0,
    )


@router.post("/chat/message", response_model=MessageResponse)
def chat_message(
    body: MessageRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> MessageResponse:
    """유저 발화 → Sia 응답 (v4).

    Flow:
      1. Redis primary load. 없으면 backup probe → flush or 410.
      2. UserTurn append (flags 추출) + state 업데이트 (A-9 / A-16 memory).
      3. decide(state) → Composition.
      4. Assistant message 렌더 (HARDCODED or HAIKU).
      5. validate() — 위반 시 경고 로그만, 본문 유지.
      6. AssistantTurn append + 집계 갱신.
      7. save_conversation_state (primary+backup dual-write).
    """
    _maintenance_gate()
    if db is None:
        raise HTTPException(500, "DB unavailable")

    state = sia_session_v4.load_conversation_state(body.conversation_id)
    if state is None:
        backup = sia_session_v4.get_backup_state(body.conversation_id)
        if backup is not None and backup.user_id == user["id"]:
            _flush_expired_conversation(db, backup, background_tasks)
            sia_session_v4.delete_conversation_state(body.conversation_id)
        elif backup is not None:
            logger.warning(
                "backup probe: user_id mismatch cid=%s", body.conversation_id,
            )
        raise HTTPException(
            status_code=410,
            detail={
                "message": "지금까지 나눈 대화를 정리했습니다.",
                "next": "extracting",
                "redirect": "/extracting",
            },
        )

    if state.user_id != user["id"]:
        raise HTTPException(403, "not your conversation")
    if state.status != "active":
        raise HTTPException(409, f"session not active: status={state.status}")

    # 1. UserTurn append + 상태 업데이트
    user_flags = extract_flags(body.user_message)
    state.turns.append(UserTurn(
        text=body.user_message,
        turn_idx=len(state.turns),
        flags=user_flags,
    ))
    update_state_from_user_turn(state, body.user_message)

    # 2. 의사결정
    composition = decide(state)
    msg_type = composition.primary_type

    # 재대화 vault 주입 — chat_start 와 동일 entry. 매 turn load (단일 SELECT, 1-3ms).
    vault_history, user_phrases = _load_vault_for_sia(db, user["id"])

    # 3. 응답 렌더
    assistant_text = _render_assistant_message(
        composition, state,
        vault_history=vault_history,
        user_phrases=user_phrases,
    )

    # 4. Validator — 경고만 (STEP 2-G 스코프: 파이프라인 개통 우선)
    v = validate(
        assistant_text, msg_type, state=state,
        range_mode=composition.range_mode,
        confrontation_block=composition.confrontation_block,
        is_combined=composition.is_combined,
        exit_confirmed=composition.exit_confirmed,
    )
    if v.errors:
        logger.warning(
            "sia validate errors cid=%s type=%s errs=%s",
            body.conversation_id, msg_type.value, v.errors,
        )
    if v.warnings:
        logger.info(
            "sia validate warnings cid=%s: %s",
            body.conversation_id, v.warnings,
        )

    # 5. AssistantTurn append + 집계
    _record_assistant_turn(state, assistant_text, composition)
    sia_session_v4.save_conversation_state(state)

    # 6. 세션 한계 체크
    from config import get_settings
    limit = get_settings().sia_session_max_turns
    turn_count = len(state.turns) // 2  # user+assistant 왕복 기준
    status = "ending_soon" if turn_count >= limit else "active"

    return MessageResponse(
        conversation_id=body.conversation_id,
        assistant_message=assistant_text,
        turn_count=turn_count,
        status=status,
    )


@router.post("/chat/end", response_model=EndResponse)
def chat_end(
    body: EndRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> EndResponse:
    """명시 종료 — conversations INSERT (status="ended") + Sonnet extraction 큐잉."""
    _maintenance_gate()
    if db is None:
        raise HTTPException(500, "DB unavailable")

    state = sia_session_v4.load_conversation_state(body.conversation_id)
    if state is None:
        raise HTTPException(410, "session expired or not found")
    if state.user_id != user["id"]:
        raise HTTPException(403, "not your conversation")

    messages = _state_to_persist_messages(state)

    conv_service.create_ended_conversation(
        db,
        user_id=user["id"],
        conversation_id=body.conversation_id,
        messages=messages,
        turn_count=len(state.turns),
        started_at_iso=state.created_at,
    )
    # STEP 4 — user_history.conversations append (IG 스냅샷 snapshot 연결)
    _append_sia_history(
        db,
        user_id=user["id"],
        conversation_id=body.conversation_id,
        state=state,
        messages=messages,
    )
    db.commit()

    sia_session_v4.delete_conversation_state(body.conversation_id)

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
#  TTL expiry recovery
# ─────────────────────────────────────────────

def _flush_expired_conversation(
    db,
    state: ConversationState,
    background_tasks: BackgroundTasks,
) -> None:
    """Backup 스냅샷을 DB (status="ended_by_timeout") 로 flush + extraction 큐잉."""
    try:
        messages = _state_to_persist_messages(state)
    except Exception:
        logger.exception(
            "backup snapshot corrupt: cid=%s", state.session_id,
        )
        return

    conv_service.create_ended_conversation(
        db,
        user_id=state.user_id,
        conversation_id=state.session_id,
        messages=messages,
        turn_count=len(state.turns),
        started_at_iso=state.created_at,
        status="ended_by_timeout",
    )
    _append_sia_history(
        db,
        user_id=state.user_id,
        conversation_id=state.session_id,
        state=state,
        messages=messages,
    )
    db.commit()
    background_tasks.add_task(
        _run_extraction_job,
        conversation_id=state.session_id,
        user_id=state.user_id,
    )


# ─────────────────────────────────────────────
#  Background: Sonnet 4.6 extraction (STEP 2-G: 기존 경로 유지)
# ─────────────────────────────────────────────

def _run_extraction_job(conversation_id: str, user_id: str) -> None:
    """chat/end 또는 timeout flush 후 BackgroundTask — Sonnet 4.6 extraction.

    STEP 2-G 스코프: 기존 D4 경로 유지 (structured_fields 8 필드 추출 + merge +
    onboarding_completed TRUE). Haiku 축 delta 누적 flush 는 Phase I 로 이월.
    """
    from services import conversations as conv_svc
    from services import extraction
    from db import get_db

    db = get_db()
    if db is None:
        logger.error(
            "extraction job: DB unavailable cid=%s", conversation_id,
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
