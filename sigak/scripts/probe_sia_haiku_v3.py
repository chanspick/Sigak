"""Sia v3 Live Haiku probe — Phase F (Task 10).

12 시나리오 × Haiku 4.5 실 API 호출 → 응답 수집 + validator 검증 + 체감 리포트.

실행 조건:
  RUN_PROBE_LIVE=1
  ANTHROPIC_API_KEY=sk-ant-...
  py scripts/probe_sia_haiku_v3.py

예상 비용:
  Haiku 4.5 input $1/1M, output $5/1M
  turn 당 ~3k input + ~500 output = ~$0.006
  12 × $0.006 ≈ $0.07

주의:
  - 실 API 호출이므로 비용 발생
  - 각 시나리오 5-15s 소요. 전체 3-5분 예상
  - 결과는 stdout + probe_sia_haiku_v3_output.json 파일에 저장
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


FEMALE_ANALYSIS = {
    "tone_category": "쿨뮤트",
    "tone_percentage": 68,
    "saturation_trend": "감소",
    "environment": "실내 + 자연광",
    "pose_frequency": "측면 > 정면",
    "observed_adjectives": ["단정", "감성", "조용함"],
    "style_consistency": 0.82,
    "mood_signal": "정돈된 여운을 남기는 방식에 익숙하신 분입니다",
    "three_month_shift": "채도가 점진적으로 낮아지는 방향",
    "analyzed_at": "2026-04-22T10:00:00+00:00",
}

MALE_ANALYSIS = {
    "tone_category": "중성",
    "tone_percentage": 62,
    "saturation_trend": "안정",
    "environment": "외부 활동 + 야외",
    "pose_frequency": "정면 > 측면",
    "observed_adjectives": ["단정", "담백", "묵직함"],
    "style_consistency": 0.75,
    "mood_signal": "꾸밈 없이 담백한 인상을 전달하시는 분입니다",
    "three_month_shift": None,
    "analyzed_at": "2026-04-22T10:00:00+00:00",
}


def _cache(gender: str, with_analysis: bool = True) -> dict:
    analysis = FEMALE_ANALYSIS if gender == "female" else MALE_ANALYSIS
    return {
        "scope": "full",
        "profile_basics": {
            "username": "testuser",
            "post_count": 10,
            "follower_count": 500,
            "following_count": 300,
            "is_private": False,
            "is_verified": False,
        },
        "latest_posts": [
            {"caption": "일상 기록", "latest_comments": ["단정하다", "감성적이다"]},
        ] * 10,
        "analysis": analysis if with_analysis else None,
        "last_analyzed_post_count": 10 if with_analysis else None,
    }


# 시나리오 prior 메시지 헬퍼 (message history)
def _short_sia_opening() -> str:
    return "정세현님의 피드를 살펴보겠습니다. 정세현님은 담담하신 인상을 전달하시는 분입니다. 이 단정이 얼마나 가까우신가요?"


def _messages_for(turn_type: str) -> list[dict]:
    opener = {"role": "user", "content": "시작하겠습니다."}
    sia_opening = {"role": "assistant", "content": _short_sia_opening()}

    if turn_type == "opening":
        return [opener]

    if turn_type == "branch_agree":
        return [opener, sia_opening, {"role": "user", "content": "네, 비슷하다"}]
    if turn_type == "branch_half":
        return [opener, sia_opening, {"role": "user", "content": "절반 정도 맞다"}]
    if turn_type == "branch_disagree":
        return [opener, sia_opening, {"role": "user", "content": "다르다"}]
    if turn_type == "branch_fail":
        return [opener, sia_opening, {"role": "user", "content": "전혀 다르다"}]

    if turn_type == "force_external_transition":
        mid_a = {"role": "assistant", "content": "그러면 정세현님은 오히려 활발하신 분입니다."}
        mid_b = {"role": "assistant", "content": "다시 한 번 여쭙겠습니다. 정세현님은 섬세하신 편이십니다."}
        return [
            opener, sia_opening,
            {"role": "user", "content": "다르다"},
            mid_a,
            {"role": "user", "content": "전혀 다르다"},
            mid_b,
            {"role": "user", "content": "다르다"},
        ]

    # external turn sequence — spectrum 2회 hit 후 외적 진입
    sia_agree_deepen = {
        "role": "assistant",
        "content": "정세현님은 혼자 시간을 잘 쓰시는 분입니다. 이 방향은 얼마나 가까우신가요?",
    }
    if turn_type == "external_desired_image":
        return [
            opener, sia_opening,
            {"role": "user", "content": "네, 비슷하다"}, sia_agree_deepen,
            {"role": "user", "content": "네, 비슷하다"},
        ]

    if turn_type == "external_body_height":
        return [
            opener, sia_opening,
            {"role": "user", "content": "네, 비슷하다"}, sia_agree_deepen,
            {"role": "user", "content": "네, 비슷하다"},
            {"role": "assistant", "content": "방향을 여쭙겠습니다. 어떤 인상을 만들고 싶으신가요?"},
            {"role": "user", "content": "세련되고 거리감 있는 인상"},
            {"role": "assistant", "content": "참고하시는 스타일이 있다면 한 줄로 답해주시면 충분합니다."},
            {"role": "user", "content": "조용한 분위기의 일상 기록"},
        ]

    if turn_type == "closing":
        return [
            {"role": "user", "content": "대화를 마무리하고 싶습니다."},
        ]

    return [opener]


def _collected_for(turn_type: str) -> dict:
    """후반 턴에서 system prompt 에 보여줄 누적 필드."""
    if turn_type == "closing":
        return {
            "desired_image": "세련되고 거리감 있는 인상",
            "reference_style": "조용한 분위기의 일상 기록",
            "height": "163-168cm",
            "weight": "50-55kg",
            "shoulder": "평균",
            "current_concerns": "톤의 일관성을 더 단단하게 유지하고 싶습니다",
            "lifestyle_context": "실내 중심",
        }
    if turn_type == "external_body_height":
        return {
            "desired_image": "세련되고 거리감 있는 인상",
            "reference_style": "조용한 분위기의 일상 기록",
        }
    return {}


SCENARIOS = [
    {"id": "01_opening_female", "gender": "female", "turn_type": "opening", "vision": True},
    {"id": "02_opening_male",   "gender": "male",   "turn_type": "opening", "vision": True},
    {"id": "03_branch_agree",   "gender": "female", "turn_type": "branch_agree", "vision": True},
    {"id": "04_branch_half",    "gender": "female", "turn_type": "branch_half", "vision": True},
    {"id": "05_branch_disagree","gender": "female", "turn_type": "branch_disagree", "vision": True},
    {"id": "06_branch_fail",    "gender": "female", "turn_type": "branch_fail", "vision": True},
    {"id": "07_force_external", "gender": "female", "turn_type": "force_external_transition", "vision": True},
    {"id": "08_external_desired_image", "gender": "female", "turn_type": "external_desired_image", "vision": True},
    {"id": "09_body_female",    "gender": "female", "turn_type": "external_body_height", "vision": True},
    {"id": "10_body_male",      "gender": "male",   "turn_type": "external_body_height", "vision": True},
    {"id": "11_closing_female", "gender": "female", "turn_type": "closing", "vision": True},
    {"id": "12_vision_null_fallback", "gender": "female", "turn_type": "opening", "vision": False},
]


def _require_live() -> None:
    if os.environ.get("RUN_PROBE_LIVE") != "1":
        print("[skipped] RUN_PROBE_LIVE != 1. 실제 API 호출 없음.")
        print("실행: RUN_PROBE_LIVE=1 ANTHROPIC_API_KEY=... py scripts/probe_sia_haiku_v3.py")
        sys.exit(0)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY 미설정")
        sys.exit(1)


def _raw_haiku_call(system_prompt: str, messages: list[dict]) -> str:
    """sia_llm.call_sia_turn 와 동일하되 validator 를 건너뛰고 raw text 반환.

    Probe 는 validator 실패 응답도 보고해야 하므로 raise 하지 않음.
    """
    from services.sia_llm import _get_client
    from config import get_settings

    settings = get_settings()
    client = _get_client()
    response = client.messages.create(
        model=settings.anthropic_model_haiku,
        max_tokens=600,
        system=system_prompt,
        messages=messages,
    )
    if not response.content:
        return ""
    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "\n".join(text_blocks).strip()


def _run_scenario(scenario: dict) -> dict:
    """하나의 시나리오 실행 — 결과 dict 반환."""
    from services import sia_llm
    from services.sia_validators import find_violations

    turn_type = scenario["turn_type"]
    gender = scenario["gender"]
    use_vision = scenario["vision"]

    # vision_null_fallback: cache 는 있지만 analysis 만 None
    ig_cache = _cache(gender, with_analysis=use_vision)

    collected = _collected_for(turn_type)

    system_prompt = sia_llm.build_system_prompt(
        user_name="정세현",
        resolved_name=None,
        collected_fields=collected,
        missing_fields=[],
        ig_feed_cache=ig_cache,
        turn_type=turn_type,
        gender=gender,
    )

    messages = _messages_for(turn_type)

    started_at = time.time()
    error: Optional[str] = None
    response_text: Optional[str] = None
    try:
        response_text = _raw_haiku_call(system_prompt, messages)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    duration = round(time.time() - started_at, 2)

    violations: dict = {}
    if response_text:
        violations = find_violations(response_text)

    return {
        "id": scenario["id"],
        "gender": gender,
        "turn_type": turn_type,
        "vision": use_vision,
        "duration_s": duration,
        "response": response_text,
        "violations": violations,
        "error": error,
        "system_prompt_chars": len(system_prompt),
    }


def main() -> int:
    _require_live()

    results: list[dict] = []
    print(f"Sia v3 live probe — {len(SCENARIOS)} scenarios")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    for idx, scenario in enumerate(SCENARIOS, 1):
        print(f"\n[{idx:>2}/{len(SCENARIOS)}] {scenario['id']} "
              f"(gender={scenario['gender']}, turn={scenario['turn_type']})")
        result = _run_scenario(scenario)
        results.append(result)

        if result["error"]:
            print(f"   ERROR: {result['error']}")
            continue

        print(f"   duration: {result['duration_s']}s  "
              f"prompt_len: {result['system_prompt_chars']} chars")

        # 위반 요약
        if result["violations"]:
            flags = ", ".join(f"{k}:{len(v)}" for k, v in result["violations"].items())
            print(f"   VIOLATIONS: {flags}")
        else:
            print(f"   validator: CLEAN")

        # 응답 첫 3줄 미리보기
        if result["response"]:
            lines = result["response"].strip().split("\n")[:3]
            for line in lines:
                print(f"   | {line[:80]}")

    # 종합 요약
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    clean_count = sum(1 for r in results if not r["violations"] and not r["error"])
    error_count = sum(1 for r in results if r["error"])
    violation_count = sum(1 for r in results if r["violations"] and not r["error"])
    print(f"Total:      {len(results)}")
    print(f"Clean:      {clean_count}")
    print(f"Violations: {violation_count}")
    print(f"Errors:     {error_count}")

    # JSON dump
    out_path = Path(__file__).parent / "probe_sia_haiku_v3_output.json"
    out_path.write_text(
        json.dumps({
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nFull output: {out_path}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
