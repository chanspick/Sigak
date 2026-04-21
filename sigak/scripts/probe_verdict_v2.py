"""Verdict 2.0 live probe with Sonnet 4.6 vision (Priority 1 D5 Phase 2~3).

실 Sonnet 4.6 vision 호출 3 시나리오:
  1photo   — 사진 1장 (정면 얼굴)
  3photos  — 사진 3장 (다양한 각도/상황)
  10photos — 사진 10장 (스트레스 테스트)

비용 고지:
  Sonnet 4.6 vision ~$0.075/call × 3 = ~$0.23
  D5 Phase 2/3 검수.

사용:
    cd sigak
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/probe_verdict_v2.py                                  # AM 3 시나리오
    python scripts/probe_verdict_v2.py --scenario 3photos               # 단일 시나리오
    python scripts/probe_verdict_v2.py --scenario 1photo --gender af    # Flag 1 검증용

Fixture 이미지:
  SCUT-FBP5500 AM (Asian Male) 또는 AF (Asian Female) 샘플 재사용.
  --gender am (default) / af 로 성별 전환.
  base64 인코딩 후 Sonnet 에 전송.

Flag 1 검증 (2026-04-21):
  Phase 2 probe 에서 AM 이미지 + female profile → alignment="상충"은
  성별 구조 mismatch 때문. --gender af 로 female 이미지 + female profile
  재시도 시 alignment 가 "일치"/"부분 일치" 로 바뀌는지 확인하면
  prompt 편향 검증 완료.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.verdict_v2 import VerdictV2Result
from services import verdict_v2
from services.sia_validators import find_violations


# ─────────────────────────────────────────────
#  Image fixtures — SCUT AM / AF 샘플
# ─────────────────────────────────────────────

SCUT_IMAGE_DIR = Path(__file__).resolve().parent.parent.parent / "experiments" / "scut-fbp5500" / "SCUT-FBP5500_v2" / "Images"

AM_CANDIDATES = ["AM1.jpg", "AM2.jpg", "AM5.jpg", "AM10.jpg", "AM20.jpg",
                 "AM50.jpg", "AM100.jpg", "AM200.jpg", "AM500.jpg", "AM1000.jpg"]

AF_CANDIDATES = ["AF1.jpg", "AF2.jpg", "AF5.jpg", "AF10.jpg", "AF20.jpg",
                 "AF50.jpg", "AF100.jpg", "AF200.jpg", "AF500.jpg", "AF1000.jpg"]

# 현재 실행에서 선택된 후보 리스트. main() 에서 --gender 로 세팅.
_ACTIVE_CANDIDATES: list[str] = AM_CANDIDATES


def _load_photo_as_base64(filename: str) -> dict:
    """SCUT 이미지 → Sonnet PhotoInput (base64)."""
    path = SCUT_IMAGE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"image not found: {path}")
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return {"base64": b64, "media_type": "image/jpeg"}


def _load_n_photos(n: int) -> list[dict]:
    """_ACTIVE_CANDIDATES 에서 처음 n 장 로드."""
    photos = []
    for fname in _ACTIVE_CANDIDATES[:n]:
        photos.append(_load_photo_as_base64(fname))
    if len(photos) != n:
        raise RuntimeError(f"requested {n} photos, loaded {len(photos)}")
    return photos


# ─────────────────────────────────────────────
#  Mock user_profile (D4 extraction complete scenario 재사용)
# ─────────────────────────────────────────────

MOCK_USER_PROFILE = {
    "user_id": "probe_user",
    "gender": "female",
    "birth_date": "1999-03-15",
    "ig_handle": "test_user",
    "structured_fields": {
        "desired_image": "편안하고 친밀한 인상 추구, 세련된 거리감은 밀어둠",
        "reference_style": "한소희 초반",
        "current_concerns": ["추구미와 피드 분위기 갭"],
        "self_perception": "정돈된 인상이라는 평을 자주 받음",
        "lifestyle_context": "프리랜서 기획자, 주말 친구들과 캐주얼",
        "height": "165_170",
        "weight": "50_55",
        "shoulder_width": "medium",
    },
    "ig_feed_cache": {
        "scope": "full",
        "profile_basics": {
            "username": "test_user",
            "follower_count": 3200,
            "post_count": 38,
        },
        "current_style_mood": [
            {"tag": "쿨뮤트", "ratio": 0.68},
            {"tag": "미니멀", "ratio": 0.22},
        ],
        "style_trajectory": "3개월간 톤 점진적 다운",
        "feed_highlights": [
            "차분한 주말", "뮤트 톤 기록", "조용한 저녁",
        ],
    },
}


# ─────────────────────────────────────────────
#  Scenarios
# ─────────────────────────────────────────────

def scenario_1_photo():
    photos = _load_n_photos(1)
    return verdict_v2.build_verdict_v2(
        user_profile=MOCK_USER_PROFILE,
        photos=photos,
    )


def scenario_3_photos():
    photos = _load_n_photos(3)
    return verdict_v2.build_verdict_v2(
        user_profile=MOCK_USER_PROFILE,
        photos=photos,
    )


def scenario_10_photos():
    photos = _load_n_photos(10)
    return verdict_v2.build_verdict_v2(
        user_profile=MOCK_USER_PROFILE,
        photos=photos,
    )


SCENARIOS = {
    "1photo": (scenario_1_photo, 1),
    "3photos": (scenario_3_photos, 3),
    "10photos": (scenario_10_photos, 10),
}


# ─────────────────────────────────────────────
#  Audit
# ─────────────────────────────────────────────

def _collect_user_text(result: VerdictV2Result) -> str:
    parts = [
        result.preview.hook_line,
        result.preview.reason_summary,
        result.full_content.verdict,
    ]
    for pi in result.full_content.photo_insights:
        parts.append(pi.insight)
        parts.append(pi.improvement)
    rec = result.full_content.recommendation
    parts.append(rec.style_direction)
    parts.append(rec.next_action)
    parts.append(rec.why)
    cta = result.full_content.cta_pi
    if cta is not None:
        parts.append(cta.headline)
        parts.append(cta.body)
        parts.append(cta.action_label)
    return "\n".join(parts)


def audit(name: str, expected_photos: int, result: VerdictV2Result) -> None:
    print("─" * 60)
    print(f"  [{name.upper()}] Sonnet 4.6 응답 (expected {expected_photos} photos)")
    print("─" * 60)

    # Preview
    print("\n  === preview ===")
    print(f"  hook_line      [{len(result.preview.hook_line)}자]")
    print(f"                 {result.preview.hook_line}")
    print(f"  reason_summary [{len(result.preview.reason_summary)}자]")
    print(f"                 {result.preview.reason_summary}")

    # Full content
    fc = result.full_content
    print("\n  === full_content.verdict ===")
    print(f"  [{len(fc.verdict)}자]  {fc.verdict}")

    print(f"\n  === photo_insights ({len(fc.photo_insights)}) ===")
    for pi in fc.photo_insights[:3]:
        print(f"  photo {pi.photo_index}:")
        print(f"    insight    : {pi.insight[:120]}")
        print(f"    improvement: {pi.improvement[:120]}")
    if len(fc.photo_insights) > 3:
        print(f"  ... (나머지 {len(fc.photo_insights) - 3} 개 생략)")

    print(f"\n  === recommendation ===")
    rec = fc.recommendation
    print(f"  style_direction: {rec.style_direction}")
    print(f"  next_action    : {rec.next_action}")
    print(f"  why            : {rec.why}")

    print(f"\n  === numbers ===")
    print(f"  {fc.numbers.model_dump_json()}")

    # cta_pi (D5 Phase 3)
    cta = fc.cta_pi
    if cta is not None:
        print(f"\n  === cta_pi (시각이 본 나 CTA) ===")
        print(f"  headline     [{len(cta.headline)}자]: {cta.headline}")
        print(f"  body         [{len(cta.body)}자]: {cta.body}")
        print(f"  action_label [{len(cta.action_label)}자]: {cta.action_label}")
        # PI 단어 유출 여부 (소프트 체크 — validator 미포함)
        combined_cta = f"{cta.headline} {cta.body} {cta.action_label}"
        pi_literal_hits = [
            tok for tok in combined_cta.split()
            if tok.strip(".,!?()[]{}:;\"'") in ("PI", "pi")
        ]
        if pi_literal_hits:
            print(f"  ⚠ PI 단어 유출: {pi_literal_hits}")
        else:
            print(f"  ✓ PI 단어 미유출")
    else:
        print(f"\n  ⚠ cta_pi 누락 — Sonnet 이 cta_pi 섹션 미생성")

    # Validation
    print(f"\n  === Hard Rules 검증 ===")
    combined = _collect_user_text(result)
    violations = find_violations(combined)
    blocking = {"HR1_verdict", "HR2_judgment", "HR3_markdown", "HR4_bullet",
                "HR5_emoji", "eval_language", "confirmation"}
    bad = {k: violations[k] for k in violations if k in blocking}
    if bad:
        print(f"  ❌ Hard violation:")
        for k, v in bad.items():
            print(f"    {k}: {v}")
    else:
        print(f"  ✓ Hard Rules 전수 통과")

    # Schema counts
    expected_insights = expected_photos
    actual_insights = len(fc.photo_insights)
    mark = "✓" if actual_insights == expected_insights else "⚠"
    print(f"  [{mark}] photo_insights 수: {actual_insights} (expected {expected_insights})")

    # Numbers populated
    n = fc.numbers
    print(f"  [{'✓' if n.photo_count == expected_photos else '⚠'}] numbers.photo_count: {n.photo_count}")
    print(f"  [{'✓' if n.dominant_tone else '·'}] numbers.dominant_tone: {n.dominant_tone}")
    print(f"  [{'✓' if n.alignment_with_profile else '·'}] numbers.alignment: {n.alignment_with_profile}")


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main():
    global _ACTIVE_CANDIDATES

    parser = argparse.ArgumentParser(description="Verdict 2.0 live probe (Sonnet vision)")
    parser.add_argument(
        "--scenario",
        default="all",
        choices=["1photo", "3photos", "10photos", "all"],
    )
    parser.add_argument(
        "--gender",
        default="am",
        choices=["am", "af"],
        help="SCUT 샘플 성별. am=Asian Male, af=Asian Female. "
             "Flag 1 검증 시 'af' 로 female profile 과 매칭된 케이스 실증.",
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set (env only, .env 읽기 금지)")
        sys.exit(1)

    if not SCUT_IMAGE_DIR.exists():
        print(f"ERROR: SCUT image dir not found: {SCUT_IMAGE_DIR}")
        sys.exit(1)

    # --gender 선택 반영
    _ACTIVE_CANDIDATES = AF_CANDIDATES if args.gender == "af" else AM_CANDIDATES
    gender_label = "Asian Female (AF)" if args.gender == "af" else "Asian Male (AM)"

    print("=" * 60)
    print("  VERDICT 2.0 LIVE PROBE — Sonnet 4.6 vision")
    print(f"  샘플: {gender_label}")
    print(f"  Profile gender (mock): {MOCK_USER_PROFILE['gender']}")
    print(f"  비용: Sonnet vision call × {'3' if args.scenario == 'all' else '1'}")
    print("=" * 60)

    targets = ["1photo", "3photos", "10photos"] if args.scenario == "all" else [args.scenario]

    for name in targets:
        runner, expected = SCENARIOS[name]
        print(f"\n>>> 시나리오 [{name}] 호출 중...\n")
        try:
            result = runner()
            audit(name, expected, result)
        except verdict_v2.VerdictV2Error as e:
            print(f"  ❌ VerdictV2Error: {e}")
        except FileNotFoundError as e:
            print(f"  ❌ 이미지 누락: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
