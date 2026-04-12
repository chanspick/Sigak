"""
SIGAK build_hair_spec()
=======================
얼굴 분석 + 설문 → 헤어스타일 스코어링 → TOP 조합 + AVOID 리턴

Pipeline:
  face_features + interview + gap
    → extract_active_features()
    → score_all_styles()
    → generate_combos()
    → build output spec
    → LLM이 WHY 텍스트 생성 (이 함수 밖에서)
"""

from hair_styles import HAIR_STYLES, get_front_styles, get_back_styles, get_etc_styles
from hair_rules import (
    FEATURE_MODIFIERS,
    LENGTH_CONSTRAINTS,
    CROSS_EFFECTS,
    IMAGE_AXES,
    match_cross_effect,
    match_image_preference,
)


# ============================================================
# 1. Feature Extraction
# ============================================================

def extract_active_features(face_features: dict, interview: dict) -> list[str]:
    """
    face_features (InsightFace 분석) + interview (설문) →
    해당 유저에게 활성화되는 feature flag 리스트 반환.
    
    Returns: ["face_wide_short", "short_forehead", "square_jaw", ...]
    """
    active = []

    # ── 얼굴 가로/세로 비율 ──
    face_ratio = face_features.get("face_width_height_ratio", 1.0)
    length_mod = face_features.get("length_modifier", "balanced")
    if face_ratio > 1.05 or length_mod == "short":
        active.append("face_wide_short")
    elif face_ratio < 0.85 or length_mod == "long":
        active.append("face_long_narrow")

    # ── 이마 비율 ──
    forehead = face_features.get("forehead_ratio", "balanced")
    if forehead == "short":
        active.append("short_forehead")
    elif forehead == "long":
        active.append("long_forehead")

    # ── 중안부 비율 ──
    midface = face_features.get("midface_ratio", "balanced")
    if midface == "long":
        active.append("long_midface")

    # ── 인중 길이 ──
    philtrum = face_features.get("philtrum_length", "balanced")
    if philtrum == "long":
        active.append("long_philtrum")

    # ── 턱 골격 ──
    jaw = face_features.get("jaw_type", "balanced")
    if jaw in ("square", "angular"):
        active.append("square_jaw")

    # ── 광대 ──
    cheekbone = face_features.get("cheekbone_prominence", "balanced")
    if cheekbone == "low":
        active.append("no_cheekbone")
    elif cheekbone == "high":
        active.append("prominent_cheekbone")

    # ── 입돌출 ──
    mouth = face_features.get("mouth_protrusion", "none")
    if mouth in ("slight", "moderate", "prominent"):
        active.append("mouth_protrusion")

    # ── 코 크기 ──
    nose = face_features.get("nose_size", "balanced")
    if nose in ("large", "prominent"):
        active.append("large_nose")

    # ── 목 길이 (설문) ──
    neck = interview.get("neck_length", "normal")
    if neck == "short":
        active.append("short_neck")
    elif neck == "long":
        active.append("long_neck")

    # ── 어깨 너비 (설문) ──
    shoulder = interview.get("shoulder_width", "normal")
    if shoulder == "narrow":
        active.append("narrow_shoulders")
    elif shoulder == "wide":
        active.append("wide_shoulders")

    return active


# ============================================================
# 2. Style Scoring
# ============================================================

def score_style(style_id: str, active_features: list[str], interview: dict) -> dict:
    """
    단일 스타일에 대해 최종 스코어 계산.
    
    Returns: {
        "style_id": str,
        "score": float,
        "rating": int (1~3),
        "modifiers_applied": [{"feature": str, "mod": float, "reason": str}],
        "conditions": [...],
        "length_constraint": {...} or None,
        "image_bonus": float,
    }
    """
    style = HAIR_STYLES.get(style_id)
    if not style:
        return None

    base = style["base_score"]  # 0.5
    modifiers_applied = []
    conditions = []
    global_flags = {}

    # ── Feature modifiers 합산 ──
    for feature in active_features:
        feature_table = FEATURE_MODIFIERS.get(feature, {})
        
        # 글로벌 플래그 수집
        if "_global" in feature_table:
            global_flags.update(feature_table["_global"])

        style_mod = feature_table.get(style_id)
        if style_mod is None:
            continue

        mod_value = style_mod["mod"]
        reason = style_mod.get("reason", "")

        # 조건부 modifier 처리
        style_conditions = style_mod.get("conditions", [])
        for cond in style_conditions:
            if_field = cond.get("if_field", "")
            if_value = cond.get("if_value")
            
            # 설문/파생 데이터에서 조건 체크
            actual_value = _resolve_condition_field(if_field, interview, style)
            
            if actual_value == if_value:
                # 조건 충족 → 추가 modifier
                mod_value += cond.get("then_mod", 0)
                conditions.append({
                    "feature": feature,
                    "style_id": style_id,
                    "condition": if_field,
                    "matched": True,
                    "rescue": cond.get("rescue", ""),
                    "rescue_mod": cond.get("rescue_mod", 0),
                })
            
            # constraint 타입 (기장/컬 제한)
            if "constraint" in cond:
                conditions.append({
                    "feature": feature,
                    "style_id": style_id,
                    "constraint": cond["constraint"],
                    "detail": {k: v for k, v in cond.items() if k not in ("constraint",)},
                })

        modifiers_applied.append({
            "feature": feature,
            "mod": mod_value,
            "reason": reason,
        })

    # ── 이미지 벡터 보너스 ──
    style_vector = style.get("image_vector", [0.5] * 5)
    user_keywords = interview.get("style_keywords", [])
    if isinstance(user_keywords, str):
        user_keywords = [kw.strip() for kw in user_keywords.split(",")]
    image_bonus = match_image_preference(style_vector, user_keywords)

    # ── 최종 스코어 ──
    total_mod = sum(m["mod"] for m in modifiers_applied)
    final_score = base + total_mod + image_bonus
    final_score = max(0.0, min(1.0, final_score))  # clamp

    # ── Rating 변환 ──
    if final_score >= 0.7:
        rating = 3  # ★★★
    elif final_score >= 0.45:
        rating = 2  # ★★☆
    else:
        rating = 1  # ★☆☆

    # ── 기장 제한 ──
    length_constraint = LENGTH_CONSTRAINTS.get(style_id)

    return {
        "style_id": style_id,
        "name_kr": style["name_kr"],
        "name_en": style.get("name_en", ""),
        "category": style["category"],
        "score": round(final_score, 3),
        "rating": rating,
        "modifiers_applied": modifiers_applied,
        "conditions": conditions,
        "length_constraint": length_constraint,
        "image_bonus": image_bonus,
        "image_vector": style.get("image_vector"),
        "gaze_effect": style.get("gaze_effect"),
        "global_flags": global_flags,
    }


def _resolve_condition_field(field: str, interview: dict, style: dict):
    """조건 필드를 실제 값으로 해석."""
    if field == "hair_volume":
        return interview.get("hair_volume", "normal")
    elif field == "forehead_coverage_heavy":
        return style.get("forehead_coverage", 0) > 0.8
    elif field == "_root_volume":
        # 뿌리볼륨 적용 여부 — 기본적으로 False (아직 적용 안 된 상태)
        return False
    elif field == "curl_at_jaw_heavy":
        return style.get("volume_at_jaw") == "heavy"
    elif field == "bangs_length_over_chin":
        return False  # 기본값, 실제로는 기장감 데이터 필요
    elif field == "length_too_short":
        return False  # 기본값
    elif field == "tight_slick_back":
        return False  # 기본값
    return None


# ============================================================
# 3. Combo Generation
# ============================================================

def generate_combos(front_scores: list, back_scores: list, all_styles: dict,
                    top_n: int = 3) -> list:
    """
    앞머리 TOP × 뒷머리 TOP 조합 생성.
    cross_effect 반영 후 최종 정렬.
    """
    combos = []

    # 앞머리 상위 5개 × 뒷머리 상위 5개 = 최대 25개 후보
    front_top = sorted(front_scores, key=lambda x: x["score"], reverse=True)[:5]
    back_top = sorted(back_scores, key=lambda x: x["score"], reverse=True)[:5]

    for fs in front_top:
        for bs in back_top:
            front_style = all_styles[fs["style_id"]]
            back_style = all_styles[bs["style_id"]]

            cross_mod, cross_reasons = match_cross_effect(
                front_style, back_style, all_styles
            )

            combined = (fs["score"] + bs["score"]) / 2.0 + cross_mod
            combined = max(0.0, min(1.0, combined))

            combos.append({
                "front_id": fs["style_id"],
                "front_name": fs["name_kr"],
                "front_score": fs["score"],
                "back_id": bs["style_id"],
                "back_name": bs["name_kr"],
                "back_score": bs["score"],
                "cross_effect": cross_mod,
                "cross_reasons": cross_reasons,
                "combined_score": round(combined, 3),
            })

    # 최종 정렬
    combos.sort(key=lambda x: x["combined_score"], reverse=True)

    # 랭크 부여
    for i, combo in enumerate(combos[:top_n]):
        combo["rank"] = i + 1

    return combos[:top_n]


# ============================================================
# 4. Global Conditions
# ============================================================

def compute_global_conditions(active_features: list[str], interview: dict) -> dict:
    """전역 조건 (뿌리볼륨, 목선 관리 등) 계산."""
    conditions = {}

    if "short_forehead" in active_features:
        conditions["root_volume"] = {
            "required": True,
            "priority": "critical",
            "reason": "이마가 짧아 뿌리볼륨 없으면 하관이 부해 보임",
            "salon_instruction": "이마 바로 위 헤어라인쪽 뿌리볼륨펌 또는 매직기 뿌리볼륨 필수. 특히 확실히 살려주기.",
        }

    if "short_neck" in active_features:
        conditions["neck_clearance"] = {
            "required": True,
            "priority": "high",
            "reason": "목이 짧아 목선이 가려지면 답답해 보임",
            "salon_instruction": "목선이 가려지지 않도록 기장/컬 주의. 목 주변에만 컬감 강한 디자인 피하기.",
        }

    if "square_jaw" in active_features:
        conditions["asymmetric_parting"] = {
            "required": False,
            "priority": "recommended",
            "reason": "턱 골격이 있어 대칭 가르마보다 비대칭이 턱 부각을 줄임",
            "salon_instruction": "5:5 정가르마보다 6:4 또는 7:3 비대칭 가르마 권장.",
        }

    return conditions


# ============================================================
# 5. Main Entry Point
# ============================================================

def build_hair_spec(face_features: dict, interview: dict, gap: dict = None,
                    gender: str = "female") -> dict:
    """
    SIGAK 헤어 추천 스펙 생성.
    
    Args:
        face_features: InsightFace 분석 결과 (얼굴형, 비율, 이목구비)
        interview: 설문 응답 (neck_length, hair_volume, style_keywords 등)
        gap: 3축 갭 벡터 (shape, volume, age) — v2에서 이미지 매칭에 활용
        gender: "female" / "male"
    
    Returns:
        {
            "cheat_sheet": str,
            "global_conditions": {...},
            "front_styles": [...],      # 8종 전체 평가
            "back_styles": [...],       # 13종 전체 평가
            "etc_styles": [...],        # 3종 전체 평가
            "top_combos": [...],        # TOP 3 앞×뒤 조합
            "avoid": [...],             # WORST 리스트
            "active_features": [...],   # 디버그용
        }
    """
    # Step 1: 활성 feature 추출
    active_features = extract_active_features(face_features, interview)

    # Step 2: 전체 스타일 스코어링
    front_scores = []
    back_scores = []
    etc_scores = []

    for style_id, style in HAIR_STYLES.items():
        if style.get("has_rating") is False:
            continue  # 가르마 같은 non-rated 스타일 제외

        result = score_style(style_id, active_features, interview)
        if result is None:
            continue

        if style["category"] == "front":
            front_scores.append(result)
        elif style["category"] == "back":
            back_scores.append(result)
        elif style["category"] == "etc":
            etc_scores.append(result)

    # Step 3: 정렬
    front_scores.sort(key=lambda x: x["score"], reverse=True)
    back_scores.sort(key=lambda x: x["score"], reverse=True)
    etc_scores.sort(key=lambda x: x["score"], reverse=True)

    # Step 4: TOP 조합 생성
    top_combos = generate_combos(front_scores, back_scores, HAIR_STYLES, top_n=3)

    # Step 5: AVOID 리스트 (score < 0.35)
    avoid = []
    for scored in front_scores + back_scores + etc_scores:
        if scored["score"] < 0.35:
            primary_mod = max(scored["modifiers_applied"],
                            key=lambda m: abs(m["mod"]),
                            default={"feature": "unknown", "reason": ""})
            avoid.append({
                "style_id": scored["style_id"],
                "name_kr": scored["name_kr"],
                "category": scored["category"],
                "score": scored["score"],
                "rating": scored["rating"],
                "primary_reason": primary_mod["reason"],
                "primary_feature": primary_mod["feature"],
            })

    # Step 6: 글로벌 조건
    global_conditions = compute_global_conditions(active_features, interview)

    # Step 7: 치트시트 생성 (LLM 없이 룰 기반 1줄 요약)
    cheat_sheet = _generate_cheat_sheet(top_combos, global_conditions, avoid)

    return {
        "cheat_sheet": cheat_sheet,
        "global_conditions": global_conditions,
        "front_styles": front_scores,
        "back_styles": back_scores,
        "etc_styles": etc_scores,
        "top_combos": top_combos,
        "avoid": avoid,
        "active_features": active_features,
    }


def _generate_cheat_sheet(top_combos: list, global_conditions: dict,
                          avoid: list) -> str:
    """룰 기반 1줄 치트시트."""
    parts = []

    if top_combos:
        best = top_combos[0]
        parts.append(f"{best['front_name']} + {best['back_name']}")

    if global_conditions.get("root_volume", {}).get("required"):
        parts.append("뿌리볼륨 필수")

    if global_conditions.get("neck_clearance", {}).get("required"):
        parts.append("목선 노출 유지")

    if avoid:
        worst_names = [a["name_kr"] for a in avoid[:2]]
        parts.append(f"피하기: {', '.join(worst_names)}")

    return ". ".join(parts) + "." if parts else ""


# ============================================================
# 6. Test / Demo
# ============================================================

if __name__ == "__main__":
    # 레어리 보고서 "서연" 케이스 재현
    test_face = {
        "face_shape": "hexagon",
        "face_width_height_ratio": 1.1,  # 넓고 짧음
        "length_modifier": "short",
        "forehead_ratio": "short",
        "midface_ratio": "long",
        "philtrum_length": "long",
        "jaw_type": "square",
        "cheekbone_prominence": "low",
        "mouth_protrusion": "slight",
        "nose_size": "large",
    }

    test_interview = {
        "neck_length": "short",
        "shoulder_width": "narrow",
        "hair_volume": "normal",
        "hair_texture": "straight",
        "hair_thickness": "normal",
        "style_keywords": "차분, 세련된",
        "desired_image": "모던하면서도 여리여리한 느낌",
    }

    result = build_hair_spec(test_face, test_interview)

    print("=" * 60)
    print("CHEAT SHEET:", result["cheat_sheet"])
    print("=" * 60)

    print("\n── ACTIVE FEATURES ──")
    print(result["active_features"])

    print("\n── GLOBAL CONDITIONS ──")
    for k, v in result["global_conditions"].items():
        print(f"  {k}: {v['salon_instruction']}")

    print("\n── FRONT STYLES (앞머리) ──")
    for s in result["front_styles"]:
        stars = "★" * s["rating"] + "☆" * (3 - s["rating"])
        print(f"  {stars} {s['name_kr']:12s}  score={s['score']:.3f}  bonus={s['image_bonus']:.3f}")

    print("\n── BACK STYLES (뒷머리) ──")
    for s in result["back_styles"]:
        stars = "★" * s["rating"] + "☆" * (3 - s["rating"])
        print(f"  {stars} {s['name_kr']:16s}  score={s['score']:.3f}")

    print("\n── TOP 3 COMBOS ──")
    for c in result["top_combos"]:
        print(f"  #{c['rank']} {c['front_name']} + {c['back_name']}  "
              f"combined={c['combined_score']:.3f}  cross={c['cross_effect']:+.2f}")

    print("\n── AVOID ──")
    for a in result["avoid"]:
        print(f"  ❌ {a['name_kr']:16s}  score={a['score']:.3f}  reason: {a['primary_reason']}")
