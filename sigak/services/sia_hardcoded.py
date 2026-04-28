"""Sia 하드코딩 메시지 템플릿 (Phase H4, 14 타입 확정판).

SPEC 출처 (총 39 문구):
  - 세션 #4 v2 §8 — 기본 4 타입 × 5 = 20
      OPENING_DECLARATION / META_REBUTTAL / EVIDENCE_DEFENSE / SOFT_WALKBACK
  - 세션 #6 v2 §10 — 관리 3 타입 = 19
      CHECK_IN 5
      RE_ENTRY 5 + 이탈 종결 V5 1
      RANGE_DISCLOSURE 경미 (limit mild) 5 + 심각 (limit severe) 3

  ※ 세션 #7 §9 RANGE_REAFFIRM 5변형 — 베타 hotfix 로 폐기 (2026-04-28).
    결정 트리가 "막막함 우세" 로 과민 분류 → 유저가 안 말한 막막함 가정
    케이스 6/20 보고. range_mode="reaffirm" 들어와도 limit (mild/severe) 로 fallback.
    sia_decision.py 분기 비활성화는 1-B 단계에서 별도 처리.

Haiku 호출 없이 결정적 해시로 변형 선택. 선택 시드:
  sha256("{user_id}:{msg_type}:{turn_idx}") → index % n

Public API
----------
  render_hardcoded(msg_type, state, **slots) -> str
  pick_variant_index(user_id, msg_type, turn_idx, n) -> int

Slots
-----
  user_meta_raw         — META_REBUTTAL 에 임베드할 유저 메타 발화 원어
  observation_evidence  — EVIDENCE_DEFENSE 에 임베드할 구체 관찰 근거
  last_diagnosis        — SOFT_WALKBACK 에 임베드할 직전 DIAGNOSIS 요약
  feed_count            — RANGE_DISCLOSURE 에 임베드할 피드 장수 정수

Mode selectors
--------------
  range_mode            — "limit" (기본) | "reaffirm" (hotfix 후 limit 으로 fallback)
                          limit + state.overattachment_severity="severe" → 심각 pool
  exit_confirmed        — RE_ENTRY 전용. True 이면 이탈 종결 V5 pool 사용.
"""
from __future__ import annotations

import hashlib

from schemas.sia_state import (
    HARDCODED_TYPES,
    ConversationState,
    MsgType,
    RangeMode,
)


# ─────────────────────────────────────────────
#  세션 #4 v2 §8 — 기본 4 타입 × 5 변형 = 20
# ─────────────────────────────────────────────

# OPENING_DECLARATION (§8.1)
# 관찰 누설 금지. 서술 종결. 호명 필수.
# M1 결합 출력 — 이 문장 뒤에 Haiku 가 OBSERVATION 1-2 문장 추가 생성 (decide.py 에서 처리).
_OPENING_VARIANTS: tuple[str, ...] = (
    "{user_name}님 피드 좀 돌아봤어요",
    "{user_name}님 올리신 거 쭉 봤어요",
    "{user_name}님 인스타 좀 들여다봤어요",
    "{user_name}님 피드 한번 훑어봤어요",
    "{user_name}님 올리신 사진들 같이 봤어요",
)

# META_REBUTTAL (§8.2) — 세션 1회. 페르소나 C: 원어 반사 + 담담한 진술 + 열린 질문.
# B 시절 `~이잖아요?` 종결 (닫힌 동의 유도) → C 는 본인 손에서 나온 사실 진술 + 풀어달라는 열린 질문.
_META_REBUTTAL_VARIANTS: tuple[str, ...] = (
    '{user_name}님 "{user_meta_raw}" 라고 하셨는데, 그래도 이 피드 스무 장은 본인이 골라 올리신 거예요. 그 고름이 어떤 결인지 풀어주실래요?',
    '{user_name}님 "{user_meta_raw}" 그 말씀도 들었어요. 근데 제가 보는 건 이 피드고, 이건 본인 손에서 나온 거예요. 어떤 마음으로 올리셨어요?',
    '{user_name}님 "{user_meta_raw}" 그 부분은 받아둘게요. 그래도 여기 올라온 스무 장은 본인이 직접 고른 거예요. 그 고름의 결, 어떻게 일어나요?',
    '{user_name}님 "{user_meta_raw}" 그 말씀이 있는 거랑 별개로, 지금 제가 보고 있는 건 본인이 올린 피드예요. 이 피드 안에서 본인이 보이는 부분 어디예요?',
    '{user_name}님 "{user_meta_raw}" 그 마음 알겠어요. 근데 피드 자체는 본인 손에서 나온 거예요. 어떤 순간에 올리고 싶어지세요?',
)

# EVIDENCE_DEFENSE (§8.3) — 세션 1회. 페르소나 C: 자기 권위 호명 제거 + 담담한 서술 종결.
# B 시절 "저 이거 직접 세어봤어요" / `~이잖아요?` → C 는 "피드 안에 이미 있다" 담담한 진술.
_EVIDENCE_DEFENSE_VARIANTS: tuple[str, ...] = (
    "{user_name}님 {observation_evidence} 이건 피드에 그대로 있는 거예요. 다시 같이 보면 같은 게 보일 거예요",
    "{user_name}님 {observation_evidence} 이건 추측이 아니라 피드에 나와 있는 그대로예요",
    "{user_name}님 {observation_evidence} 이 부분은 피드 자체가 보여주는 거예요",
    "{user_name}님 {observation_evidence} 이건 올리신 사진들이 그대로 말해주는 거예요",
    "{user_name}님 {observation_evidence} 이건 제가 만든 게 아니라 피드 안에 이미 있는 거예요",
)

# SOFT_WALKBACK (§8.4) — 평가 없는 설명체. 서술 종결.
_SOFT_WALKBACK_VARIANTS: tuple[str, ...] = (
    "{last_diagnosis} 이건 제가 느낀 거고, 이게 정답이란 얘기는 아니에요",
    "{last_diagnosis} 라고 봤는데, 다르게 읽히셔도 그게 맞을 수 있어요",
    "{last_diagnosis} 이렇게 정리해본 거예요. {user_name}님이 보시는 각도랑 다를 수 있어요",
    "{last_diagnosis} 이건 한 가지 읽기고, 본인 감각이 더 정확할 수 있어요",
    "{last_diagnosis} 이런 가능성 하나 열어둔 거예요. 확정은 아니에요",
)


# ─────────────────────────────────────────────
#  세션 #6 v2 §10 — 관리 3 타입
# ─────────────────────────────────────────────

# CHECK_IN (§10.1) — 속도 옵션 + 이탈 옵션 필수. 서술 종결.
_CHECK_IN_VARIANTS: tuple[str, ...] = (
    "{user_name}님, 제 질문이 좀 많은 것 같아요. 편한 속도로 말씀해주시거나 여기서 그만하고 싶으시면 그것도 괜찮아요",
    "{user_name}님, 제 페이스가 좀 빠른가요. 편하신 만큼 답해주셔도 되고 지금 여기까지 보고 싶으시면 그것도 괜찮아요",
    "{user_name}님, 제가 너무 파고드는 거 같네요. 편한 속도로 하셔도 되고 여기서 멈추고 싶으시면 그것도 괜찮아요",
    "{user_name}님, 잠깐. 제가 좀 몰아친 느낌이 있어요. 편한 속도로 말씀해주시거나 나중에 이어하고 싶으시면 그것도 괜찮아요",
    "{user_name}님, 제가 질문을 좀 많이 드렸네요. 천천히 하셔도 되고 여기까지만 보고 싶으시면 그것도 괜찮아요",
)

# RE_ENTRY (§10.2) — CHECK_IN 직후 재진입. 반응 기준 완화 표현 필수. 서술 종결.
_RE_ENTRY_VARIANTS: tuple[str, ...] = (
    "아 그러셨구나. 그럼 제가 본 걸 정리해서 말씀드릴게요. 맞다 아니다만 반응 주셔도 괜찮아요",
    "아 넵 알겠어요. 그럼 제가 읽은 부분 간단히 말씀드릴게요. 편하신 만큼만 반응해주셔도 돼요",
    '아 그랬군요. 제가 본 걸 쭉 정리해볼게요. 그냥 들으셔도 되고 중간에 "아니다" 싶으면 말씀해주셔도 돼요',
    "아 그런 거였구나. 그럼 남은 얘기는 제가 마무리하는 쪽으로 갈게요. 맞다 아니다만 반응 주셔도 괜찮아요",
    "아 넵. 그럼 제가 본 거 이어서 말씀드릴게요. 편하신 만큼만 들으셔도 돼요",
)

# RE_ENTRY V5 — 이탈 선택 시 종결 버전 (세션 #6 v2 §10.2, 10.3 (a) 확정)
_RE_ENTRY_EXIT_VARIANTS: tuple[str, ...] = (
    "알겠어요. {user_name}님 언제든 돌아오시면 이어갈 수 있어요",
)

# RANGE_DISCLOSURE 경미 (§10.3) — 한계 명시 + 관찰 유효성 보존. 서술 종결.
_RANGE_LIMIT_MILD_VARIANTS: tuple[str, ...] = (
    "제가 본 건 피드 {feed_count}장이 전부라서, {user_name}님 전체를 아는 건 아니에요. 그치만 피드에서 드러난 부분은 이 정도 또렷했다는 거예요",
    "사실 제가 가진 정보는 피드 {feed_count}장뿐이에요. {user_name}님 실제 일상이랑 다를 수 있어요. 다만 피드 안에서는 이렇게 읽혔다는 거예요",
    "제가 읽은 건 피드 {feed_count}장이라서 {user_name}님 전부는 아니에요. 그 범위 안에서 드러난 게 꽤 일관됐다는 거예요",
    "{user_name}님, 제가 본 건 피드 {feed_count}장이 전부라 한계가 있어요. 그 안에서 보인 패턴이 이 정도였다는 거예요",
    "제가 접근한 건 피드 {feed_count}장에 한정돼요. {user_name}님이 사시는 맥락 전체는 아니에요. 다만 그 안에서 이 정도 보였다는 거예요",
)

# RANGE_DISCLOSURE 심각 (§10.4) — 고립/의존 신호. 외부 자원 권유 추가. 서술 종결.
_RANGE_LIMIT_SEVERE_VARIANTS: tuple[str, ...] = (
    "{user_name}님 이 얘기 꺼내주신 건 고마워요. 다만 제가 친구나 상담 대체가 될 수는 없고, 이런 얘기는 사람한테 하시는 게 더 닿을 거예요",
    "{user_name}님, 지금 하신 말씀 무겁게 받았어요. 근데 저는 피드 {feed_count}장 본 AI 라서 이런 얘기 받아드리기에 한계가 있어요. 가까운 사람한테 한번 말씀 나눠보시는 게 좋을 것 같아요",
    "{user_name}님, 그런 상황이셨다니 마음이 쓰여요. 다만 제가 해드릴 수 있는 건 피드 안에서 본 것까지예요. 사람한테 이런 얘기 하실 여지가 있으면 그쪽이 더 도움 될 거예요",
)


# ─────────────────────────────────────────────
#  세션 #7 §9 RANGE_REAFFIRM 5변형 — 베타 hotfix (2026-04-28) 로 폐기.
#  결정 트리가 "막막함 우세" 과민 분류 → 유저가 안 말한 막막함 가정 케이스 6/20.
#  range_mode="reaffirm" 들어와도 limit pool 로 fallback (아래 _pick_variant_pool 참조).
# ─────────────────────────────────────────────


# ─────────────────────────────────────────────
#  기본 TEMPLATES 맵 (msg_type → 디폴트 pool)
#
#  RE_ENTRY / RANGE_DISCLOSURE 는 mode/severity 분기 시 다른 pool 사용.
#  디폴트 pool 은 가장 빈번한 케이스 (RE_ENTRY 비-이탈, RANGE limit mild).
# ─────────────────────────────────────────────

TEMPLATES: dict[MsgType, tuple[str, ...]] = {
    MsgType.OPENING_DECLARATION: _OPENING_VARIANTS,
    MsgType.META_REBUTTAL: _META_REBUTTAL_VARIANTS,
    MsgType.EVIDENCE_DEFENSE: _EVIDENCE_DEFENSE_VARIANTS,
    MsgType.SOFT_WALKBACK: _SOFT_WALKBACK_VARIANTS,
    MsgType.CHECK_IN: _CHECK_IN_VARIANTS,
    MsgType.RE_ENTRY: _RE_ENTRY_VARIANTS,
    MsgType.RANGE_DISCLOSURE: _RANGE_LIMIT_MILD_VARIANTS,
}

# 전수 변형 카탈로그 (베타 hotfix 후 총 39, 원래 44 — RANGE_REAFFIRM 5변형 폐기)
ALL_VARIANT_POOLS: dict[str, tuple[str, ...]] = {
    "opening_declaration": _OPENING_VARIANTS,
    "meta_rebuttal": _META_REBUTTAL_VARIANTS,
    "evidence_defense": _EVIDENCE_DEFENSE_VARIANTS,
    "soft_walkback": _SOFT_WALKBACK_VARIANTS,
    "check_in": _CHECK_IN_VARIANTS,
    "re_entry": _RE_ENTRY_VARIANTS,
    "re_entry_exit": _RE_ENTRY_EXIT_VARIANTS,
    "range_limit_mild": _RANGE_LIMIT_MILD_VARIANTS,
    "range_limit_severe": _RANGE_LIMIT_SEVERE_VARIANTS,
    # "range_reaffirm" 삭제 — 베타 hotfix (2026-04-28). 막막함 가정 진앙.
}


# ─────────────────────────────────────────────
#  Pool 선택 로직
# ─────────────────────────────────────────────

def _pick_variant_pool(
    msg_type: MsgType,
    state: ConversationState,
    range_mode: RangeMode,
    exit_confirmed: bool,
) -> tuple[str, ...]:
    """msg_type + mode selectors 에 따라 사용할 variant pool 결정."""
    if msg_type == MsgType.RE_ENTRY and exit_confirmed:
        return _RE_ENTRY_EXIT_VARIANTS
    if msg_type == MsgType.RANGE_DISCLOSURE:
        # range_mode="reaffirm" 진입해도 limit pool 로 fallback — 베타 hotfix (2026-04-28).
        # 막막함 가정 진앙 (sia_decision.py 분기 비활성화는 1-B에서 별도 처리).
        if state.overattachment_severity == "severe":
            return _RANGE_LIMIT_SEVERE_VARIANTS
        return _RANGE_LIMIT_MILD_VARIANTS
    return TEMPLATES[msg_type]


# ─────────────────────────────────────────────
#  Public — index selection + rendering
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


def render_hardcoded(
    msg_type: MsgType,
    state: ConversationState,
    *,
    user_meta_raw: str = "",
    observation_evidence: str = "",
    last_diagnosis: str = "",
    feed_count: int = 0,
    range_mode: RangeMode = "limit",
    exit_confirmed: bool = False,
) -> str:
    """HARDCODED_TYPES 에 해당하는 메시지 결정적 생성.

    Parameters
    ----------
    msg_type : HARDCODED_TYPES 중 하나. 아니면 ValueError.
    state    : user_id / user_name / overattachment_severity / assistant_turns() 소비.
    user_meta_raw        : META_REBUTTAL 전용 슬롯. 생략 시 빈 문자열.
    observation_evidence : EVIDENCE_DEFENSE 전용 슬롯.
    last_diagnosis       : SOFT_WALKBACK 전용 슬롯.
    feed_count           : RANGE_DISCLOSURE 전용 슬롯 (정수).
    range_mode           : "limit" (기본) | "reaffirm" (베타 hotfix 후 limit 으로 fallback).
    exit_confirmed       : RE_ENTRY 이탈 종결 버전 트리거.
    """
    if msg_type not in HARDCODED_TYPES:
        raise ValueError(f"{msg_type.value} is not hardcoded; use Haiku prompt")

    variants = _pick_variant_pool(msg_type, state, range_mode, exit_confirmed)
    turn_idx = len(state.assistant_turns())
    idx = pick_variant_index(state.user_id, msg_type, turn_idx, len(variants))
    template = variants[idx]

    rendered = template.format(
        user_name=state.user_name,
        user_meta_raw=user_meta_raw,
        observation_evidence=observation_evidence,
        last_diagnosis=last_diagnosis,
        feed_count=feed_count,
    )
    # 슬롯 누락으로 생길 수 있는 선두 공백 정리
    return rendered.strip()


def total_variant_count() -> int:
    """전수 하드코딩 문구 개수 (베타 hotfix 후 39 — 원래 44에서 RANGE_REAFFIRM 5 폐기)."""
    return sum(len(v) for v in ALL_VARIANT_POOLS.values())
