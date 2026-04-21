"""Sonnet 4.6 extraction live probe — D4 검수용 스크립트.

3 시나리오 (design doc §4-3 extraction prompt 실체 검증):
  complete  — 완전 7 유저 턴 대화 → 8 필드 대부분 추출 성공 기대
  incomplete — 짧은 3 유저 턴 → 대부분 필드 no_data + fallback_needed 기대
  ambiguous — 모호/회피 응답 → 환각 없이 null + fallback_needed 기대

사용:
    cd sigak
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/probe_sonnet_extraction.py                    # complete
    python scripts/probe_sonnet_extraction.py --scenario all     # 3 전수
    python scripts/probe_sonnet_extraction.py --scenario ambiguous

Key 관리:
  os.environ["ANTHROPIC_API_KEY"] 에서만 읽음. commit 시 key 포함 0건.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.user_profile import ConversationMessage, ExtractionResult
from scripts.fixtures.sonnet_probe_data import (
    AMBIGUOUS,
    COMPLETE_7TURN,
    INCOMPLETE_3TURN,
)
from services import extraction


# ─────────────────────────────────────────────
#  Scenario runners
# ─────────────────────────────────────────────

def _parse_messages(raw: list[dict]) -> list[ConversationMessage]:
    return [ConversationMessage.model_validate(m) for m in raw]


def scenario_complete() -> tuple[list[ConversationMessage], ExtractionResult]:
    msgs = _parse_messages(COMPLETE_7TURN)
    result = extraction.extract_structured_fields(msgs)
    return msgs, result


def scenario_incomplete() -> tuple[list[ConversationMessage], ExtractionResult]:
    msgs = _parse_messages(INCOMPLETE_3TURN)
    result = extraction.extract_structured_fields(msgs)
    return msgs, result


def scenario_ambiguous() -> tuple[list[ConversationMessage], ExtractionResult]:
    msgs = _parse_messages(AMBIGUOUS)
    result = extraction.extract_structured_fields(msgs)
    return msgs, result


SCENARIOS = {
    "complete": scenario_complete,
    "incomplete": scenario_incomplete,
    "ambiguous": scenario_ambiguous,
}


# ─────────────────────────────────────────────
#  Audit
# ─────────────────────────────────────────────

def audit_extraction(name: str, msgs, result: ExtractionResult) -> None:
    print("─" * 60)
    print(f"  [{name.upper()}] 입력: {len(msgs)} 턴")
    print("─" * 60)

    fields = result.fields
    conf = fields.confidence
    print("\n  === 추출 결과 ===")
    mapping = [
        ("desired_image", fields.desired_image),
        ("reference_style", fields.reference_style),
        ("current_concerns", fields.current_concerns),
        ("self_perception", fields.self_perception),
        ("lifestyle_context", fields.lifestyle_context),
        ("height", fields.height),
        ("weight", fields.weight),
        ("shoulder_width", fields.shoulder_width),
    ]
    for k, v in mapping:
        c = getattr(conf, k, 0.0) if conf else 0.0
        status = "null" if v is None else repr(v)
        print(f"  {k:20s} conf={c:.2f}  {status}")

    print(f"\n  fallback_needed: {result.fallback_needed}")
    print()

    # 시나리오별 기대 자동 체크
    if name == "complete":
        _check_complete(result)
    elif name == "incomplete":
        _check_incomplete(result)
    elif name == "ambiguous":
        _check_ambiguous(result)


def _check_complete(result: ExtractionResult):
    """완전 대화 — 최소 5 필드 이상 추출 성공 기대."""
    fields = result.fields
    populated = sum(1 for v in [
        fields.desired_image, fields.current_concerns, fields.self_perception,
        fields.lifestyle_context, fields.height, fields.weight,
        fields.shoulder_width, fields.reference_style,
    ] if v is not None)
    print("  === 기대 체크 (complete) ===")
    mark = "✓" if populated >= 5 else "✗"
    print(f"  [{mark}] populated 필드 수 {populated}/8 (기대 ≥5)")

    # height / weight / shoulder_width 특별 확인 (대화에 "165 / 50 초반 / 어깨 보통")
    print(f"  [{'✓' if fields.height else '✗'}] height 추출됨 (대화에 '165' 명시)")
    print(f"  [{'✓' if fields.weight else '✗'}] weight 추출됨 (대화에 '50 초반' 명시)")
    print(f"  [{'✓' if fields.shoulder_width else '✗'}] shoulder_width 추출됨 (대화에 '어깨 보통' 명시)")


def _check_incomplete(result: ExtractionResult):
    """짧은 대화 — 대부분 fallback_needed."""
    fields = result.fields
    print("  === 기대 체크 (incomplete) ===")

    # desired_image 는 "편안하게" 언급됐으므로 populated OK
    di_ok = fields.desired_image is not None
    print(f"  [{'✓' if di_ok else '✗'}] desired_image 최소 추출 (유저 '편안하게' 언급)")

    # 나머지 6 필드 (reference/concerns/self/lifestyle/height/weight/shoulder) 는 모두 null + fallback
    should_be_null = [
        "reference_style", "self_perception",
        "lifestyle_context", "height", "weight", "shoulder_width",
    ]
    null_count = sum(1 for f in should_be_null if getattr(fields, f) is None)
    print(f"  [{'✓' if null_count >= 5 else '✗'}] 언급 없는 필드 null 처리 {null_count}/6 (기대 ≥5)")

    # fallback_needed 에 6 필드 중 최소 4개 이상 포함 기대
    in_fallback = sum(1 for f in should_be_null if f in result.fallback_needed)
    print(f"  [{'✓' if in_fallback >= 4 else '✗'}] fallback_needed 에 미수집 필드 기재 {in_fallback}/6 (기대 ≥4)")


def _check_ambiguous(result: ExtractionResult):
    """모호한 답변 — 환각 감지. 유저가 직접 말한 것만 추출, 나머지는 null + fallback."""
    fields = result.fields
    print("  === 기대 체크 (ambiguous) ===")

    # desired_image: "잘 모르겠어요 / 상황마다 다름" 만 있음 → 추출 불가능 (null 또는 매우 낮은 confidence)
    # 유저 환각 감지: desired_image 에 구체적 방향 값 있으면 환각 의심
    di = fields.desired_image
    if di is None:
        print(f"  [✓] desired_image null (유저 회피 응답)")
    else:
        # "모르겠음" / "상황마다 다름" 같은 표현이면 OK, 구체 방향은 환각
        if any(keyword in di for keyword in ["모르", "상황", "다양", "정해", "다름"]):
            print(f"  [✓] desired_image = {di!r} (모호성 반영, 구체 환각 아님)")
        else:
            print(f"  [✗] desired_image = {di!r} — 환각 의심 (유저는 구체 방향 말 안 했음)")

    # 체형 — 유저 "말하기 그래요, 넘어갈게요" → 전부 null
    print(f"  [{'✓' if fields.height is None else '✗'}] height null (유저 skip)")
    print(f"  [{'✓' if fields.weight is None else '✗'}] weight null (유저 skip)")
    print(f"  [{'✓' if fields.shoulder_width is None else '✗'}] shoulder_width null (유저 skip)")

    # fallback_needed 에 3 체형 필드 전부 포함 기대
    bods = ["height", "weight", "shoulder_width"]
    in_fb = sum(1 for f in bods if f in result.fallback_needed)
    print(f"  [{'✓' if in_fb == 3 else '✗'}] fallback_needed 체형 3필드 전부 포함 {in_fb}/3")


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sonnet 4.6 extraction live probe")
    parser.add_argument(
        "--scenario",
        default="complete",
        choices=["complete", "incomplete", "ambiguous", "all"],
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set (env only, .env 읽기 금지)")
        sys.exit(1)

    print("=" * 60)
    print("  SONNET 4.6 EXTRACTION LIVE PROBE")
    print("=" * 60)

    targets = ["complete", "incomplete", "ambiguous"] if args.scenario == "all" else [args.scenario]

    for name in targets:
        runner = SCENARIOS[name]
        print(f"\n>>> 시나리오 [{name}] 호출 중...\n")
        try:
            msgs, result = runner()
            audit_extraction(name, msgs, result)
        except extraction.ExtractionError as e:
            print(f"  [✗] ExtractionError: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
