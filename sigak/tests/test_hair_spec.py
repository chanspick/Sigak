"""
hair_spec 엔진 E2E 단위 테스트
레어리 "서연" 케이스 재현: 짧은 육각형, 짧은 이마, 긴 중안부, 사각턱
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.hair_spec import build_hair_spec, extract_active_features


# ── 서연 케이스 ──
SUYEON_FACE = {
    "face_shape": "hexagon",
    "forehead_ratio": 0.22,     # 짧은 이마
    "philtrum_ratio": 0.40,     # 긴 인중/중안부
    "jaw_angle": 110,           # 사각턱
    "cheekbone_prominence": 0.30,  # 옆광대 낮음
    "nose_width_ratio": 0.32,   # 코 큰 편
    "face_length_ratio": 0.95,  # 짧은 편
}

SUYEON_INTERVIEW = {
    "neck_length": "short",
    "shoulder_width": "narrow",
    "hair_volume": "medium",
    "hair_texture": "straight",
    "hair_thickness": "medium",
    "face_concerns": "wide_face,short_forehead,square_jaw,mouth_protrusion,large_nose",
    "style_image_keywords": "elegant,chic",
    "desired_image": "모던하면서도 여리여리한 느낌",
}


def test_active_features():
    """서연 케이스에서 올바른 feature flag 추출 확인."""
    active = extract_active_features(SUYEON_FACE, SUYEON_INTERVIEW)
    print("ACTIVE FEATURES:", active)

    assert "face_wide_short" in active, "짧은 육각형 → face_wide_short 활성화"
    assert "short_forehead" in active, "이마 비율 0.22 → short_forehead"
    assert "long_midface" in active, "인중 비율 0.40 → long_midface"
    assert "square_jaw" in active, "턱각도 110 → square_jaw"
    assert "short_neck" in active, "설문 neck_length=short"
    assert "narrow_shoulders" in active, "설문 shoulder_width=narrow"
    assert "mouth_protrusion" in active, "face_concerns에 mouth_protrusion"
    assert "large_nose" in active, "코 너비 0.32 or face_concerns"
    print("  → 모든 feature flag 정상 활성화 ✓")


def test_scoring_basic():
    """스코어링 기본 동작 확인."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)

    assert "cheat_sheet" in result
    assert "top_combos" in result
    assert "avoid" in result
    assert "front_styles" in result
    assert "back_styles" in result
    assert "global_conditions" in result
    print("  → 모든 필수 필드 존재 ✓")

    # 스타일 수 확인
    assert len(result["front_styles"]) == 8, f"앞머리 8종 필요, 실제: {len(result['front_styles'])}"
    assert len(result["back_styles"]) == 13, f"뒷머리 13종 필요, 실제: {len(result['back_styles'])}"
    print(f"  → 앞머리 {len(result['front_styles'])}종, 뒷머리 {len(result['back_styles'])}종 ✓")


def test_top_combo_ranking():
    """TOP 3 조합 결과 검증."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)
    combos = result["top_combos"]

    assert len(combos) == 3, f"TOP 3 필요, 실제: {len(combos)}"
    assert combos[0]["rank"] == 1
    assert combos[0]["combined_score"] >= combos[1]["combined_score"]
    assert combos[1]["combined_score"] >= combos[2]["combined_score"]
    print(f"  → TOP 3 정렬 정상 ✓")

    # 서연 케이스에서 비대칭 사이드뱅(h-f04)이 TOP에 있어야 함
    top_fronts = [c["front_id"] for c in combos]
    assert "h-f04" in top_fronts, f"비대칭 사이드뱅이 TOP 3에 없음: {top_fronts}"
    print(f"  → h-f04 (비대칭 사이드뱅) TOP 3 포함 ✓")

    for c in combos:
        print(f"    #{c['rank']} {c['front_name']} × {c['back_name']}  "
              f"score={c['combined_score']:.3f}  cross={c['cross_effect']:+.2f}")


def test_avoid_list():
    """AVOID 리스트 검증."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)
    avoid = result["avoid"]

    assert len(avoid) > 0, "서연 케이스에서 AVOID 리스트 비어있으면 안 됨"
    avoid_ids = [a["style_id"] for a in avoid]

    # 풀뱅(h-f01)과 단발S컬(h-b05)은 강하게 감점되어 AVOID에 있어야 함
    assert "h-f01" in avoid_ids, f"풀뱅이 AVOID에 없음: {avoid_ids}"
    assert "h-b05" in avoid_ids, f"단발S컬이 AVOID에 없음: {avoid_ids}"
    print(f"  → AVOID {len(avoid)}개: {[a['name_kr'] for a in avoid]} ✓")


def test_global_conditions():
    """글로벌 조건 검증."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)
    gc = result["global_conditions"]

    assert "root_volume" in gc, "짧은 이마 → 뿌리볼륨 필수"
    assert gc["root_volume"]["required"] is True
    print(f"  → 뿌리볼륨 필수: {gc['root_volume']['salon_instruction'][:40]}... ✓")

    assert "neck_clearance" in gc, "짧은 목 → 목선 관리 필요"
    print(f"  → 목선 관리: {gc['neck_clearance']['salon_instruction'][:40]}... ✓")

    assert "asymmetric_parting" in gc, "사각턱 → 비대칭 가르마 권장"
    print(f"  → 비대칭 가르마 권장 ✓")


def test_cheat_sheet():
    """치트시트 문자열 검증."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)
    cs = result["cheat_sheet"]

    assert len(cs) > 10, f"치트시트가 너무 짧음: '{cs}'"
    assert "뿌리볼륨" in cs, f"치트시트에 뿌리볼륨 언급 필요: '{cs}'"
    print(f"  → 치트시트: \"{cs}\" ✓")


def test_image_bonus():
    """이미지 벡터 보너스 검증 (elegant, chic 키워드)."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)

    # 우아/시크 키워드 → 해당 축 높은 스타일에 보너스
    front_scores = {s["style_id"]: s for s in result["front_styles"]}

    # h-f04 (비대칭 사이드뱅): 도도시크=0.6, 우아차분=0.7 → 보너스 높아야
    f04_bonus = front_scores["h-f04"]["image_bonus"]
    # h-f01 (풀뱅): 도도시크=0.2, 우아차분=0.2 → 보너스 낮아야
    f01_bonus = front_scores["h-f01"]["image_bonus"]

    assert f04_bonus > f01_bonus, f"h-f04 보너스({f04_bonus}) > h-f01 보너스({f01_bonus}) 필요"
    print(f"  → 이미지 보너스: h-f04={f04_bonus:.3f} > h-f01={f01_bonus:.3f} ✓")


def test_full_output_structure():
    """report_formatter 호환 구조 검증."""
    result = build_hair_spec(SUYEON_FACE, SUYEON_INTERVIEW)

    # report_content["hair_recommendation"]에 들어갈 구조
    assert "cheat_sheet" in result
    assert "top_combos" in result
    assert "avoid" in result

    # combo 필드 검증
    combo = result["top_combos"][0]
    assert "front_id" in combo
    assert "back_id" in combo
    assert "combined_score" in combo
    assert "rank" in combo

    # avoid 필드 검증
    av = result["avoid"][0]
    assert "style_id" in av
    assert "name_kr" in av
    assert "primary_reason" in av

    print("  → report_formatter 호환 구조 ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("SIGAK Hair Spec Engine — E2E Test (서연 케이스)")
    print("=" * 60)

    tests = [
        ("Feature 추출", test_active_features),
        ("스코어링 기본", test_scoring_basic),
        ("TOP 3 랭킹", test_top_combo_ranking),
        ("AVOID 리스트", test_avoid_list),
        ("글로벌 조건", test_global_conditions),
        ("치트시트", test_cheat_sheet),
        ("이미지 보너스", test_image_bonus),
        ("출력 구조", test_full_output_structure),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n── {name} ──")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{passed + failed} passed")
    if failed:
        print(f"  {failed} FAILED")
        sys.exit(1)
    else:
        print("  ALL PASSED ✓")
