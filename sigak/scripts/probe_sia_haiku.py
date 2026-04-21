"""Sia Haiku live probe — D3 검수용 스크립트.

6 시나리오 지원:
  opening  — 오프닝 (빈 collected_fields + IG 성공)
  midturn  — 중간 턴 (유저 "1번" 선택 직후)
  closing  — 클로징 (유저 "이만하면 됐어요" + 8 필드 수집 완료)
  ig_skip  — IG 수집 skipped (ig_handle 없음/IG_ENABLED=false)
  no_name  — 3순위 호칭 폴백 (user.name 없음, 애플 로그인)
  midturn_alt — 중간 턴 (유저 "2번" 선택 — 분기 자연 전환 확인)

사용:
    cd sigak
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/probe_sia_haiku.py                        # opening
    python scripts/probe_sia_haiku.py --scenario all         # 6 전수
    python scripts/probe_sia_haiku.py --scenario ig_skip     # 단일

Key 관리:
  ANTHROPIC_API_KEY 는 반드시 os.environ 에서만 읽음 (.env 읽기/commit 없음).
  CLI 플래그 또는 config 파일 주입 경로 없음 (의도적).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.fixtures.sia_probe_data import (
    ALL_FIELDS,
    FAKE_BODY_CONFIRM,
    FAKE_MIDTURN,
    FAKE_OPENING,
    FULL_COLLECTED,
    MOCK_IG_SKIPPED,
    MOCK_IG_SUCCESS,
)
from services.sia_llm import build_system_prompt, call_sia_turn_with_retry
from services.sia_validators import (
    HARD_CHARS,
    WARN_CHARS,
    count_sentences,
    find_violations,
    long_sentences,
    warn_sentences,
)


# ─────────────────────────────────────────────
#  Scenario runners
# ─────────────────────────────────────────────

def scenario_opening() -> tuple[str, str]:
    """오프닝 — 빈 collected_fields + IG 성공 + 1순위 호칭."""
    sp = build_system_prompt(
        user_name="정세현",
        resolved_name=None,
        collected_fields={},
        missing_fields=ALL_FIELDS,
        ig_feed_cache=MOCK_IG_SUCCESS,
    )
    response = call_sia_turn_with_retry(
        system_prompt=sp,
        messages_history=[{"role": "user", "content": "(대화 시작)"}],
    )
    return sp, response


def scenario_midturn(selection: str = "1번") -> tuple[str, str]:
    """중간 턴 — 유저가 오프닝 4지선다에서 특정 번호 선택."""
    collected = {"desired_image_draft": f"{selection} 선택"}
    sp = build_system_prompt(
        user_name="정세현",
        resolved_name=None,
        collected_fields=collected,
        missing_fields=ALL_FIELDS,
        ig_feed_cache=MOCK_IG_SUCCESS,
    )
    history = [
        {"role": "user", "content": "(대화 시작)"},
        {"role": "assistant", "content": FAKE_OPENING},
        {"role": "user", "content": f"{selection}이요"},
    ]
    response = call_sia_turn_with_retry(system_prompt=sp, messages_history=history)
    return sp, response


def scenario_midturn_alt() -> tuple[str, str]:
    """midturn 분기 — 유저 '2번' 선택 (거리감 있는 인상) 후 자연 전환 확인."""
    return scenario_midturn(selection="2번")


def scenario_closing() -> tuple[str, str]:
    """클로징 — 8 필드 완전 수집 + 유저 '이만하면 됐어요'."""
    sp = build_system_prompt(
        user_name="정세현",
        resolved_name=None,
        collected_fields=FULL_COLLECTED,
        missing_fields=[],
        ig_feed_cache=MOCK_IG_SUCCESS,
    )
    history = [
        {"role": "user", "content": "(대화 시작)"},
        {"role": "assistant", "content": FAKE_OPENING},
        {"role": "user", "content": "1번"},
        {"role": "assistant", "content": FAKE_MIDTURN},
        {"role": "user", "content": "자주 느낀다, 풀고 싶다"},
        {"role": "assistant", "content": (
            "갭 인식이 뚜렷한 분입니다.\n"
            "평소 주로 어디서 시간을 보내시는지 알려주십시오."
        )},
        {"role": "user", "content": "프리랜서 기획자고 주말은 친구들과 캐주얼하게 보냅니다"},
        {"role": "assistant", "content": FAKE_BODY_CONFIRM},
        {"role": "user", "content": "1번이요 (160대 후반, 50 초반, 어깨 보통)"},
        {"role": "user", "content": "이만하면 됐어요"},
    ]
    response = call_sia_turn_with_retry(system_prompt=sp, messages_history=history)
    return sp, response


def scenario_ig_skip() -> tuple[str, str]:
    """IG skipped — ig_feed_cache=None. 숫자 사용 금지 상태 오프닝."""
    sp = build_system_prompt(
        user_name="정세현",
        resolved_name=None,
        collected_fields={},
        missing_fields=ALL_FIELDS,
        ig_feed_cache=MOCK_IG_SKIPPED,
    )
    response = call_sia_turn_with_retry(
        system_prompt=sp,
        messages_history=[{"role": "user", "content": "(대화 시작)"}],
    )
    return sp, response


def scenario_no_name() -> tuple[str, str]:
    """3순위 호칭 폴백 — user_name=None (애플 로그인) + IG 성공."""
    sp = build_system_prompt(
        user_name=None,
        resolved_name=None,
        collected_fields={},
        missing_fields=ALL_FIELDS,
        ig_feed_cache=MOCK_IG_SUCCESS,
    )
    response = call_sia_turn_with_retry(
        system_prompt=sp,
        messages_history=[{"role": "user", "content": "(대화 시작)"}],
    )
    return sp, response


SCENARIOS = {
    "opening": scenario_opening,
    "midturn": scenario_midturn,
    "midturn_alt": scenario_midturn_alt,
    "closing": scenario_closing,
    "ig_skip": scenario_ig_skip,
    "no_name": scenario_no_name,
}


# ─────────────────────────────────────────────
#  Audit (본인 검수 체크리스트)
# ─────────────────────────────────────────────

def audit_response(text: str, expect_user_definition: bool = False,
                   expect_four_choice: bool = True,
                   expect_concrete_number: bool = True) -> dict:
    v = find_violations(text)
    bullets = [l for l in text.split("\n") if l.strip().startswith("- ")]
    number_list = re.findall(r"^\s*\d+\.\s", text, re.MULTILINE)

    # 구체 숫자 감지 — 단위 (장/개/%/배) + 순수 숫자 둘 다
    has_concrete_number = bool(re.search(r"\d+(장|개|명|%|배|턴|명)", text))

    # 유저 정의문 ("~분입니다") — 오프닝에서만 기대
    has_user_definition = bool(
        re.search(r"[가-힣]+\s*분입니다|인\s*분입니다|하시는\s*분입니다", text)
    )

    sentence_count = count_sentences(text)
    hard_over = long_sentences(text, max_chars=HARD_CHARS)
    warn = warn_sentences(text)

    return {
        "hr1_no_verdict": "HR1_verdict" not in v,
        "hr2_no_judgment": "HR2_judgment" not in v,
        "hr3_no_markdown": "HR3_markdown" not in v,
        "hr4_no_bullet_star": "HR4_bullet" not in v,
        "hr4plus_no_number_list": len(number_list) == 0,
        "hr5_no_emoji": "HR5_emoji" not in v,
        "no_forbidden_suffix": "tone_suffix" not in v,
        "has_formal_suffix": "tone_missing" not in v,
        "no_evaluation": "eval_language" not in v,
        "no_confirmation": "confirmation" not in v,
        "four_choice_hyphen": (len(bullets) == 4 and not number_list) if expect_four_choice else True,
        "concrete_number": has_concrete_number if expect_concrete_number else True,
        "user_definition": has_user_definition if expect_user_definition else True,
        "sentence_count": sentence_count,
        "hard_over_clauses": hard_over,      # >60자 (차단)
        "warn_clauses": warn,                 # 45-60자 (허용, metric)
        "raw_violations": v,
        "bullet_count": len(bullets),
        "number_list_count": len(number_list),
    }


def print_audit(name: str, response: str, audit: dict):
    print("─" * 60)
    print(f"  [{name.upper()}] Sia 응답")
    print("─" * 60)
    print(response)
    print("─" * 60)

    checks = [
        ("hr1_no_verdict",     'HR1 "verdict" 0건'),
        ("hr2_no_judgment",    'HR2 "판정" 0건'),
        ("hr3_no_markdown",    'HR3 마크다운 0건'),
        ("hr4_no_bullet_star", 'HR4 별표/중점 bullet 0건'),
        ("hr4plus_no_number_list", 'HR4+ 숫자 리스트 0건'),
        ("hr5_no_emoji",       'HR5 이모지 0건'),
        ("no_forbidden_suffix",'금지 어미 0건'),
        ("has_formal_suffix",  '서술형 정중체 어미 사용'),
        ("no_evaluation",      '평가 표현 없음'),
        ("no_confirmation",    '확인 요청 없음'),
        ("four_choice_hyphen", '4지선다 (하이픈 4줄)'),
        ("concrete_number",    '구체 숫자 포함'),
        ("user_definition",    '유저 정의문'),
    ]
    for key, label in checks:
        mark = "✓" if audit[key] else "✗"
        print(f"  [{mark}] {label}")

    sc = audit["sentence_count"]
    print(f"\n  문장 수: {sc}")

    hard = audit["hard_over_clauses"]
    warn = audit["warn_clauses"]
    if hard:
        print(f"  🔴 Hard violation ({HARD_CHARS}자 초과, 차단 대상) × {len(hard)}:")
        for c in hard:
            print(f"      [{len(c)}자] {c}")
    if warn:
        print(f"  🟡 Warning ({WARN_CHARS+1}-{HARD_CHARS}자, 허용) × {len(warn)}:")
        for c in warn:
            print(f"      [{len(c)}자] {c}")
    if not hard and not warn:
        print(f"  ✓ 모든 절 ≤{WARN_CHARS}자")

    print(f"  bullets: {audit['bullet_count']} / number_lists: {audit['number_list_count']}")


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sia Haiku live probe")
    parser.add_argument(
        "--scenario",
        default="opening",
        choices=["opening", "midturn", "midturn_alt", "closing",
                 "ig_skip", "no_name", "all"],
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set (env only — .env 파일 읽기 금지 정책)")
        sys.exit(1)

    print("=" * 60)
    print("  SIA HAIKU LIVE PROBE (iteration 3 — 정책 완화 + 엣지 케이스)")
    print(f"  policy: target={WARN_CHARS}자 / hard={HARD_CHARS}자")
    print("=" * 60)

    if args.scenario == "all":
        targets = ["opening", "midturn", "midturn_alt", "closing",
                   "ig_skip", "no_name"]
    else:
        targets = [args.scenario]

    for name in targets:
        runner = SCENARIOS[name]
        print(f"\n>>> 시나리오 [{name}] 호출 중...\n")
        _sp, response = runner()

        # 시나리오별 기대치 조정
        expect_def = name in ("opening", "ig_skip", "no_name")   # 오프닝에만 정의문 필수
        expect_4ch = name != "closing"                             # 클로징은 4지선다 없음
        expect_num = name not in ("ig_skip", "midturn", "midturn_alt", "closing")
        # ig_skip: IG 데이터 없음 → 숫자 사용 금지 (오히려 숫자 있으면 위반)
        # midturn/closing: 이미 받은 선택 재해석이라 숫자 강조 필요 약함

        audit = audit_response(
            response,
            expect_user_definition=expect_def,
            expect_four_choice=expect_4ch,
            expect_concrete_number=expect_num,
        )
        # ig_skip 은 "숫자 부재" 가 오히려 정답
        if name == "ig_skip":
            # 숫자 있으면 위반
            has_num = bool(re.search(r"\d+(장|개|%|배|명)", response))
            audit["concrete_number"] = not has_num   # invert — 숫자 없어야 통과

        print_audit(name, response, audit)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
