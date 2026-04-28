"""Sia v4 슬롯 렌더링 + 한국어 디버그 (2026-04-28).

11 turn (T1-T11) 분기 4건 (T2/T3/T5/T7) 템플릿 + 사용자 발화 슬롯 동적 치환.

슬롯 종류:
  - 원어 / 핵심 단어        — 직전 사용자 발화 (조사 제거)
  - 추구미 단어 / T2-T3 단어 — 첫 사용자 응답 단어 (조사 제거)
  - 관찰 1조각 / 관찰        — IgFeedAnalysis.signature_observations[0]
  - T7 발화                  — state.user_turns()[6] 인용 (T8/T10/T11 사용)
  - T9 장면                  — state.user_turns()[8] 인용 (T10/T11 사용)
  - vault 발화               — UserHistory.user_original_phrases[0] 인용

설계 원칙:
- 한국어 조사 제거 (긴 것부터 매칭) — LLM 슬롯 엉킴 방지
- 사용자 발화 인용 ('...' wrap) — T7/T9/vault 발화 명확화
- 슬롯 누락 시 빈 문자열 또는 fallback (UI 깨짐 방지)
- vault 데이터 명시적 파라미터 (state monkeypatch X)

Public API:
  strip_korean_particles(text) -> str
  quote_user_phrase(text) -> str
  render_slot(slot_name, state, *, vault_history, user_phrases) -> str
  render_v4_template(turn_id, state, *, vault_history, user_phrases) -> str
"""
from __future__ import annotations

import re
from typing import Optional

from schemas.sia_state import ConversationState, UserTurn
from schemas.user_history import UserHistory


# ─────────────────────────────────────────────
#  한국어 조사 (긴 것부터 매칭)
# ─────────────────────────────────────────────

_KOREAN_PARTICLES = [
    "이에요", "예요", "에요", "이고요", "고요", "이요", "요",
    "을", "를", "이", "가", "은", "는", "에", "의", "도", "만",
    "한테", "에게", "께", "와", "과", "랑", "이랑",
]


def strip_korean_particles(text: str) -> str:
    """사용자 발화 끝 조사 제거 → 명사구 추출.

    긴 조사부터 매칭 (예요 vs 요). 조사 1개만 제거 (다중 조사 안 챔).
    빈 문자열/None → 빈 문자열 반환.
    """
    text = (text or "").strip()
    if not text:
        return ""
    for particle in sorted(_KOREAN_PARTICLES, key=len, reverse=True):
        if text.endswith(particle):
            text = text[: -len(particle)].strip()
            break
    return text


def quote_user_phrase(text: str) -> str:
    """사용자 발화 인용 — '<조사 제거된 phrase>' 형태.

    T7/T9/vault 슬롯 사용. 빈 문자열이면 빈 문자열 반환 (인용 안 함).
    """
    cleaned = strip_korean_particles(text)
    if not cleaned:
        return ""
    return f"'{cleaned}'"


# ─────────────────────────────────────────────
#  Turn 템플릿 (T1-T11, base.md 정합)
# ─────────────────────────────────────────────

_TURN_TEMPLATES: dict[str, str] = {
    "T1": (
        "안녕하세요 {user}님, Sia예요.\n"
        "첫 만남이라 천천히 시작할게요.\n"
        "오늘은 두 개 같이 봐요. 추구미랑 지금 피드.\n"
        "되고 싶은 모습부터 들려주세요."
    ),
    "T2-A": (
        "[원어], 좋네요.\n"
        "그 [원어] 하면 딱 떠오르는 사람이 있어요? 연예인이어도 좋고, 주변 사람이어도 좋아요.\n"
        "아니면 요즘 보면서 '이거다' 싶었던 사진이나 장면 있어요?"
    ),
    "T2-C": (
        "좀 더 듣고 싶어요.\n"
        "방금 말씀하신 [핵심 단어] —\n"
        "그거 좀 풀어주세요.\n"
        "[핵심 단어] 하면 딱 떠오르는 사람이 있어요? 연예인이어도 좋고, 주변 사람이어도 좋아요.\n"
        "아니면 요즘 보면서 '이거다' 싶었던 사진이나 장면 있어요?"
    ),
    "T3-base": (
        "좋아요. 이제 그림이 그려져요.\n"
        "{user}님 추구미에서 제일 중요한 한 가지 꼽으면 뭐예요?"
    ),
    "T3-norm": (
        "그런 마음 들 수 있어요. 누구나 한 번씩 그래요.\n"
        "{user}님 추구미에서 제일 중요한 한 가지 꼽으면 뭐예요?"
    ),
    "T4": (
        "이제 본인 피드 한 번 떠올려보시고요.\n"
        "지금 추구미를 잘 따라가고 있어요?"
    ),
    "T5-A": (
        "[원어] 그러시구나.\n"
        "어떤 부분에서 제일 그렇게 느끼세요?\n"
        "듣다 보니 저도 살짝 걸리는 포인트 있긴 한데,\n"
        "그건 이 얘기부터 듣고 말할게요."
    ),
    "T5-B": (
        "비슷한데 확신은 없으시구나.\n"
        "그 '잘 모르겠다'가 어디서 와요?\n"
        "색이에요, 분위기예요, 아니면 다른 거예요?"
    ),
    "T6": (
        "{user}님 추구미는 [추구미 단어]인데,\n"
        "지금 피드는 제가 보기엔 [관찰 1조각] 쪽이에요.\n"
        "본인 눈에는 둘이 어때요? 딱 맞아요, 아니면 좀 어긋나요?"
    ),
    "T7-base": (
        "처음에 [T2-T3 단어] 얘기하셨잖아요.\n"
        "지금 피드 [관찰] 쪽이랑 나란히 놓고 보면,\n"
        "{user}님은 어디부터 손대고 싶어요?"
    ),
    "T7-vault": (
        "근데 지난번에도 [vault 발화] 비슷한 얘기 하셨거든요.\n"
        "처음에 [T2-T3 단어]랑 그때 얘기 결국 같은 축이에요.\n"
        "이 안에서 어디부터 손대고 싶어요?"
    ),
    "T8": (
        "정리하면,\n"
        "추구미 [추구미 단어], 지금 피드 [관찰].\n"
        "방금 나온 [T7 발화]는 딱 {user}님 스타일이에요."
    ),
    "T9": (
        "지금 얘기 듣다 보면,\n"
        "{user}님 머릿속에 어떤 화면 떠올라요?\n"
        "'이렇게 돼 있으면 좋겠다' 한 장면만 골라보자면?"
    ),
    "T10": (
        "처음에 [T2-T3 단어] 얘기하셨고,\n"
        "방금 [T9 장면]까지 그려주셨잖아요.\n"
        "오늘은 일단 그 두 개만 우리 사이 암호처럼 들고 있어도 좋을 것 같아요."
    ),
    "T11": (
        "{user}님, 오늘 얘기 재밌었어요.\n"
        "나중에 피드 바꾸고 싶을 때,\n"
        "방금 잡은 [T9 장면]부터 슬쩍 떠올려보셔도 좋을 것 같아요.\n"
        "\n"
        "Sia는 언제나 {user}님의 미감 비서로 남아있을게요.\n"
        "하고 싶은 얘기 있으면 언제든 또 찾아오세요."
    ),
}


# 기본 관찰 fallback (signature_observations 미생성 시)
_DEFAULT_OBSERVATION = "톤 정돈된 분위기"


# ─────────────────────────────────────────────
#  Slot rendering
# ─────────────────────────────────────────────

def render_slot(
    slot_name: str,
    state: ConversationState,
    *,
    vault_history: Optional[UserHistory] = None,
    user_phrases: Optional[list[str]] = None,
) -> str:
    """슬롯 이름 → 사용자 발화/관찰/vault 기반 동적 값.

    Parameters
    ----------
    slot_name : "원어" / "핵심 단어" / "추구미 단어" / "T2-T3 단어" /
                "관찰 1조각" / "관찰" / "T7 발화" / "T9 장면" / "vault 발화"
    state : ConversationState — 누적 turn 참조.
    vault_history : 선택. UserDataVault.user_history (재대화 시).
    user_phrases : 선택. UserTasteProfile.user_original_phrases.
                   user_phrases 가 vault_history 보다 우선.

    Returns
    -------
    str : 슬롯 값 (조사 제거 / 인용 처리 완료). 매핑 안 되면 빈 문자열 또는 fallback.

    Raises
    ------
    ValueError : 알 수 없는 slot_name.
    """
    if slot_name in ("원어", "핵심 단어"):
        last_user = state.last_user()
        return strip_korean_particles(last_user.text) if last_user else ""

    if slot_name in ("추구미 단어", "T2-T3 단어"):
        # 첫 6 turn 안의 첫 user turn = T1 응답 (user1)
        for turn in state.turns[:6]:
            if isinstance(turn, UserTurn):
                word = strip_korean_particles(turn.text)
                if word and len(word) >= 2:
                    return word
        return ""

    if slot_name in ("관찰 1조각", "관찰"):
        if state.ig_feed_cache:
            analysis = state.ig_feed_cache.get("analysis") or {}
            if isinstance(analysis, dict):
                obs_list = analysis.get("signature_observations") or []
                if obs_list:
                    first = obs_list[0]
                    if isinstance(first, str) and first.strip():
                        return first.strip()
        return _DEFAULT_OBSERVATION

    if slot_name == "T7 발화":
        # T7 user response = 7번째 user turn (zero-indexed 6)
        users = state.user_turns()
        if len(users) > 6:
            return quote_user_phrase(users[6].text)
        return ""

    if slot_name == "T9 장면":
        # T9 user response = 9번째 user turn (zero-indexed 8)
        users = state.user_turns()
        if len(users) > 8:
            return quote_user_phrase(users[8].text)
        return ""

    if slot_name == "vault 발화":
        # user_phrases 우선 (UserTasteProfile.user_original_phrases)
        if user_phrases:
            for phrase in user_phrases:
                if phrase and phrase.strip():
                    return quote_user_phrase(phrase)
        # vault_history fallback
        if vault_history is not None:
            phrases = getattr(vault_history, "user_original_phrases", None) or []
            for phrase in phrases:
                if phrase and phrase.strip():
                    return quote_user_phrase(phrase)
        return ""

    raise ValueError(f"Unknown slot: {slot_name}")


# ─────────────────────────────────────────────
#  Template rendering
# ─────────────────────────────────────────────

_SLOT_RE = re.compile(r"\[([^\]]+)\]")


def render_v4_template(
    turn_id: str,
    state: ConversationState,
    *,
    vault_history: Optional[UserHistory] = None,
    user_phrases: Optional[list[str]] = None,
) -> str:
    """v4 turn 템플릿 렌더링.

    [슬롯명] → render_slot 동적 치환 / {user} → state.user_name.

    Parameters
    ----------
    turn_id : "T1" / "T2-A" / ... / "T11"
    state : ConversationState — 사용자 발화 / ig_feed_cache 참조.
    vault_history / user_phrases : 선택. T7-vault 슬롯용.

    Raises
    ------
    ValueError : 알 수 없는 turn_id.
    """
    template = _TURN_TEMPLATES.get(turn_id)
    if template is None:
        raise ValueError(f"Unknown turn_id: {turn_id}")

    # 1. [슬롯명] 치환 (slot_name 추출 → render_slot 호출 → 치환)
    rendered = template
    for slot_name in _SLOT_RE.findall(template):
        value = render_slot(
            slot_name,
            state,
            vault_history=vault_history,
            user_phrases=user_phrases,
        )
        rendered = rendered.replace(f"[{slot_name}]", value)

    # 2. {user} 치환
    user_name = state.user_name or ""
    rendered = rendered.replace("{user}", user_name)

    return rendered


def get_turn_template(turn_id: str) -> Optional[str]:
    """turn_id → raw template (디버그용). None = 알 수 없는 turn_id."""
    return _TURN_TEMPLATES.get(turn_id)


def all_turn_ids() -> tuple[str, ...]:
    """v4 정의된 turn_id 전수."""
    return tuple(_TURN_TEMPLATES.keys())
