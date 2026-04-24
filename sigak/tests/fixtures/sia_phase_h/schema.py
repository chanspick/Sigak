"""Phase H fixture 공통 스키마 — 5종 드라이런 (만재/지은/준호/서연/도윤).

SPEC 출처: .moai/specs/SPEC-SIA/
  - 세션 #4 v2 §3.2 (만재), §4.2 (지은)
  - 세션 #6 v2 §7.2 (준호)
  - 세션 #7 §12.1 (서연), §12.2 (도윤)

각 fixture 는 dict 로 표현. 사람 친화적 + Python import 직접 로드 (PyYAML 의존성 없음).

Fixture 필드:
  id / name / archetype / session_length / source / profile / turns / expected / notes

turns[] 각 요소:
  role          — "assistant" | "user"
  text          — 메시지 원문 (스펙 fixture 그대로)
  msg_type      — MsgType (assistant 만 필수)
  is_first_turn — M1 결합 출력 (OBSERVATION 에만 True)
  is_combined   — EMPATHY 결합 출력 (secondary_type 동반)
  secondary_type — 결합 둘째 문장 타입
  confrontation_block — C1~C7
  range_mode    — "limit" | "reaffirm"
  exit_confirmed — RE_ENTRY V5 플래그
  apply_self_pr_prefix — A-13

expected:
  type_counts   — {MsgType: int} 누적 타입 분포
  management_expected — bool: 관리 3 타입 사용 여부
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from schemas.sia_state import MsgType, RangeMode


@dataclass
class AssistantSpec:
    """Assistant 턴 fixture 엔트리."""
    text: str
    msg_type: MsgType
    is_first_turn: bool = False
    is_combined: bool = False
    secondary_type: Optional[MsgType] = None
    tertiary_type: Optional[MsgType] = None    # 세션 #7 §1.5 3단 결합 (서연 M4)
    confrontation_block: Optional[str] = None
    range_mode: RangeMode = "limit"
    exit_confirmed: bool = False
    apply_self_pr_prefix: bool = False


@dataclass
class UserSpec:
    """User 턴 fixture 엔트리."""
    text: str


@dataclass
class FixtureProfile:
    handle: str
    summary: str
    defense_mode: str = ""


@dataclass
class FixtureExpected:
    """분포 + 구조 검증 메타."""
    type_counts: dict[MsgType, int] = field(default_factory=dict)
    # sub-rule 위반이 "허용된" 경우 (A-3 트리거 우선 시) — 경고로만 노출
    empathy_over_15_percent_allowed: bool = False
    diagnosis_min_satisfied: bool = True
    recognition_min_satisfied: bool = True


@dataclass
class Fixture:
    """드라이런 fixture 전체."""
    id: str
    name: str
    archetype: str
    session_length: int
    source: str
    profile: FixtureProfile
    turns: list[AssistantSpec | UserSpec]
    expected: FixtureExpected
    notes: list[str] = field(default_factory=list)

    def assistant_turns(self) -> list[AssistantSpec]:
        return [t for t in self.turns if isinstance(t, AssistantSpec)]

    def user_turns(self) -> list[UserSpec]:
        return [t for t in self.turns if isinstance(t, UserSpec)]
