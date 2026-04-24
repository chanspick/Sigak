"""Sia Phase H v4 Live Haiku probe — A-17/18/19/20 검증.

실행 조건:
  RUN_PROBE_LIVE=1
  ANTHROPIC_API_KEY=sk-ant-...
  py scripts/probe_sia_phase_h_live.py

목표:
  - Haiku 4.5 로 5턴 대화 시뮬 (@xhan0_0 본인 피드 맥락)
  - 각 턴마다 A-17 (영업어휘), A-18 (길이), A-20 (추상칭찬), 마크다운 grep
  - 평균 발화 길이 측정
  - fallback 발동 여부 기록

예상 비용:
  5 turn × ~$0.006 ≈ $0.03
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.sia_state import (  # noqa: E402
    AssistantTurn,
    ConversationState,
    MsgType,
    UserTurn,
)
from services.sia_decision import Composition, decide, update_state_from_user_turn  # noqa: E402
from services.sia_hardcoded import render_hardcoded  # noqa: E402
from services.sia_llm import _render_ig_summary, call_sia_turn_with_retry  # noqa: E402
from services.sia_prompts_v4 import load_haiku_prompt  # noqa: E402
from services.sia_validators_v4 import (  # noqa: E402
    check_a17_commerce,
    check_a18_length,
    check_a18_length_warning,
    check_a20_abstract_praise,
    check_markdown_markup,
    validate,
)


FOUNDER_ANALYSIS = {
    "tone_category": "웜뉴트",
    "tone_percentage": 54,
    "saturation_trend": "안정",
    "environment": "실내 카페 + 음식 + 셀프 톤",
    "pose_frequency": "정면 드묾, 사물/공간 위주",
    "observed_adjectives": ["차분", "정돈", "관찰자"],
    "style_consistency": 0.71,
    "mood_signal": "본인 얼굴보다 일상 결 자체를 더 자주 기록하는 피드",
    "three_month_shift": "피드 리듬이 일정하게 유지되는 방향",
    "analyzed_at": "2026-04-24T12:00:00+00:00",
}


SCRIPTED_USER_TURNS = [
    # t1 — 범위 확인
    "얼마나 정확하게 읽는 건데",
    # t2 — self-PR
    "평균보단 감각 있다고들 하던데",
    # t3 — 일반화 회피
    "다들 비슷하지 않나요",
    # t4 — 짧은 긍정
    "어 맞아",
    # t5 — 종료 의향
    "이 정도면 충분해요",
]


def _summarize(text: str) -> dict:
    """A-17/18/20/markdown 위반 수집 + 통계."""
    return {
        "char_count": len(text),
        "a17": check_a17_commerce(text),
        "a18_hard": check_a18_length(text),
        "a18_warn": check_a18_length_warning(text),
        "a20": check_a20_abstract_praise(text),
        "markdown": check_markdown_markup(text),
    }


def _run_probe() -> dict:
    if not os.getenv("RUN_PROBE_LIVE"):
        print("RUN_PROBE_LIVE not set. Skipping.")
        return {"skipped": True}
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY missing.")
        return {"error": "no_api_key"}

    state = ConversationState(
        session_id="probe-phase-h",
        user_id="founder-xhan0_0",
        user_name="진규",
        user_gender="male",
        user_age=None,
        ig_handle="xhan0_0",
        ig_feed_cache=FOUNDER_ANALYSIS,
    )

    turns: list[dict] = []

    # M1 = OPENING_DECLARATION + OBSERVATION 결합.
    opening = render_hardcoded(
        MsgType.OPENING_DECLARATION,
        user_name=state.user_name,
        feed_count=38,
    )
    prompt = load_haiku_prompt(
        MsgType.OBSERVATION,
        state,
        user_flags=None,
        vision_summary=_render_ig_summary(state.ig_feed_cache),
        is_first_turn=True,
        is_combined=False,
    )
    obs = call_sia_turn_with_retry(
        system_prompt=prompt,
        messages_history=[],
    )
    m1_text = f"{opening}\n{obs}".strip()
    v = validate(m1_text, MsgType.OBSERVATION, state=state)
    turns.append({
        "turn_idx": 0,
        "role": "assistant",
        "msg_type": "M1_OPENING+OBSERVATION",
        "text": m1_text,
        "stats": _summarize(m1_text),
        "validator_errors": v.errors,
        "validator_warnings": v.warnings,
    })
    state.turns.append(AssistantTurn(
        text=m1_text, msg_type=MsgType.OBSERVATION, turn_idx=0,
    ))
    print(f"\n─── M1 (OPENING+OBSERVATION) ───\n{m1_text}\n")

    # M2-M5 — 유저 턴 대응.
    for i, user_msg in enumerate(SCRIPTED_USER_TURNS):
        state.turns.append(UserTurn(
            text=user_msg, turn_idx=len(state.turns),
        ))
        state = update_state_from_user_turn(state, user_msg)
        composition = decide(state)
        msg_type = composition.primary_type

        if msg_type in {
            MsgType.OPENING_DECLARATION,
            MsgType.META_REBUTTAL,
            MsgType.EVIDENCE_DEFENSE,
            MsgType.SOFT_WALKBACK,
            MsgType.CHECK_IN,
            MsgType.RE_ENTRY,
            MsgType.RANGE_DISCLOSURE,
        }:
            # 하드코딩
            kwargs = {
                "user_name": state.user_name,
                "feed_count": 38,
            }
            if msg_type == MsgType.META_REBUTTAL:
                kwargs["user_meta_raw"] = user_msg
            if msg_type == MsgType.EVIDENCE_DEFENSE:
                kwargs["observation_evidence"] = "카페랑 사물 사진이 반복되더라구요."
            if msg_type == MsgType.SOFT_WALKBACK:
                kwargs["last_diagnosis"] = "피드에 본인 얼굴이 드문 편이시더라구요."
            try:
                text = render_hardcoded(
                    msg_type,
                    **kwargs,
                    range_mode=composition.range_mode,
                    severity=state.overattachment_severity,
                    exit_confirmed=composition.exit_confirmed,
                )
            except TypeError:
                text = render_hardcoded(msg_type, **kwargs)
            source = "hardcoded"
        else:
            prompt = load_haiku_prompt(
                msg_type,
                state,
                user_flags=None,
                vision_summary=_render_ig_summary(state.ig_feed_cache),
                is_first_turn=False,
                is_combined=composition.is_combined,
                secondary_type=composition.secondary_type,
                confrontation_block=composition.confrontation_block,
                apply_self_pr_prefix=composition.apply_self_pr_prefix,
                range_mode=composition.range_mode,
            )
            history = [
                {
                    "role": "assistant" if isinstance(t, AssistantTurn) else "user",
                    "content": t.text,
                }
                for t in state.turns[-6:]
                if getattr(t, "text", None)
            ]
            text = call_sia_turn_with_retry(
                system_prompt=prompt,
                messages_history=history,
            )
            source = "haiku"

        v = validate(
            text, msg_type, state=state,
            range_mode=composition.range_mode,
            confrontation_block=composition.confrontation_block,
            is_combined=composition.is_combined,
            exit_confirmed=composition.exit_confirmed,
        )
        turns.append({
            "turn_idx": len(turns),
            "role": "user",
            "text": user_msg,
        })
        turns.append({
            "turn_idx": len(turns),
            "role": "assistant",
            "msg_type": msg_type.value,
            "composition": {
                "primary": composition.primary_type.value,
                "secondary": composition.secondary_type.value if composition.secondary_type else None,
                "block": composition.confrontation_block,
                "range_mode": composition.range_mode,
                "is_combined": composition.is_combined,
                "apply_self_pr_prefix": composition.apply_self_pr_prefix,
                "exit_confirmed": composition.exit_confirmed,
            },
            "source": source,
            "text": text,
            "stats": _summarize(text),
            "validator_errors": v.errors,
            "validator_warnings": v.warnings,
        })
        state.turns.append(AssistantTurn(
            text=text, msg_type=msg_type, turn_idx=len(state.turns),
        ))
        print(f"\n─── T{i+1} user ───\n{user_msg}")
        print(f"─── T{i+1} Sia ({msg_type.value}, {source}) ───\n{text}\n")
        time.sleep(0.5)

    assistant_texts = [
        t["text"] for t in turns
        if t.get("role") == "assistant" and t.get("source") == "haiku"
    ]
    if assistant_texts:
        avg_len = sum(len(t) for t in assistant_texts) / len(assistant_texts)
    else:
        avg_len = 0

    a17_total = sum(
        len(t.get("stats", {}).get("a17", []))
        for t in turns if t.get("role") == "assistant"
    )
    a18_hard_total = sum(
        len(t.get("stats", {}).get("a18_hard", []))
        for t in turns if t.get("role") == "assistant"
    )
    a20_total = sum(
        len(t.get("stats", {}).get("a20", []))
        for t in turns if t.get("role") == "assistant"
    )
    md_total = sum(
        len(t.get("stats", {}).get("markdown", []))
        for t in turns if t.get("role") == "assistant"
    )

    summary = {
        "turns": turns,
        "aggregate": {
            "haiku_turn_count": len(assistant_texts),
            "haiku_avg_length": round(avg_len, 1),
            "a17_commerce_violations": a17_total,
            "a18_hard_violations": a18_hard_total,
            "a20_praise_violations": a20_total,
            "markdown_violations": md_total,
        },
    }

    print("\n═══ AGGREGATE ═══")
    print(json.dumps(summary["aggregate"], indent=2, ensure_ascii=False))

    out_path = Path(__file__).parent / "probe_sia_phase_h_live_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {out_path}")
    return summary


if __name__ == "__main__":
    _run_probe()
