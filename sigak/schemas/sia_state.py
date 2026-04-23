"""Sia 대화 상태 스키마 (Phase H).

CLAUDE.md v2.0 + PHASE_H_DIRECTIVE §2.

페르소나 B-친밀형 + 메시지 단위 + 100% 주관식 전환 전용. Phase A-F 의
spectrum/turn 기반 state 는 폐기.

설계 원칙:
- dataclass 기반 (지시서 §2.1 확정). Pydantic 과 혼용 피함.
- Redis JSON 직렬화는 `to_dict()` / `from_dict()` 명시적 경로.
- MsgType enum 은 to_dict 에서 .value 로 내려가고 from_dict 에서 역매핑.
- 기존 sia_session.py 의 Redis dual-write 인프라는 재사용 (v4 래퍼 경유).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


# ─────────────────────────────────────────────
#  MsgType — 11개
# ─────────────────────────────────────────────

class MsgType(str, Enum):
    OPENING_DECLARATION = "opening_declaration"
    OBSERVATION = "observation"
    PROBE = "probe"
    EXTRACTION = "extraction"
    EMPATHY_MIRROR = "empathy_mirror"
    RECOGNITION = "recognition"
    CONFRONTATION = "confrontation"
    META_REBUTTAL = "meta_rebuttal"
    EVIDENCE_DEFENSE = "evidence_defense"
    DIAGNOSIS = "diagnosis"
    SOFT_WALKBACK = "soft_walkback"


# 그룹핑 (지시서 §1.1)
COLLECTION: frozenset[MsgType] = frozenset({
    MsgType.OBSERVATION, MsgType.PROBE, MsgType.EXTRACTION,
})
UNDERSTANDING: frozenset[MsgType] = frozenset({
    MsgType.EMPATHY_MIRROR, MsgType.RECOGNITION,
    MsgType.DIAGNOSIS, MsgType.SOFT_WALKBACK,
})
WHITESPACE: frozenset[MsgType] = frozenset({
    MsgType.OPENING_DECLARATION,
})
CONFRONT: frozenset[MsgType] = frozenset({
    MsgType.CONFRONTATION,
    MsgType.META_REBUTTAL,
    MsgType.EVIDENCE_DEFENSE,
})

# 비율 목표 (지시서 §1.2)
DIAGNOSIS_MIN_RATIO = 0.12
RECOGNITION_MIN_RATIO = 0.15
EMPATHY_MIRROR_MAX_RATIO = 0.15
SOFT_WALKBACK_MAX_RATIO = 0.08

# 질문 종결 원칙 (validator A-8, §1.3 표)
QUESTION_REQUIRED: frozenset[MsgType] = frozenset({
    MsgType.OBSERVATION, MsgType.PROBE, MsgType.EXTRACTION,
    MsgType.RECOGNITION, MsgType.CONFRONTATION,
    MsgType.META_REBUTTAL, MsgType.EVIDENCE_DEFENSE,
})
QUESTION_FORBIDDEN: frozenset[MsgType] = frozenset({
    MsgType.OPENING_DECLARATION, MsgType.EMPATHY_MIRROR,
    MsgType.DIAGNOSIS, MsgType.SOFT_WALKBACK,
})

# 하드코딩 타입 (Haiku 호출 없이 템플릿 + 해시 변형)
HARDCODED_TYPES: frozenset[MsgType] = frozenset({
    MsgType.OPENING_DECLARATION,
    MsgType.META_REBUTTAL,
    MsgType.EVIDENCE_DEFENSE,
    MsgType.SOFT_WALKBACK,
})

# Haiku 생성 타입 — 11 - 하드코딩 4 = 7개
HAIKU_TYPES: frozenset[MsgType] = frozenset({
    MsgType.OBSERVATION,
    MsgType.PROBE,
    MsgType.EXTRACTION,
    MsgType.EMPATHY_MIRROR,
    MsgType.RECOGNITION,
    MsgType.CONFRONTATION,
    MsgType.DIAGNOSIS,
})


# ─────────────────────────────────────────────
#  UserMessageFlags — 정규식 1단 추출 결과
# ─────────────────────────────────────────────

@dataclass
class UserMessageFlags:
    """유저 메시지 정규식 1단 추출 (services/sia_flag_extractor.py)."""
    has_concede: bool = False              # 맞아요 / 사실 / 맞긴 해요
    has_emotion_word: bool = False         # 부담 / 어색 / 힘들어서 / 속상
    emotion_word_raw: Optional[str] = None
    has_tt: bool = False                   # ㅜㅜ / ㅠㅠ
    has_explain_req: bool = False          # 무슨 얘기 / 뭔 소리
    has_meta_challenge: bool = False       # MBTI 같은 거 / AI 가 뭘 알아
    has_evidence_doubt: bool = False       # 근거 없잖아 / 어떻게 알아
    has_self_disclosure: bool = False      # 사실 저는 / 실은 / 원래
    is_defensive: bool = False             # 편해서 / 취향 / 그냥 / 잘 안 찍


def _flags_to_dict(f: UserMessageFlags) -> dict[str, Any]:
    return asdict(f)


def _flags_from_dict(d: dict[str, Any]) -> UserMessageFlags:
    return UserMessageFlags(**{
        k: d.get(k, UserMessageFlags.__dataclass_fields__[k].default)
        for k in UserMessageFlags.__dataclass_fields__
    })


# ─────────────────────────────────────────────
#  Turn (user / assistant)
# ─────────────────────────────────────────────

@dataclass
class UserTurn:
    text: str
    turn_idx: int
    flags: UserMessageFlags = field(default_factory=UserMessageFlags)


@dataclass
class AssistantTurn:
    text: str
    msg_type: MsgType
    turn_idx: int
    # 어미 카운트 (validator A-2 cross-turn 창)
    jangayo_count: int = 0
    yeyo_count: int = 0
    neyo_count: int = 0
    deoraguyo_count: int = 0
    # RECOGNITION 누적용 축 태깅
    observed_axes: list[str] = field(default_factory=list)


TurnUnion = UserTurn | AssistantTurn


def _user_turn_to_dict(t: UserTurn) -> dict[str, Any]:
    return {
        "role": "user",
        "text": t.text,
        "turn_idx": t.turn_idx,
        "flags": _flags_to_dict(t.flags),
    }


def _assistant_turn_to_dict(t: AssistantTurn) -> dict[str, Any]:
    return {
        "role": "assistant",
        "text": t.text,
        "msg_type": t.msg_type.value,
        "turn_idx": t.turn_idx,
        "jangayo_count": t.jangayo_count,
        "yeyo_count": t.yeyo_count,
        "neyo_count": t.neyo_count,
        "deoraguyo_count": t.deoraguyo_count,
        "observed_axes": list(t.observed_axes),
    }


def _turn_from_dict(d: dict[str, Any]) -> TurnUnion:
    role = d.get("role")
    if role == "user":
        return UserTurn(
            text=d["text"],
            turn_idx=int(d["turn_idx"]),
            flags=_flags_from_dict(d.get("flags") or {}),
        )
    if role == "assistant":
        return AssistantTurn(
            text=d["text"],
            msg_type=MsgType(d["msg_type"]),
            turn_idx=int(d["turn_idx"]),
            jangayo_count=int(d.get("jangayo_count", 0)),
            yeyo_count=int(d.get("yeyo_count", 0)),
            neyo_count=int(d.get("neyo_count", 0)),
            deoraguyo_count=int(d.get("deoraguyo_count", 0)),
            observed_axes=list(d.get("observed_axes") or []),
        )
    raise ValueError(f"invalid role in turn dict: {role!r}")


# ─────────────────────────────────────────────
#  ConversationState
# ─────────────────────────────────────────────

@dataclass
class ConversationState:
    """Phase H 대화 상태. sia_session_v4.py 가 Redis 와 동기화."""
    session_id: str
    user_id: str                               # 하드코딩 해시 시드
    user_name: str                             # 호명 ("만재" / "정세현")

    turns: list[TurnUnion] = field(default_factory=list)

    # 누적 카운터 (decide_next_message + validator 참조)
    observation_count: int = 0
    observations_since_recognition: int = 0
    collection_streak: int = 0

    # 세션 1회 제한 플래그
    meta_rebuttal_used: bool = False
    evidence_defense_used: bool = False

    # JSON 필드 수집 — 종료 판정용 (§10.3)
    collected_fields: dict[str, Any] = field(default_factory=dict)

    # 타입별 카운터 (비율 체크)
    type_counts: dict[MsgType, int] = field(default_factory=dict)

    # 세션 메타
    status: str = "active"                     # active | closed | ended_by_timeout
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    # ── Queries ──

    def assistant_turns(self) -> list[AssistantTurn]:
        return [t for t in self.turns if isinstance(t, AssistantTurn)]

    def user_turns(self) -> list[UserTurn]:
        return [t for t in self.turns if isinstance(t, UserTurn)]

    def last_k_assistant(self, k: int = 3) -> list[AssistantTurn]:
        return self.assistant_turns()[-k:]

    def last_user(self) -> Optional[UserTurn]:
        for t in reversed(self.turns):
            if isinstance(t, UserTurn):
                return t
        return None

    def last_assistant(self) -> Optional[AssistantTurn]:
        for t in reversed(self.turns):
            if isinstance(t, AssistantTurn):
                return t
        return None

    # ── A-2 cross-turn 비율 helpers ──

    @property
    def jangayo_window_count(self) -> int:
        """최근 3 메시지 창 ~잖아요 합계."""
        return sum(t.jangayo_count for t in self.last_k_assistant(3))

    @property
    def has_neyo_or_deoraguyo_in_window(self) -> bool:
        """최근 3창 ~네요/~더라구요 존재 여부."""
        return any(
            (t.neyo_count + t.deoraguyo_count) > 0
            for t in self.last_k_assistant(3)
        )

    def recent_assistant_drafts(self, n: int = 3) -> list[str]:
        """validator cross-turn 체크용."""
        return [t.text for t in self.last_k_assistant(n)]

    def type_distribution(self) -> dict[MsgType, int]:
        """현재 누적된 msg_type별 카운트 snapshot (validator v4 §5.2 sub-rule)."""
        return dict(self.type_counts)

    # ── Serialization ──

    def to_dict(self) -> dict[str, Any]:
        """Redis JSON 직렬화용."""
        serialized_turns: list[dict[str, Any]] = []
        for t in self.turns:
            if isinstance(t, UserTurn):
                serialized_turns.append(_user_turn_to_dict(t))
            elif isinstance(t, AssistantTurn):
                serialized_turns.append(_assistant_turn_to_dict(t))
            else:
                raise ValueError(f"unknown turn type: {type(t).__name__}")

        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "turns": serialized_turns,
            "observation_count": self.observation_count,
            "observations_since_recognition": self.observations_since_recognition,
            "collection_streak": self.collection_streak,
            "meta_rebuttal_used": self.meta_rebuttal_used,
            "evidence_defense_used": self.evidence_defense_used,
            "collected_fields": dict(self.collected_fields),
            "type_counts": {k.value: v for k, v in self.type_counts.items()},
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ConversationState":
        """Redis JSON 역직렬화."""
        turns = [_turn_from_dict(tt) for tt in (d.get("turns") or [])]
        type_counts_raw = d.get("type_counts") or {}
        type_counts: dict[MsgType, int] = {}
        for k, v in type_counts_raw.items():
            try:
                type_counts[MsgType(k)] = int(v)
            except (ValueError, TypeError):
                # unknown key → 스킵 (스키마 포워드 호환)
                continue

        return cls(
            session_id=d["session_id"],
            user_id=d["user_id"],
            user_name=d.get("user_name") or "",
            turns=turns,
            observation_count=int(d.get("observation_count", 0)),
            observations_since_recognition=int(
                d.get("observations_since_recognition", 0)
            ),
            collection_streak=int(d.get("collection_streak", 0)),
            meta_rebuttal_used=bool(d.get("meta_rebuttal_used", False)),
            evidence_defense_used=bool(d.get("evidence_defense_used", False)),
            collected_fields=dict(d.get("collected_fields") or {}),
            type_counts=type_counts,
            status=str(d.get("status") or "active"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
        )
