"""Sia 대화 상태 스키마 (Phase H, 14 타입 확정판).

SPEC 출처: .moai/specs/SPEC-SIA/ 세션 #4 v2 + #5 v2 + #6 v2 + #7.

페르소나 B-친밀형 + 메시지 단위 + 100% 주관식. 14 타입 체계:
- 수집 버킷 (30%): OBSERVATION / PROBE / EXTRACTION
- 이해 버킷 (50%): EMPATHY_MIRROR / RECOGNITION / DIAGNOSIS / SOFT_WALKBACK
- 대결 버킷 (이해 내부): CONFRONTATION / META_REBUTTAL / EVIDENCE_DEFENSE
- 여백 버킷 (5-10%): OPENING_DECLARATION
- 관리 버킷 (0-15%, 트리거 기반): CHECK_IN / RE_ENTRY / RANGE_DISCLOSURE [세션 #6 v2 신규]

설계 원칙:
- dataclass 기반 (지시서 §2.1 확정). Pydantic 과 혼용 피함.
- Redis JSON 직렬화는 `to_dict()` / `from_dict()` 명시적 경로.
- MsgType enum 은 to_dict 에서 .value 로 내려가고 from_dict 에서 역매핑.
- 기존 sia_session.py 의 Redis dual-write 인프라는 재사용 (v4 래퍼 경유).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Literal, Optional


# ─────────────────────────────────────────────
#  MsgType — 14개 (세션 #6 v2 §6.1 확정)
# ─────────────────────────────────────────────

class MsgType(str, Enum):
    # 수집
    OBSERVATION = "observation"
    PROBE = "probe"
    EXTRACTION = "extraction"
    # 이해
    EMPATHY_MIRROR = "empathy_mirror"
    RECOGNITION = "recognition"
    DIAGNOSIS = "diagnosis"
    SOFT_WALKBACK = "soft_walkback"
    # 대결 (이해 버킷 내 섞임)
    CONFRONTATION = "confrontation"
    META_REBUTTAL = "meta_rebuttal"
    EVIDENCE_DEFENSE = "evidence_defense"
    # 여백
    OPENING_DECLARATION = "opening_declaration"
    # 관리 (세션 #6 v2 신규, 트리거 기반)
    CHECK_IN = "check_in"
    RE_ENTRY = "re_entry"
    RANGE_DISCLOSURE = "range_disclosure"


# 그룹핑 (세션 #6 v2 §6.1)
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
# 관리 버킷 (트리거 기반, 비율 강제 없음)
MANAGEMENT: frozenset[MsgType] = frozenset({
    MsgType.CHECK_IN, MsgType.RE_ENTRY, MsgType.RANGE_DISCLOSURE,
})

# 비율 목표 (세션 #4 v2 §2, 세션 #5 v2 §7.1-7.2 확정)
DIAGNOSIS_MIN_RATIO = 0.12
RECOGNITION_MIN_RATIO = 0.15
EMPATHY_MIRROR_MAX_RATIO = 0.15  # 가이드. A-3 트리거 강제 시 허용
SOFT_WALKBACK_MAX_RATIO = 0.08

# 질문 종결 원칙 (세션 #6 v2 §6.2)
# EMPATHY_MIRROR 기본 금지, 단 세션 #7 A-1 결합 출력 시 둘째/셋째 문장이 질문 허용
QUESTION_REQUIRED: frozenset[MsgType] = frozenset({
    MsgType.OBSERVATION, MsgType.PROBE, MsgType.EXTRACTION,
    MsgType.RECOGNITION, MsgType.CONFRONTATION,
    MsgType.META_REBUTTAL, MsgType.EVIDENCE_DEFENSE,
})
QUESTION_FORBIDDEN: frozenset[MsgType] = frozenset({
    MsgType.OPENING_DECLARATION, MsgType.EMPATHY_MIRROR,
    MsgType.DIAGNOSIS, MsgType.SOFT_WALKBACK,
    MsgType.CHECK_IN, MsgType.RE_ENTRY, MsgType.RANGE_DISCLOSURE,
})

# 하드코딩 타입 (Haiku 호출 없이 템플릿 + 해시 변형)
# 세션 #4 v2 §8 = 4 (OPENING / META_REBUTTAL / EVIDENCE_DEFENSE / SOFT_WALKBACK)
# 세션 #6 v2 §10 추가 = 3 (CHECK_IN / RE_ENTRY / RANGE_DISCLOSURE)
# 총 7 타입 × 변형 = 44 문구 (세션 #7 §9.3 확정)
HARDCODED_TYPES: frozenset[MsgType] = frozenset({
    MsgType.OPENING_DECLARATION,
    MsgType.META_REBUTTAL,
    MsgType.EVIDENCE_DEFENSE,
    MsgType.SOFT_WALKBACK,
    MsgType.CHECK_IN,
    MsgType.RE_ENTRY,
    MsgType.RANGE_DISCLOSURE,
})

# Haiku 생성 타입 — 14 - 하드코딩 7 = 7개 (변동 없음)
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
#  RANGE_DISCLOSURE 모드 (세션 #7 §1.6)
# ─────────────────────────────────────────────

RangeMode = Literal["limit", "reaffirm"]
"""RANGE_DISCLOSURE 한 타입 안에 mode 분기.

limit   — 기존 spec. 과몰입/관계 의존 대응. 거리 두기 + 자기 한정
reaffirm — 세션 #7 신규. 막막함/평가요청+막막함우세 시. 사업 존재 재선언

분기 기준은 sia_decision.decide_next_message 에서 처리.
"""

# 과몰입 심각도 (세션 #6 v2 §4.1)
OverattachmentSeverity = Literal["", "mild", "severe"]


# ─────────────────────────────────────────────
#  UserMessageFlags — 정규식 1단 추출 결과
# ─────────────────────────────────────────────

@dataclass
class UserMessageFlags:
    """유저 메시지 정규식 1단 추출 (services/sia_flag_extractor.py).

    페르소나 C 9 flag (extract_flags) + v4 turn flow 3 flag (extract_flags_v4).
    v4 flag 기본값 False — 페르소나 C 경로 회귀 0.
    """
    # 페르소나 C 9 flag
    has_concede: bool = False              # 맞아요 / 사실 / 맞긴 해요
    has_emotion_word: bool = False         # 부담 / 어색 / 힘들어서 / 속상
    emotion_word_raw: Optional[str] = None
    has_tt: bool = False                   # ㅜㅜ / ㅠㅠ
    has_explain_req: bool = False          # 무슨 얘기 / 뭔 소리
    has_meta_challenge: bool = False       # MBTI 같은 거 / AI 가 뭘 알아
    has_evidence_doubt: bool = False       # 근거 없잖아 / 어떻게 알아
    has_self_disclosure: bool = False      # 사실 저는 / 실은 / 원래
    is_defensive: bool = False             # 편해서 / 취향 / 그냥 / 잘 안 찍

    # v4 turn flow 3 flag (T3-norm / T5-B / T7-vault 분기)
    has_self_doubt: bool = False           # 못생 / 비교 / 부럽 → T3-norm
    has_uncertainty: bool = False          # 잘 모르겠 / 글쎄 / <20자 → T5-B
    vault_present: bool = False            # vault 1+ 건 → T7-vault


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
    """Phase H 대화 상태 (14 타입 확정판). sia_session_v4.py 가 Redis 와 동기화.

    SPEC 출처: 세션 #4 v2 + 세션 #6 v2 §8.2 + 세션 #7 §7.4.
    """
    session_id: str
    user_id: str                               # 하드코딩 해시 시드
    user_name: str                             # 호명 ("만재" / "정세현")

    turns: list[TurnUnion] = field(default_factory=list)

    # 누적 카운터 (decide_next_message + validator 참조)
    observation_count: int = 0
    observations_since_recognition: int = 0
    collection_streak: int = 0                 # 수집 타입 연속 수 (A-2 RECOGNITION 강제용)

    # 세션 1회 제한 플래그
    meta_rebuttal_used: bool = False
    evidence_defense_used: bool = False

    # JSON 필드 수집 — 종료 판정용
    #   (세션 #4 §10.3 + 본 cutover: coordinate delta 누적 flush 저장소)
    collected_fields: dict[str, Any] = field(default_factory=dict)

    # 타입별 카운터 (비율 체크)
    type_counts: dict[MsgType, int] = field(default_factory=dict)

    # ── 세션 #6 v2 §8.2: 실패 모드 대응 state ──
    trivial_streak: int = 0                    # A-9 단답 연속 카운터 (3 도달 → CHECK_IN 이양)
    axis_switch_required: bool = False         # A-9 D 경로 플래그 (수용부 + 축 전환)
    overattachment_severity: OverattachmentSeverity = ""  # A-11 경미/심각 분기
    overattachment_warned: bool = False        # A-11 동일 세션 중복 경고 방지

    # ── 세션 #7 §7.4: A-16 유저 명시 자기인지 추적 ──
    # 토픽 키 → 남은 턴 수. detect_user_disclaimer 가 set, decide 가 매 턴 decrement.
    user_disclaimer_memory: dict[str, int] = field(default_factory=dict)

    # ── 세션 #7 §5: A-13 자기 충만형 라포 prefix 카운터 ──
    self_pr_prefix_used: int = 0               # 세션당 1-2회 한정 (남발 시 가식)

    # ── 본 cutover 추가: 페르소나 B Vision 기반 대화 + 성별 분기 ──
    gender: Optional[str] = None               # "female" | "male" | None (온보딩 Step 0)
    ig_feed_cache: Optional[dict] = None       # Vision 분석 포함 IG 피드 snapshot

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
            # 세션 #6 v2 실패 모드
            "trivial_streak": self.trivial_streak,
            "axis_switch_required": self.axis_switch_required,
            "overattachment_severity": self.overattachment_severity,
            "overattachment_warned": self.overattachment_warned,
            # 세션 #7 A-16 / A-13
            "user_disclaimer_memory": dict(self.user_disclaimer_memory),
            "self_pr_prefix_used": self.self_pr_prefix_used,
            # 본 cutover — 페르소나 B Vision 기반
            "gender": self.gender,
            "ig_feed_cache": self.ig_feed_cache,
            # 메타
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ConversationState":
        """Redis JSON 역직렬화. 구 payload 는 기본값으로 fill."""
        turns = [_turn_from_dict(tt) for tt in (d.get("turns") or [])]
        type_counts_raw = d.get("type_counts") or {}
        type_counts: dict[MsgType, int] = {}
        for k, v in type_counts_raw.items():
            try:
                type_counts[MsgType(k)] = int(v)
            except (ValueError, TypeError):
                # unknown key → 스킵 (스키마 포워드 호환)
                continue

        # overattachment_severity 범위 검증 (fallback = "")
        sev_raw = d.get("overattachment_severity") or ""
        sev: OverattachmentSeverity = (
            sev_raw if sev_raw in ("", "mild", "severe") else ""
        )

        # user_disclaimer_memory — value 를 int 로 강제
        udm_raw = d.get("user_disclaimer_memory") or {}
        udm: dict[str, int] = {}
        if isinstance(udm_raw, dict):
            for k, v in udm_raw.items():
                try:
                    udm[str(k)] = int(v)
                except (ValueError, TypeError):
                    continue

        # gender 범위 검증 (fallback = None)
        gender_raw = d.get("gender")
        gender: Optional[str] = (
            gender_raw if gender_raw in ("female", "male") else None
        )

        # ig_feed_cache — dict 만 허용. 그 외는 None
        igc_raw = d.get("ig_feed_cache")
        ig_feed_cache: Optional[dict] = (
            dict(igc_raw) if isinstance(igc_raw, dict) else None
        )

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
            trivial_streak=int(d.get("trivial_streak", 0)),
            axis_switch_required=bool(d.get("axis_switch_required", False)),
            overattachment_severity=sev,
            overattachment_warned=bool(d.get("overattachment_warned", False)),
            user_disclaimer_memory=udm,
            self_pr_prefix_used=int(d.get("self_pr_prefix_used", 0)),
            gender=gender,
            ig_feed_cache=ig_feed_cache,
            status=str(d.get("status") or "active"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
        )
