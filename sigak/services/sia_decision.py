"""decide_next_message — Sia 다음 메시지 타입 결정 트리 (Phase H2b).

PHASE_H_DIRECTIVE §4.

우선순위:
  A-3 트리거 강제 (최상)  > A-2 비율 강제  > phase 기본 (최하)

결정적 로직. Haiku/LLM 호출 없음. state 만으로 결정 가능.
"""
from __future__ import annotations

from schemas.sia_state import (
    DIAGNOSIS_MIN_RATIO,
    ConversationState,
    MsgType,
    UserTurn,
)


def decide_next_message(state: ConversationState) -> MsgType:
    """다음 Sia 메시지 타입 결정.

    directive §4.1 로직 그대로.
    """
    a_turns = state.assistant_turns()

    # ──────────────────────────────────────
    # 0. 오프닝 (HOOK 삭제 후 바로 OBSERVATION)
    # ──────────────────────────────────────
    if len(a_turns) == 0:
        return MsgType.OPENING_DECLARATION
    if len(a_turns) == 1:
        return MsgType.OBSERVATION

    last_user = state.last_user()
    if last_user is None:
        return MsgType.OBSERVATION

    flags = last_user.flags

    # ──────────────────────────────────────
    # 1. A-3 트리거 강제 (최상위)
    # ──────────────────────────────────────

    # 1.1. 해명 요청 → 1 메시지 응답 (DIAGNOSIS or OBSERVATION)
    if flags.has_explain_req:
        if state.observation_count >= 2:
            return MsgType.DIAGNOSIS
        return MsgType.OBSERVATION

    # 1.2. 메타 반박 → META_REBUTTAL (세션 1회)
    if flags.has_meta_challenge and not state.meta_rebuttal_used:
        return MsgType.META_REBUTTAL

    # 1.3. 근거 불신 → EVIDENCE_DEFENSE (세션 1회)
    if flags.has_evidence_doubt and not state.evidence_defense_used:
        return MsgType.EVIDENCE_DEFENSE

    # 1.4. 감정 단어 → EMPATHY_MIRROR
    if flags.has_emotion_word:
        return MsgType.EMPATHY_MIRROR

    # 1.5. ㅜㅜ or 자기개시 2연속 → EMPATHY_MIRROR
    if flags.has_tt or _consecutive_self_disclosure(state, n=2):
        return MsgType.EMPATHY_MIRROR

    # ──────────────────────────────────────
    # 2. A-2 비율 강제 (중위)
    # ──────────────────────────────────────

    # 2.1. 수집 3연속 → RECOGNITION 강제 (일정 호흡 보장)
    if state.collection_streak >= 3:
        return MsgType.RECOGNITION

    # 2.2. RECOGNITION 하한 체크
    #   obs>=3 → 세션 2회 이상
    #   obs>=2 → 세션 1회 이상
    if state.observation_count >= 3:
        recog_needed = 2
    elif state.observation_count >= 2:
        recog_needed = 1
    else:
        recog_needed = 0
    recog_done = state.type_counts.get(MsgType.RECOGNITION, 0)
    if (
        (recog_needed - recog_done) > 0
        and state.observations_since_recognition >= 2
    ):
        return MsgType.RECOGNITION

    # 2.3. DIAGNOSIS 하한 체크 (총 8턴 이상부터 적용)
    total_turns = len(a_turns)
    if total_turns >= 8:
        diag_done = state.type_counts.get(MsgType.DIAGNOSIS, 0)
        diag_needed = max(1, int(total_turns * DIAGNOSIS_MIN_RATIO))
        if (
            diag_done < diag_needed
            and state.observation_count >= 3
            and flags.has_concede
        ):
            return MsgType.DIAGNOSIS

    # ──────────────────────────────────────
    # 3. Phase 규칙 (하위)
    # ──────────────────────────────────────

    # 3.1. concede + 관찰 3+ → RECOGNITION 먼저, 그 다음 DIAGNOSIS
    if flags.has_concede and state.observation_count >= 3:
        last = a_turns[-1]
        if last.msg_type == MsgType.RECOGNITION:
            return MsgType.DIAGNOSIS
        return MsgType.RECOGNITION

    # 3.2. 방어 + 관찰 2+ → CONFRONTATION
    if flags.is_defensive and state.observation_count >= 2:
        return MsgType.CONFRONTATION

    # 3.3. 관찰 부족 → 수집 계열 (같은 타입 2연속 회피)
    if state.observation_count < 3:
        last = a_turns[-1]
        if last.msg_type == MsgType.OBSERVATION:
            return MsgType.PROBE
        if last.msg_type == MsgType.PROBE:
            return MsgType.EXTRACTION
        return MsgType.OBSERVATION

    # 3.4. DIAGNOSIS 직후 → SOFT_WALKBACK
    if a_turns[-1].msg_type == MsgType.DIAGNOSIS:
        return MsgType.SOFT_WALKBACK

    # 3.5. fallback — RECOGNITION
    return MsgType.RECOGNITION


# ─────────────────────────────────────────────
#  Internal
# ─────────────────────────────────────────────

def _consecutive_self_disclosure(state: ConversationState, n: int = 2) -> bool:
    """최근 n 개 UserTurn 모두 has_self_disclosure 인지."""
    u_turns = state.user_turns()
    if len(u_turns) < n:
        return False
    return all(t.flags.has_self_disclosure for t in u_turns[-n:])
