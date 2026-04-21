"""
SIGAK Hair Spec Engine
======================
얼굴 분석(CV) + 설문(interview) → 헤어스타일 스코어링 → TOP 조합 + AVOID

Pipeline:
  face_features + interview + gap
    → extract_active_features()
    → score_all_styles()
    → generate_combos()
    → build output spec
    → LLM이 WHY 텍스트 생성 (이 함수 밖에서)
"""

from pipeline.hair_styles import (
    HAIR_STYLES,
    get_front_styles,
    get_back_styles,
    get_etc_styles,
    get_complete_styles,
)
from pipeline.hair_rules import (
    FEATURE_MODIFIERS,
    LENGTH_CONSTRAINTS,
    match_cross_effect,
    match_image_preference,
)

# 트렌드 태그 — trend_data.py 기반
try:
    from pipeline.trend_data import HAIR_FRONT_TRENDS, HAIR_BACK_TRENDS
except ImportError:
    HAIR_FRONT_TRENDS, HAIR_BACK_TRENDS = {}, {}


def _get_trend_tag(front_id: str, back_id: str) -> str | None:
    """앞머리+뒷머리 평균 trend score → 태그 문자열."""
    scores = []
    if front_id in HAIR_FRONT_TRENDS:
        scores.append(HAIR_FRONT_TRENDS[front_id]["score"])
    if back_id in HAIR_BACK_TRENDS:
        scores.append(HAIR_BACK_TRENDS[back_id]["score"])
    if not scores:
        return None
    avg = sum(scores) / len(scores)
    if avg >= 0.7:
        return "🔥 트렌드"
    elif avg >= 0.3:
        return "▲ 상승"
    elif avg <= -0.5:
        return "↘ 하락"
    return None


# ============================================================
# 0. Face Features Bridge
# ============================================================
# face.py는 수치형(float), 스코어링 엔진은 카테고리형(str) 사용.
# 설문의 face_concerns를 교차 검증 시그널로 활용.

def _categorize_face_features(face_features: dict, interview: dict) -> dict:
    """수치형 FaceFeatures → 카테고리형 변환 (스코어링 엔진 입력용).

    CV 분석값과 유저 자가진단(face_concerns)을 교차 참조.
    """
    cat = {}

    # face_concerns: 유저 자가 진단 (multi_select, 쉼표 구분)
    concerns_raw = interview.get("face_concerns") or ""
    concerns = set(concerns_raw.split(",")) if concerns_raw else set()

    # ── 얼굴 가로/세로 비율 ──
    face_shape = face_features.get("face_shape", "oval")
    short_shapes = {"round", "square", "hexagon", "short_hexagon"}
    long_shapes = {"oblong", "long_diamond", "long"}

    if face_shape in short_shapes or "wide_face" in concerns or "short_face" in concerns:
        cat["length_modifier"] = "short"
        cat["face_width_height_ratio"] = 1.1
    elif face_shape in long_shapes or "long_face" in concerns:
        cat["length_modifier"] = "long"
        cat["face_width_height_ratio"] = 0.8
    else:
        cat["length_modifier"] = "balanced"
        cat["face_width_height_ratio"] = 1.0

    # ── 이마 비율 (수치 0~1 → 카테고리) ──
    fr = face_features.get("forehead_ratio", 0.33)
    if fr < 0.28 or "short_forehead" in concerns:
        cat["forehead_ratio"] = "short"
    elif fr > 0.38 or "wide_forehead" in concerns:
        cat["forehead_ratio"] = "long"
    else:
        cat["forehead_ratio"] = "balanced"

    # ── 중안부/인중 ──
    philtrum = face_features.get("philtrum_ratio", 0.33)
    if philtrum > 0.38 or "long_midface" in concerns:
        cat["midface_ratio"] = "long"
        cat["philtrum_length"] = "long"
    else:
        cat["midface_ratio"] = "balanced"
        cat["philtrum_length"] = "balanced"

    # ── 턱 골격 ──
    jaw_angle = face_features.get("jaw_angle", 125)
    if jaw_angle < 115 or "square_jaw" in concerns:
        cat["jaw_type"] = "square"
    else:
        cat["jaw_type"] = "balanced"

    # ── 광대 ──
    cheek = face_features.get("cheekbone_prominence", 0.5)
    if cheek > 0.65 or "prominent_cheekbone" in concerns:
        cat["cheekbone_prominence"] = "high"
    elif cheek < 0.35:
        cat["cheekbone_prominence"] = "low"
    else:
        cat["cheekbone_prominence"] = "balanced"

    # ── 입돌출 ──
    if "mouth_protrusion" in concerns:
        cat["mouth_protrusion"] = "slight"
    else:
        cat["mouth_protrusion"] = "none"

    # ── 코 크기 ──
    nose_w = face_features.get("nose_width_ratio", 0.25)
    if nose_w > 0.30 or "large_nose" in concerns:
        cat["nose_size"] = "large"
    else:
        cat["nose_size"] = "balanced"

    return cat


# ============================================================
# 1. Feature Extraction
# ============================================================

def extract_active_features(face_features: dict, interview: dict) -> list[str]:
    """face_features(CV) + interview(설문) → 활성 feature flag 리스트."""
    cat = _categorize_face_features(face_features, interview)
    active = []

    # 얼굴 가로/세로
    if cat["face_width_height_ratio"] > 1.05 or cat["length_modifier"] == "short":
        active.append("face_wide_short")

    # 이마
    if cat["forehead_ratio"] == "short":
        active.append("short_forehead")

    # 중안부
    if cat["midface_ratio"] == "long":
        active.append("long_midface")

    # 인중
    if cat["philtrum_length"] == "long":
        active.append("long_philtrum")

    # 턱
    if cat["jaw_type"] in ("square", "angular"):
        active.append("square_jaw")

    # 광대
    if cat["cheekbone_prominence"] == "low":
        active.append("no_cheekbone")

    # 입돌출
    if cat["mouth_protrusion"] != "none":
        active.append("mouth_protrusion")

    # 코
    if cat["nose_size"] in ("large", "prominent"):
        active.append("large_nose")

    # 목 길이 (설문)
    neck = interview.get("neck_length", "medium")
    if neck == "short":
        active.append("short_neck")

    # 어깨 너비 (설문)
    shoulder = interview.get("shoulder_width", "medium")
    if shoulder == "narrow":
        active.append("narrow_shoulders")

    return active


# ============================================================
# 2. Style Scoring
# ============================================================

def score_style(style_id: str, active_features: list[str], interview: dict) -> dict | None:
    """단일 스타일 최종 스코어 계산."""
    style = HAIR_STYLES.get(style_id)
    if not style:
        return None

    base = style["base_score"]
    modifiers_applied = []
    conditions = []
    global_flags = {}

    for feature in active_features:
        feature_table = FEATURE_MODIFIERS.get(feature, {})

        if "_global" in feature_table:
            global_flags.update(feature_table["_global"])

        style_mod = feature_table.get(style_id)
        if style_mod is None:
            continue

        mod_value = style_mod["mod"]
        reason = style_mod.get("reason", "")

        for cond in style_mod.get("conditions", []):
            if_field = cond.get("if_field", "")
            if_value = cond.get("if_value")

            actual_value = _resolve_condition_field(if_field, interview, style)

            if actual_value == if_value:
                mod_value += cond.get("then_mod", 0)
                conditions.append({
                    "feature": feature,
                    "style_id": style_id,
                    "condition": if_field,
                    "matched": True,
                    "rescue": cond.get("rescue", ""),
                    "rescue_mod": cond.get("rescue_mod", 0),
                })

            if "constraint" in cond:
                conditions.append({
                    "feature": feature,
                    "style_id": style_id,
                    "constraint": cond["constraint"],
                    "detail": {k: v for k, v in cond.items() if k != "constraint"},
                })

        modifiers_applied.append({
            "feature": feature,
            "mod": mod_value,
            "reason": reason,
        })

    # 이미지 벡터 보너스
    style_vector = style.get("image_vector", [0.5] * 5)
    user_keywords = _get_user_keywords(interview)
    image_bonus = match_image_preference(style_vector, user_keywords)

    # 최종 스코어 (clamp 없이 raw 유지 — combo 정렬에서 변별력 확보)
    total_mod = sum(m["mod"] for m in modifiers_applied)
    raw_score = base + total_mod + image_bonus
    display_score = max(0.0, min(1.0, raw_score))  # 표시용만 clamp

    # Rating (display 기준)
    if display_score >= 0.7:
        rating = 3
    elif display_score >= 0.45:
        rating = 2
    else:
        rating = 1

    return {
        "style_id": style_id,
        "name_kr": style["name_kr"],
        "name_en": style.get("name_en", ""),
        "category": style["category"],
        "score": round(raw_score, 3),       # raw (combo 정렬용)
        "score_display": round(display_score, 3),  # clamped (UI 표시용)
        "rating": rating,
        "modifiers_applied": modifiers_applied,
        "conditions": conditions,
        "length_constraint": LENGTH_CONSTRAINTS.get(style_id),
        "image_bonus": image_bonus,
        "image_vector": style.get("image_vector"),
        "gaze_effect": style.get("gaze_effect"),
        "global_flags": global_flags,
    }


def _get_user_keywords(interview: dict) -> list[str]:
    """설문에서 이미지 키워드 추출 (신규 style_image_keywords 우선, 레거시 style_keywords 폴백)."""
    raw = interview.get("style_image_keywords") or interview.get("style_keywords") or ""
    if isinstance(raw, list):
        return raw
    if not raw:
        return []
    return [kw.strip() for kw in raw.split(",") if kw.strip()]


def _resolve_condition_field(field: str, interview: dict, style: dict):
    """조건 필드를 실제 값으로 해석."""
    if field == "hair_volume":
        return interview.get("hair_volume", "medium")
    elif field == "forehead_coverage_heavy":
        return style.get("forehead_coverage", 0) > 0.8
    elif field == "_root_volume":
        return False  # 아직 미적용 상태
    elif field == "curl_at_jaw_heavy":
        return style.get("volume_at_jaw") == "heavy"
    elif field == "bangs_length_over_chin":
        return False
    elif field == "length_too_short":
        return False
    elif field == "tight_slick_back":
        return False
    return None


# ============================================================
# 3. Combo Generation
# ============================================================

def generate_combos(front_scores: list, back_scores: list,
                    global_conditions: dict,
                    top_n: int = 3) -> list:
    """앞머리 TOP × 뒷머리 TOP 조합 생성 + cross_effect + WHY + salon 지시문."""
    combos = []

    front_top = sorted(front_scores, key=lambda x: x["score"], reverse=True)[:5]
    back_top = sorted(back_scores, key=lambda x: x["score"], reverse=True)[:5]

    for fs in front_top:
        for bs in back_top:
            front_style = HAIR_STYLES[fs["style_id"]]
            back_style = HAIR_STYLES[bs["style_id"]]

            cross_mod, cross_reasons = match_cross_effect(
                front_style, back_style, HAIR_STYLES
            )

            combined = (fs["score"] + bs["score"]) / 2.0 + cross_mod

            # WHY: 앞머리 + 뒷머리 주요 이유 조합
            why_parts = []
            for m in fs.get("modifiers_applied", []):
                if m["mod"] > 0 and m["reason"]:
                    why_parts.append(m["reason"])
            for m in bs.get("modifiers_applied", []):
                if m["mod"] > 0 and m["reason"]:
                    why_parts.append(m["reason"])
            if cross_reasons:
                why_parts.extend(cross_reasons)
            # 상위 3개만
            why_text = ". ".join(why_parts[:3]) + "." if why_parts else ""

            # Salon 지시문: 스타일 구체 지시 + 기장 제한 + 글로벌 조건
            salon_parts = []
            front_lc = fs.get("length_constraint")
            if front_lc and front_lc.get("salon_note"):
                salon_parts.append(front_lc["salon_note"])
            back_lc = bs.get("length_constraint")
            if back_lc and back_lc.get("salon_note"):
                salon_parts.append(back_lc["salon_note"])
            for gc in global_conditions.values():
                if gc.get("required") and gc.get("salon_instruction"):
                    salon_parts.append(gc["salon_instruction"])
            salon_text = ". ".join(salon_parts) + "." if salon_parts else ""

            # 트렌드 태그 (trend_data.py 기반)
            trend_tag = _get_trend_tag(fs["style_id"], bs["style_id"])

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
                "why": why_text,
                "salon_instruction": salon_text,
                "trend": trend_tag,
            })

    combos.sort(key=lambda x: x["combined_score"], reverse=True)

    for i, combo in enumerate(combos[:top_n]):
        combo["rank"] = i + 1

    return combos[:top_n]


# ============================================================
# 4. Global Conditions
# ============================================================

def compute_global_conditions(active_features: list[str], interview: dict) -> dict:
    """전역 조건 (뿌리볼륨, 목선, 가르마 등)."""
    conditions = {}

    if "short_forehead" in active_features:
        conditions["root_volume"] = {
            "required": True,
            "priority": "critical",
            "reason": "이마가 짧아 뿌리볼륨 없으면 하관이 부해 보임",
            "salon_instruction": "이마 바로 위 헤어라인쪽 뿌리볼륨펌 또는 매직기 뿌리볼륨 필수",
        }

    if "short_neck" in active_features:
        conditions["neck_clearance"] = {
            "required": True,
            "priority": "high",
            "reason": "목이 짧아 목선이 가려지면 답답해 보임",
            "salon_instruction": "목선이 가려지지 않도록 기장/컬 주의. 목 주변 컬 강한 디자인 피하기.",
        }

    if "square_jaw" in active_features:
        conditions["asymmetric_parting"] = {
            "required": False,
            "priority": "recommended",
            "reason": "턱 골격이 있어 대칭보다 비대칭이 턱 부각을 줄임",
            "salon_instruction": "5:5 정가르마보다 6:4 또는 7:3 비대칭 가르마 권장",
        }

    return conditions


# ============================================================
# 5. Main Entry Point
# ============================================================

def generate_mono_combos(
    complete_scores: list,
    global_conditions: dict,
    top_n: int = 3,
) -> list:
    """Male: TOP N 단일 complete cut. Female 의 front×back 조합 구조와 호환되도록
    back_id=None 으로 반환하여 downstream (_build_hair_recommendation) 이 동일하게 처리."""
    combos = []
    top = sorted(complete_scores, key=lambda x: x["score"], reverse=True)[:top_n]

    for rank, s in enumerate(top, start=1):
        # WHY
        why_parts = []
        for m in s.get("modifiers_applied", []):
            if m["mod"] > 0 and m["reason"]:
                why_parts.append(m["reason"])
        why_text = ". ".join(why_parts[:3]) + "." if why_parts else ""

        # Salon instruction
        salon_parts = []
        lc = s.get("length_constraint")
        if lc and lc.get("salon_note"):
            salon_parts.append(lc["salon_note"])
        for gc in global_conditions.values():
            if gc.get("required") and gc.get("salon_instruction"):
                salon_parts.append(gc["salon_instruction"])
        salon_text = ". ".join(salon_parts) + "." if salon_parts else ""

        # Trend tag — male styles not yet in HAIR_FRONT_TRENDS/HAIR_BACK_TRENDS.
        # 값 있으면 front/back 동일 id 로 조회 시도 (현재는 미수록 → None 예상).
        trend_tag = _get_trend_tag(s["style_id"], s["style_id"])

        combos.append({
            "front_id": s["style_id"],
            "front_name": s["name_kr"],
            "front_score": s["score"],
            "back_id": None,
            "back_name": None,
            "back_score": None,
            "cross_effect": 0,
            "cross_reasons": [],
            "combined_score": round(s["score"], 3),
            "why": why_text,
            "salon_instruction": salon_text,
            "trend": trend_tag,
            "rank": rank,
        })

    return combos


def build_hair_spec(face_features: dict, interview: dict,
                    gap: dict | None = None,
                    gender: str = "female") -> dict:
    """SIGAK 헤어 추천 스펙 생성 — 파이프라인 메인 함수.

    Args:
        face_features: CV 분석 결과 (face.py FaceFeatures dict)
        interview: 설문 응답 (neck_length, hair_volume, face_concerns 등)
        gap: 3축 갭 벡터 — v2에서 이미지 매칭에 활용
        gender: "female" / "male"

    Returns:
        report_formatter._build_hair_recommendation()이 소비하는 구조:
        {
            "cheat_sheet": str,
            "global_conditions": {...},
            "front_styles": [...],      # female: 8 scored / male: []
            "back_styles": [...],       # female: 13 scored / male: []
            "etc_styles": [...],        # female: 0~3 scored / male: []
            "complete_styles": [...],   # female: []       / male: 12 scored
            "top_combos": [...],        # 3 조합 (female: front×back / male: mono)
            "avoid": [...],
            "active_features": [...],
        }
    """
    # Step 1: 활성 feature 추출
    active_features = extract_active_features(face_features, interview)

    # Step 2: gender-filtered 전체 스타일 스코어링
    front_scores = []
    back_scores = []
    etc_scores = []
    complete_scores = []

    for style_id, style in HAIR_STYLES.items():
        # gender 필터 — 다른 성별 스타일은 skip (silent female default 차단)
        if style.get("gender", "female") != gender:
            continue
        if style.get("has_rating") is False:
            continue

        result = score_style(style_id, active_features, interview)
        if result is None:
            continue

        cat = style.get("category")
        if cat == "front":
            front_scores.append(result)
        elif cat == "back":
            back_scores.append(result)
        elif cat == "etc":
            etc_scores.append(result)
        elif cat == "complete":
            complete_scores.append(result)

    # Step 3: 정렬
    front_scores.sort(key=lambda x: x["score"], reverse=True)
    back_scores.sort(key=lambda x: x["score"], reverse=True)
    etc_scores.sort(key=lambda x: x["score"], reverse=True)
    complete_scores.sort(key=lambda x: x["score"], reverse=True)

    # Step 4: 글로벌 조건 (combo에서 salon 지시문 생성에 필요)
    global_conditions = compute_global_conditions(active_features, interview)

    # Step 5: TOP 조합 — gender 에 따라 분기
    if gender == "male":
        top_combos = generate_mono_combos(complete_scores, global_conditions, top_n=3)
    else:
        top_combos = generate_combos(front_scores, back_scores, global_conditions, top_n=3)

    # Step 6: AVOID (score < 0.35) — gender 에 따라 pool 분기
    avoid = []
    if gender == "male":
        avoid_pool = complete_scores
    else:
        avoid_pool = front_scores + back_scores + etc_scores
    for scored in avoid_pool:
        if scored["score"] < 0.35:
            primary_mod = max(
                scored["modifiers_applied"],
                key=lambda m: abs(m["mod"]),
                default={"feature": "unknown", "reason": ""},
            )
            avoid.append({
                "style_id": scored["style_id"],
                "name_kr": scored["name_kr"],
                "category": scored["category"],
                "score": scored["score"],
                "rating": scored["rating"],
                "primary_reason": primary_mod["reason"],
                "primary_feature": primary_mod["feature"],
            })

    # Step 7: 치트시트
    cheat_sheet = _generate_cheat_sheet(top_combos, global_conditions, avoid)

    return {
        "cheat_sheet": cheat_sheet,
        "global_conditions": global_conditions,
        "front_styles": front_scores,
        "back_styles": back_scores,
        "etc_styles": etc_scores,
        "complete_styles": complete_scores,
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
