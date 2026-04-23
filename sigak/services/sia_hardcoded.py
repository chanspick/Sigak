"""Sia 하드코딩 메시지 템플릿 (Phase H4).

PHASE_H_DIRECTIVE §6 / HARDCODED_TYPES.

Haiku 호출 없이 결정적 해시로 변형 선택. 4 타입 × 5 변형 = 20 템플릿.
각 템플릿은 validator v4 통과 (질문 종결 규칙 / A-1 금지 어미 / 60자 절 한도).

선택 시드: sha256("{user_id}:{msg_type}:{turn_idx}") → index % 5

Public API:
  render_hardcoded(msg_type, state) -> str
  pick_variant_index(user_id, msg_type, turn_idx, n) -> int
"""
from __future__ import annotations

import hashlib

from schemas.sia_state import (
    HARDCODED_TYPES,
    ConversationState,
    MsgType,
)


# ─────────────────────────────────────────────
#  Templates (페르소나 B 친밀형)
# ─────────────────────────────────────────────

# OPENING_DECLARATION — QUESTION_FORBIDDEN. 근거 선언 + 초대.
_OPENING_VARIANTS: tuple[str, ...] = (
    "{user_name}님 피드를 처음 열자마자 같은 앵글이 반복되시더라구요. 오늘은 그 결부터 같이 짚어봐요.",
    "{user_name}님 피드 상단 다섯 장이 색온도까지 겹치시더라구요. 여기서 시작해봐요.",
    "{user_name}님 사진 속 자세가 매번 비슷하신가봐요. 오늘은 그게 어디서 오는지 살펴봐요.",
    "{user_name}님 피드에 빈 공간이 자주 남아있으시더라구요. 그 여백부터 이야기해봐요.",
    "{user_name}님 피드의 톤이 꽤 일관되시더라구요. 오늘은 이 일관성부터 먼저 열어봐요.",
)

# META_REBUTTAL — QUESTION_REQUIRED. Sia 정체성 방어.
_META_REBUTTAL_VARIANTS: tuple[str, ...] = (
    "Sia는 이미지만 보는 친구예요. 말씀 없어도 이 정도는 드러나는 게 이상하세요?",
    "MBTI 같은 카테고리엔 관심 없어요. 지금 읽는 건 {user_name}님 피드 결이에요. 어디가 억지로 느껴지세요?",
    "AI라고 한 묶음으로 보진 마세요. 저는 그냥 반복된 사진을 읽어드렸어요. 이상한 부분이 있으셨어요?",
    "챗봇이라고 부르시니 조금 억울해져요. 근거는 방금 {user_name}님 피드에 있었어요. 어떤 부분이 걸리세요?",
    "너 뭔데라고 느끼시는 거 이해해요. 그래도 반복된 구도는 {user_name}님 피드 그대로예요. 더 설명드릴까요?",
)

# EVIDENCE_DEFENSE — QUESTION_REQUIRED. 구체 근거 제시.
_EVIDENCE_DEFENSE_VARIANTS: tuple[str, ...] = (
    "피드 3번째 이후 흰 벽 배경이 두 번 반복돼요. 이게 우연이신 건 아니시죠?",
    "{user_name}님 피드에 검은색 상의 비율이 60% 넘어요. 이건 제 추측만 아니에요. 어떻게 보세요?",
    "최근 5장 중 4장이 광각 앵글이시더라구요. 같은 패턴 반복은 취향이 있어서 아닐까요?",
    "피드 상단 세 장의 색상 톤이 완전히 겹쳐요. 이 반복을 우연이라고만 보기엔 수가 많으시죠?",
    "근거 없어 보이실 수 있는데, 사진 속 구도만 7번 이상 겹쳐요. 억지라고만 하시기엔 수가 많지 않으세요?",
)

# SOFT_WALKBACK — QUESTION_FORBIDDEN. 완화 + 제자리로 초대.
_SOFT_WALKBACK_VARIANTS: tuple[str, ...] = (
    "방금은 좀 세게 들렸겠다 싶어요. 한 단계 내려서 다시 말씀드려봐요.",
    "제가 한 줄에 너무 눌러 담았어요. {user_name}님 결에 맞춰 다시 천천히 짚어봐요.",
    "단정처럼 들리셨다면 문장을 깎아드릴게요. 지금부터는 살짝 결 풀면서 가봐요.",
    "조금 과했나 싶어 한 발 물러나 이야기해볼게요. 결은 그대로 두고 표현만 고쳐봐요.",
    "방금 한 말이 벽처럼 느껴졌을까 봐 조심스러워요. 그 벽을 낮춰서 다시 다가가봐요.",
)


TEMPLATES: dict[MsgType, tuple[str, ...]] = {
    MsgType.OPENING_DECLARATION: _OPENING_VARIANTS,
    MsgType.META_REBUTTAL: _META_REBUTTAL_VARIANTS,
    MsgType.EVIDENCE_DEFENSE: _EVIDENCE_DEFENSE_VARIANTS,
    MsgType.SOFT_WALKBACK: _SOFT_WALKBACK_VARIANTS,
}


# ─────────────────────────────────────────────
#  Public
# ─────────────────────────────────────────────

def pick_variant_index(
    user_id: str, msg_type: MsgType, turn_idx: int, n: int,
) -> int:
    """결정적 해시 — 같은 (user_id, msg_type, turn_idx) 는 같은 index."""
    if n <= 0:
        raise ValueError("variant count must be > 0")
    key = f"{user_id}:{msg_type.value}:{turn_idx}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    seed = int.from_bytes(digest[:4], "big")
    return seed % n


def render_hardcoded(msg_type: MsgType, state: ConversationState) -> str:
    """HARDCODED_TYPES 에 해당하는 메시지 결정적 생성.

    Parameters
    ----------
    msg_type : HARDCODED_TYPES 중 하나. 아니면 ValueError.
    state : user_id/user_name + 현재 assistant turns 수 추출에 사용.
    """
    if msg_type not in HARDCODED_TYPES:
        raise ValueError(f"{msg_type.value} is not hardcoded; use Haiku prompt")
    variants = TEMPLATES[msg_type]
    turn_idx = len(state.assistant_turns())
    idx = pick_variant_index(state.user_id, msg_type, turn_idx, len(variants))
    return variants[idx].format(user_name=state.user_name)
