"""
SIGAK Action Spec Layer

의사결정 우선순위:
1. 유저 목표 방향은 gap이 결정
2. 어느 부위를 우선할지는 type_delta + TYPE_MODIFIERS가 보정
3. 실행 강도는 TYPE_MODIFIERS.shading_intensity가 조정

함수 분리:
- build_action_spec() → 의미 레이어 (방향 + 부위 + 강도)
- build_overlay_plan() → 시각 레이어 (zone name + 색상 + 투명도)
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ─────────────────────────────────────────────
#  Data Structures
# ─────────────────────────────────────────────

@dataclass
class VisualPriority:
    zone: str
    importance: float
    reason: str
    axis: str
    delta_direction: str  # "increase" | "decrease"


@dataclass
class RecommendedAction:
    zone: str
    method: str
    goal: str
    priority: int  # 1, 2, 3, 4


@dataclass
class AvoidAction:
    zone: str
    method: str
    reason: str


@dataclass
class ActionSpec:
    matched_type_id: str
    matched_type_label: str
    primary_gap_axis: str
    visual_priorities: list[VisualPriority]       # 최대 3개
    recommended_actions: list[RecommendedAction]   # 2~4개 (최소 2개 보장)
    avoid_actions: list[AvoidAction]               # 최대 2개
    expected_effects: list[str]                    # 2~3문장
    report_mode: str                               # "makeup_female_v0"
    _debug_trace: dict = field(default_factory=dict, repr=False)


@dataclass
class OverlayZone:
    zone_name: str     # semantic name (landmark indices 없음)
    zone_type: str     # "shading" | "blush" | "highlight" | "tint"
    color_hex: str
    opacity: float


# ─────────────────────────────────────────────
#  축별 공통 Action 룰 테이블
# ─────────────────────────────────────────────

AXIS_ACTION_RULES: dict[str, dict[str, list[dict]]] = {
    "structure": {
        "increase": [
            {"zone": "jawline", "method": "contour_shading", "goal": "턱선 정리로 윤곽 선명화", "base_score": 0.9},
            {"zone": "temple", "method": "light_shading", "goal": "관자놀이 정리로 상안부 균형", "base_score": 0.7},
            {"zone": "nose_bridge", "method": "highlight", "goal": "코 중심축 강조", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "mid_cheek", "method": "soft_blush", "goal": "볼 중심 볼륨감으로 부드러운 인상", "base_score": 0.9},
            {"zone": "jawline", "method": "highlight", "goal": "턱선 경계 완화", "base_score": 0.7},
            {"zone": "forehead_center", "method": "highlight", "goal": "이마 중앙 볼륨으로 부드러움", "base_score": 0.6},
        ],
    },
    "impression": {
        "increase": [
            {"zone": "outer_eye", "method": "upward_line", "goal": "눈꼬리 방향 정리로 시원한 눈매", "base_score": 0.9},
            {"zone": "brow_tail", "method": "sharp_draw", "goal": "눈썹 끝 정리로 선명한 인상", "base_score": 0.75},
            {"zone": "lip_corner", "method": "slight_upturn", "goal": "입꼬리 각도 정리", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "under_eye", "method": "soft_highlight", "goal": "눈 아래 밝기로 부드러운 눈매", "base_score": 0.9},
            {"zone": "brow_arch", "method": "rounded_draw", "goal": "눈썹 곡선화로 부드러운 인상", "base_score": 0.75},
            {"zone": "lip_center", "method": "volume_highlight", "goal": "입술 중앙 볼륨감", "base_score": 0.6},
        ],
    },
    "maturity": {
        "increase": [
            {"zone": "cheekbone", "method": "contour_shading", "goal": "광대 음영으로 성숙한 윤곽", "base_score": 0.85},
            {"zone": "brow", "method": "straight_draw", "goal": "일자 눈썹으로 정돈된 인상", "base_score": 0.7},
            {"zone": "lip", "method": "defined_line", "goal": "립라인 정리로 단정한 느낌", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "cheek_apple", "method": "round_blush", "goal": "볼 사과존 블러셔로 어려 보이는 효과", "base_score": 0.85},
            {"zone": "under_eye", "method": "bright_concealer", "goal": "눈 밑 밝기로 동안 느낌", "base_score": 0.7},
            {"zone": "lip_center", "method": "gloss_highlight", "goal": "입술 중앙 광택으로 생기", "base_score": 0.6},
        ],
    },
    "intensity": {
        "increase": [
            {"zone": "eye_crease", "method": "shadow_depth", "goal": "눈두덩 음영으로 깊은 눈매", "base_score": 0.85},
            {"zone": "lip", "method": "full_color", "goal": "립 컬러 강조로 존재감", "base_score": 0.75},
            {"zone": "nose_tip", "method": "subtle_shadow", "goal": "코끝 음영으로 오목한 느낌", "base_score": 0.6},
        ],
        "decrease": [
            {"zone": "overall", "method": "matte_base", "goal": "전체 매트 베이스로 차분한 느낌", "base_score": 0.85},
            {"zone": "lip", "method": "nude_tone", "goal": "자연스러운 립 톤으로 부담감 완화", "base_score": 0.75},
            {"zone": "brow", "method": "feathered_draw", "goal": "자연스러운 눈썹결로 힘 빼기", "base_score": 0.6},
        ],
    },
}

MAX_TARGET_AXES = 3
MIN_RECOMMENDED_ACTIONS = 2
MAX_RECOMMENDED_ACTIONS = 4


# ─────────────────────────────────────────────
#  타입별 modifier (v0: 5개만)
# ─────────────────────────────────────────────

TYPE_MODIFIERS: dict[str, dict] = {
    "type_1": {
        "style_tone": "부드럽고 따뜻한",
        "shading_intensity": "light",
        "zone_boost": {"under_eye": 0.2, "cheek_apple": 0.15},
        "avoid_override": [
            {"zone": "jawline", "method": "hard_contour", "reason": "타입의 부드러운 인상과 충돌"}
        ],
    },
    "type_4": {
        "style_tone": "선명하고 시크한",
        "shading_intensity": "medium",
        "zone_boost": {"outer_eye": 0.2, "cheekbone": 0.15},
        "avoid_override": [],
    },
    "type_2": {
        "style_tone": "맑고 생기있는",
        "shading_intensity": "minimal",
        "zone_boost": {"cheek_apple": 0.2, "lip_center": 0.1},
        "avoid_override": [
            {"zone": "cheekbone", "method": "contour_shading", "reason": "동안 인상이 깎일 수 있음"}
        ],
    },
    "type_5": {
        "style_tone": "정돈되고 우아한",
        "shading_intensity": "medium",
        "zone_boost": {"brow": 0.15, "lip": 0.15},
        "avoid_override": [],
    },
    "type_6": {
        "style_tone": "강렬하고 존재감 있는",
        "shading_intensity": "strong",
        "zone_boost": {"eye_crease": 0.2, "lip": 0.15, "cheekbone": 0.1},
        "avoid_override": [],
    },
}
# 나머지 타입: 공통 룰만 적용, modifier 없음


# ─────────────────────────────────────────────
#  Overlay 시각 매핑
# ─────────────────────────────────────────────

ZONE_VISUAL: dict[str, tuple[str, str, float]] = {
    "jawline":         ("shading",   "#8B6914", 0.25),
    "temple":          ("shading",   "#8B6914", 0.20),
    "cheekbone":       ("shading",   "#8B6914", 0.22),
    "mid_cheek":       ("blush",     "#F4B8C1", 0.22),
    "outer_cheek":     ("blush",     "#F4B8C1", 0.22),
    "cheek_apple":     ("blush",     "#F4B8C1", 0.22),
    "outer_eye":       ("shading",   "#9B7653", 0.20),
    "under_eye":       ("highlight", "#F5E6D0", 0.25),
    "nose_bridge":     ("highlight", "#F5E6D0", 0.30),
    "forehead_center": ("highlight", "#F5E6D0", 0.25),
    "brow_tail":       ("shading",   "#7B6544", 0.18),
    "eye_crease":      ("shading",   "#8B7355", 0.22),
    "lip":             ("tint",      "#C4616C", 0.30),
    "lip_center":      ("highlight", "#F0D0C8", 0.25),
    "lip_corner":      ("shading",   "#A0705A", 0.15),
    "nose_tip":        ("shading",   "#9B8060", 0.18),
    "brow":            ("shading",   "#6B5A3A", 0.20),
    "brow_arch":       ("shading",   "#6B5A3A", 0.18),
    "overall":         ("shading",   "#C8B898", 0.10),
}


# ─────────────────────────────────────────────
#  Internal Helpers
# ─────────────────────────────────────────────

def _derive_zone_bonus(type_delta: dict[str, float]) -> dict[str, float]:
    """
    타입 대비 delta가 큰 축 → 관련 zone에 bonus.
    magnitude 기반 (v0). 방향 필터링은 다음 스프린트에서 정교화.
    """
    AXIS_ZONE_MAP = {
        "structure": ["jawline", "temple", "cheekbone", "nose_bridge"],
        "impression": ["outer_eye", "brow_tail", "under_eye", "brow_arch"],
        "maturity": ["cheekbone", "brow", "cheek_apple"],
        "intensity": ["eye_crease", "lip", "nose_tip"],
    }
    zone_bonus: dict[str, float] = {}
    for axis, delta in type_delta.items():
        if abs(delta) < 0.1:
            continue
        bonus = abs(delta) * 0.3
        for zone in AXIS_ZONE_MAP.get(axis, []):
            zone_bonus[zone] = zone_bonus.get(zone, 0) + bonus
    return zone_bonus


def _generate_expected_effects(
    primary_axis: str, type_label: str, style_tone: str
) -> list[str]:
    """deterministic 기대 효과 문장 생성"""
    axis_effect = {
        "structure": "얼굴 윤곽이 더 정돈돼 보입니다",
        "impression": "눈매와 인상이 더 선명해집니다",
        "maturity": "전체적인 분위기가 달라져 보입니다",
        "intensity": "이목구비의 존재감이 조정됩니다",
    }
    effects = [axis_effect.get(primary_axis, "전체 인상이 개선됩니다")]
    if type_label and style_tone:
        effects.append(f"{type_label} 타입의 {style_tone} 매력이 더 살아납니다")
    effects.append("적용 순서대로 하나씩 시도해보세요")
    return effects


# ─────────────────────────────────────────────
#  build_action_spec()
# ─────────────────────────────────────────────

def build_action_spec(
    face_features,
    current_coords: dict[str, float],
    matched_type: dict,
    type_delta: dict[str, float],
    gap: dict,
    interview_intent: dict[str, str] | None = None,
) -> ActionSpec:
    """
    Layer 1: gap → 목표 방향 결정
    Layer 2: type_delta + modifier → 부위 우선순위 보정
    """
    debug_trace: dict = {}

    # ── Layer 1: gap에서 target axes 추출 ──
    gap_vector = gap.get("vector", {})
    sorted_axes = sorted(gap_vector.items(), key=lambda x: abs(x[1]), reverse=True)
    target_axes: list[tuple[str, str, float]] = []
    for axis, delta_val in sorted_axes:
        if abs(delta_val) < 0.1:
            continue
        direction = "increase" if delta_val > 0 else "decrease"
        target_axes.append((axis, direction, abs(delta_val)))
    target_axes = target_axes[:MAX_TARGET_AXES]

    primary_axis = target_axes[0][0] if target_axes else "structure"
    debug_trace["target_axes"] = [(a, d, round(m, 3)) for a, d, m in target_axes]

    # ── Layer 1.5: 공통 룰에서 action 후보 + base_score 수집 ──
    candidates: list[dict] = []
    for axis, direction, magnitude in target_axes:
        rules = AXIS_ACTION_RULES.get(axis, {}).get(direction, [])
        for rule in rules:
            score = rule["base_score"] * magnitude
            candidates.append({
                **rule, "axis": axis, "direction": direction, "score": score,
            })

    # ── Layer 2: type_delta로 zone importance 보정 ──
    type_zone_bonus = _derive_zone_bonus(type_delta)
    for c in candidates:
        c["score"] += type_zone_bonus.get(c["zone"], 0.0)
    debug_trace["type_zone_bonus"] = type_zone_bonus

    # ── Layer 2.5: 타입 modifier 적용 ──
    type_id = matched_type.get("key", "")
    modifier = TYPE_MODIFIERS.get(type_id, {})

    for c in candidates:
        c["score"] += modifier.get("zone_boost", {}).get(c["zone"], 0.0)

    avoid_actions: list[AvoidAction] = []
    for override in modifier.get("avoid_override", []):
        avoid_actions.append(AvoidAction(**override))
        candidates = [
            c for c in candidates
            if not (c["zone"] == override["zone"] and c["method"] == override["method"])
        ]
    debug_trace["modifier_applied"] = type_id or "none"

    # ── 최종 선택: score 기반 정렬 + zone 중복 제거 ──
    candidates.sort(key=lambda x: x["score"], reverse=True)

    visual_priorities: list[VisualPriority] = []
    recommended: list[RecommendedAction] = []
    seen_zones: set[str] = set()

    for c in candidates:
        if c["zone"] in seen_zones:
            continue
        seen_zones.add(c["zone"])

        if len(visual_priorities) < 3:
            visual_priorities.append(VisualPriority(
                zone=c["zone"], importance=round(c["score"], 2),
                reason=c["goal"], axis=c["axis"], delta_direction=c["direction"],
            ))
        if len(recommended) < MAX_RECOMMENDED_ACTIONS:
            recommended.append(RecommendedAction(
                zone=c["zone"], method=c["method"],
                goal=c["goal"], priority=len(recommended) + 1,
            ))

    # ── 최소 action 보장 (gap이 작거나 후보 부족 시) ──
    if len(recommended) < MIN_RECOMMENDED_ACTIONS:
        fallback_rules = AXIS_ACTION_RULES.get(primary_axis, {}).get("increase", [])
        for rule in fallback_rules:
            if rule["zone"] not in seen_zones and len(recommended) < MIN_RECOMMENDED_ACTIONS:
                recommended.append(RecommendedAction(
                    zone=rule["zone"], method=rule["method"],
                    goal=rule["goal"], priority=len(recommended) + 1,
                ))
                seen_zones.add(rule["zone"])

    debug_trace["final_actions"] = [r.zone for r in recommended]

    # ── 기대 효과 ──
    type_label = matched_type.get("name_kr", "")
    style_tone = modifier.get("style_tone", "")
    expected_effects = _generate_expected_effects(primary_axis, type_label, style_tone)

    return ActionSpec(
        matched_type_id=type_id,
        matched_type_label=type_label,
        primary_gap_axis=primary_axis,
        visual_priorities=visual_priorities,
        recommended_actions=recommended,
        avoid_actions=avoid_actions,
        expected_effects=expected_effects,
        report_mode="makeup_female_v0",
        _debug_trace=debug_trace,
    )


# ─────────────────────────────────────────────
#  build_overlay_plan()
# ─────────────────────────────────────────────

def build_overlay_plan(
    action_spec: ActionSpec,
    face_features,
) -> list[OverlayZone]:
    """
    recommended_actions → 시각적 오버레이 계획.
    zone name(semantic)까지만 확정. landmark 변환은 렌더러에서 source_model 확인 후 수행.
    """
    modifier = TYPE_MODIFIERS.get(action_spec.matched_type_id, {})
    intensity = modifier.get("shading_intensity", "medium")
    mult = {"minimal": 0.6, "light": 0.8, "medium": 1.0, "strong": 1.2}.get(intensity, 1.0)

    zones: list[OverlayZone] = []
    for action in action_spec.recommended_actions:
        visual = ZONE_VISUAL.get(action.zone)
        if not visual:
            continue
        ztype, color, opacity = visual
        zones.append(OverlayZone(
            zone_name=action.zone, zone_type=ztype,
            color_hex=color, opacity=min(opacity * mult, 0.5),
        ))
    return zones
