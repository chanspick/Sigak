"""
EDA + Calibration Analysis for face_shape and skin_tone.

SCUT-FBP5500 AF (Asian Female) 2000-image calibration data 기반으로
현재 face.py 의 분류 임계값을 분석하고, 개선안을 제안한다.

Usage:
    python -m sigak.scripts.eda_face_calibration
"""

from __future__ import annotations

import json
import math
import textwrap
from pathlib import Path

# ──────────────────────────────────────────────
# 경로 설정
# ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_JSON = REPO_ROOT / "experiments" / "scut-fbp5500" / "calibration_af_insightface.json"
REPORT_OUTPUT = REPO_ROOT / "experiments" / "scut-fbp5500" / "eda_face_shape_report.md"

# ──────────────────────────────────────────────
# 얼굴형 시그니처 (Single Source of Truth)
# ──────────────────────────────────────────────
# key = 정규화 피처명, value = (target_normalized, weight)
#
# 정규화 기준:
#   ratio_norm:    높을수록 긴 얼굴
#   jaw_norm:      높을수록 넓은 턱 (둥근 턱)
#   cheek_norm:    높을수록 광대 돌출
#   forehead_norm: 높을수록 넓은 이마
#
# 설계 의도:
# - 가중 선형 유사도 기반 분류 (score = sum(w * (1-|diff|)) / sum(w))
# - oval 에 명시적 penalty 를 적용하여 "catch-all" 방지
# - oval 의 target 이 중앙값과 거의 일치하여 항상 높은 점수를 받는 문제를 해결
# - OVAL_PENALTY: oval 점수에 곱하는 감쇠 계수 (0.80 = 20% 감점)
#   이 값을 낮추면 oval 비율 감소, 높이면 증가
# - 목표: 각 유형 5-35%, 단일 유형 35% 이하
OVAL_PENALTY = 0.88

SIGNATURES = {
    "oval": {
        "ratio": (0.55, 1.5), "jaw": (0.45, 1.5),
        "cheek": (0.50, 1.5), "forehead": (0.50, 1.5),
    },
    "round": {
        "ratio": (0.15, 2.0), "jaw": (0.85, 2.5),
        "cheek": (0.40, 1.0), "forehead": (0.50, 0.5),
    },
    "oblong": {
        "ratio": (0.90, 2.5), "jaw": (0.50, 0.5),
        "cheek": (0.45, 0.5), "forehead": (0.50, 0.5),
    },
    "square": {
        "ratio": (0.30, 1.5), "jaw": (0.10, 2.5),
        "cheek": (0.35, 1.0), "forehead": (0.55, 1.0),
    },
    "heart": {
        "ratio": (0.50, 0.5), "jaw": (0.25, 2.0),
        "cheek": (0.55, 1.5), "forehead": (0.80, 2.5),
    },
    "inverted_triangle": {
        "ratio": (0.55, 0.5), "jaw": (0.15, 2.0),
        "cheek": (0.80, 2.5), "forehead": (0.60, 1.5),
    },
    "diamond": {
        "ratio": (0.60, 1.0), "jaw": (0.20, 1.5),
        "cheek": (0.85, 3.0), "forehead": (0.25, 2.5),
    },
}
ALL_SHAPES = list(SIGNATURES.keys())


def load_calibration() -> dict:
    """캘리브레이션 JSON을 읽어 반환한다."""
    with open(CALIBRATION_JSON, encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────

def _estimate_pct_below(stat: dict, threshold: float) -> float:
    """백분위 보간으로 threshold 이하 비율을 추정한다."""
    percentiles = [
        (0, stat["min"]), (5, stat["p5"]), (10, stat["p10"]),
        (25, stat["p25"]), (50, stat["p50"]), (75, stat["p75"]),
        (90, stat["p90"]), (95, stat["p95"]), (100, stat["max"]),
    ]
    if threshold <= stat["min"]:
        return 0.0
    if threshold >= stat["max"]:
        return 100.0
    for i in range(len(percentiles) - 1):
        p_lo, v_lo = percentiles[i]
        p_hi, v_hi = percentiles[i + 1]
        if v_lo <= threshold <= v_hi:
            if v_hi == v_lo:
                return (p_lo + p_hi) / 2
            frac = (threshold - v_lo) / (v_hi - v_lo)
            return p_lo + frac * (p_hi - p_lo)
    return 50.0


def _estimate_pct_above(stat: dict, threshold: float) -> float:
    """threshold 이상인 비율을 추정한다."""
    return 100.0 - _estimate_pct_below(stat, threshold)


def _normalize(value: float, vmin: float, vmax: float) -> float:
    """값을 [0, 1] 범위로 정규화한다."""
    if vmax == vmin:
        return 0.5
    return max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))


def _score_shape(ratio_n: float, jaw_n: float, cheek_n: float, forehead_n: float,
                 sigs: dict) -> dict:
    """
    각 얼굴형에 대한 가중 선형 유사도 점수를 계산한다.

    score = sum( weight * (1 - |norm - target|) ) / sum(weight)
    oval 유형에는 OVAL_PENALTY 를 곱하여 중앙값 편향을 보정한다.
    """
    scores = {}
    norms = {"ratio": ratio_n, "jaw": jaw_n, "cheek": cheek_n, "forehead": forehead_n}
    for shape, sig in sigs.items():
        weighted_sum = 0.0
        weight_total = 0.0
        for feat, (target, weight) in sig.items():
            similarity = 1.0 - abs(norms[feat] - target)
            weighted_sum += weight * similarity
            weight_total += weight
        score = weighted_sum / weight_total if weight_total > 0 else 0.0
        if shape == "oval":
            score *= OVAL_PENALTY
        scores[shape] = score
    return scores


# ──────────────────────────────────────────────
# 1. 현재 분류 임계값 분석
# ──────────────────────────────────────────────

def analyze_current_thresholds(cal: dict) -> str:
    """
    현재 face.py의 _classify_face_shape 임계값이 캘리브레이션 데이터와
    얼마나 맞지 않는지를 분석한다.
    """
    r = cal["face_length_ratio"]
    j = cal["jaw_angle"]
    c = cal["cheekbone_prominence"]
    f = cal["forehead_ratio"]

    lines = []
    lines.append("## 1. 현재 임계값 분석\n")
    lines.append("### 현재 `_classify_face_shape` 로직\n")
    lines.append("```python")
    lines.append("def _classify_face_shape(ratio, jaw_angle, cheekbone, forehead) -> str:")
    lines.append('    if ratio > 1.5 and jaw_angle < 125:     return "oblong"')
    lines.append('    elif ratio < 1.2 and jaw_angle > 140:   return "round"')
    lines.append('    elif ratio < 1.3 and jaw_angle < 120:   return "square"')
    lines.append('    elif cheekbone > 0.5 and forehead > 0.38: return "heart"')
    lines.append('    else:                                    return "oval"')
    lines.append("```\n")

    lines.append("### 캘리브레이션 데이터 요약\n")
    lines.append("| Metric | mean | std | min | p5 | p25 | p50 | p75 | p95 | max |")
    lines.append("|--------|------|-----|-----|-----|------|------|------|------|-----|")
    for key in ["face_length_ratio", "jaw_angle", "cheekbone_prominence", "forehead_ratio"]:
        d = cal[key]
        lines.append(
            f"| {key} | {d['mean']:.3f} | {d['std']:.3f} | {d['min']:.3f} "
            f"| {d['p5']:.3f} | {d['p25']:.3f} | {d['p50']:.3f} "
            f"| {d['p75']:.3f} | {d['p95']:.3f} | {d['max']:.3f} |"
        )
    lines.append("")

    lines.append("### 조건별 문제점\n")

    lines.append("**1) oblong (ratio > 1.5 AND jaw_angle < 125)**")
    lines.append(f"- face_length_ratio max = {r['max']:.3f}, p95 = {r['p95']:.3f}")
    lines.append(f"- ratio > 1.5 을 만족하는 얼굴이 데이터 범위 밖 (max {r['max']:.3f})")
    lines.append("- 결과: **0%** 의 얼굴이 oblong 으로 분류됨\n")

    lines.append("**2) round (ratio < 1.2 AND jaw_angle > 140)**")
    lines.append(f"- jaw_angle max = {j['max']:.1f}")
    lines.append(f"- jaw_angle > 140 을 만족하는 얼굴이 전혀 없음 (max {j['max']:.1f})")
    lines.append("- 결과: **0%** 의 얼굴이 round 로 분류됨\n")

    pct_ratio_lt_130 = _estimate_pct_below(r, 1.3)
    pct_jaw_lt_120 = _estimate_pct_below(j, 120.0)
    lines.append("**3) square (ratio < 1.3 AND jaw_angle < 120)**")
    lines.append(f"- ratio < 1.3: 약 {pct_ratio_lt_130:.0f}% (p90={r['p90']:.3f})")
    lines.append(f"- jaw_angle < 120: 약 {pct_jaw_lt_120:.0f}% (p90={j['p90']:.1f})")
    lines.append("- 두 조건의 교집합이 크므로, 대부분 heart/oval 전에 square로 잡힘\n")

    pct_cheek_gt_05 = _estimate_pct_above(c, 0.5)
    pct_fore_gt_038 = _estimate_pct_above(f, 0.38)
    lines.append("**4) heart (cheekbone > 0.5 AND forehead > 0.38)**")
    lines.append(f"- cheekbone > 0.5: 약 {pct_cheek_gt_05:.0f}% (p5={c['p5']:.3f})")
    lines.append(f"- forehead > 0.38: 약 {pct_fore_gt_038:.0f}% (p10={f['p10']:.3f})")
    lines.append("- 두 조건 모두 대다수가 만족 -> square에 안 잡힌 나머지가 대부분 heart\n")

    lines.append("**5) oval (else / catch-all)**")
    lines.append("- square와 heart가 대부분 흡수하므로, oval 비율이 매우 낮을 수 있음")
    lines.append("- 또는 square 조건이 너무 넓어서 oval이 거의 없음\n")

    lines.append("### 예상 분포 (현재 로직)\n")
    lines.append("| Type | 예상 비율 | 문제 |")
    lines.append("|------|----------|------|")
    lines.append("| oblong | ~0% | ratio > 1.5 조건 도달 불가 |")
    lines.append("| round | ~0% | jaw_angle > 140 조건 도달 불가 |")
    lines.append("| square | ~60-70% | ratio < 1.3 AND jaw_angle < 120 조건이 너무 관대 |")
    lines.append("| heart | ~25-35% | square 에 안 잡힌 나머지 대부분 |")
    lines.append("| oval | ~0-5% | catch-all 이지만 도달 어려움 |")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 2. 새 임계값 제안 (7가지 유형, 점수 기반)
# ──────────────────────────────────────────────

def propose_new_thresholds(cal: dict) -> str:
    """
    퍼센타일 기반의 multi-feature scoring 분류 방식을 제안한다.
    """
    r = cal["face_length_ratio"]
    j = cal["jaw_angle"]
    c = cal["cheekbone_prominence"]
    f = cal["forehead_ratio"]

    lines = []
    lines.append("## 2. 새로운 분류 시스템 제안\n")

    lines.append("### 설계 원칙\n")
    lines.append("1. **점수 기반 분류 + oval penalty**: 모든 유형에 가중 선형 유사도 계산 후, "
                 "oval 점수에만 penalty 계수를 곱하여 중앙값 편향 보정")
    lines.append("2. **퍼센타일 기반 정규화**: 원시 값 대신 0-1 정규화 점수를 사용하여 "
                 "각 피처의 스케일 차이를 제거")
    lines.append("3. **7가지 유형**: oval, round, heart, square, oblong, "
                 "inverted_triangle, diamond")
    lines.append("4. **목표 분포**: 각 유형 5-35%, 단일 유형 최대 35%")
    lines.append(f"5. **OVAL_PENALTY**: {OVAL_PENALTY} (낮출수록 oval 비율 감소)\n")

    lines.append("### 퍼센타일 기반 정규화 기준\n")
    lines.append("각 피처를 [0, 1] 범위로 정규화한다. 0 = 데이터 최소 방향, 1 = 최대 방향.\n")
    lines.append("```")
    for label, d in [("face_length_ratio", r), ("jaw_angle", j),
                     ("cheekbone_prominence", c), ("forehead_ratio", f)]:
        rng = d["max"] - d["min"]
        lines.append(f"{label}: min={d['min']:.3f}, max={d['max']:.3f}")
        lines.append(f"  -> norm = (value - {d['min']:.3f}) / ({d['max']:.3f} - {d['min']:.3f})")
        lines.append(f"  -> p25_norm = {(d['p25'] - d['min']) / rng:.3f}")
        lines.append(f"  -> p50_norm = {(d['p50'] - d['min']) / rng:.3f}")
        lines.append(f"  -> p75_norm = {(d['p75'] - d['min']) / rng:.3f}")
        lines.append("")
    lines.append("```\n")

    lines.append("### 얼굴형별 시그니처 정의\n")
    lines.append("각 얼굴형은 4개 피처에 대한 `(target, weight)` 쌍으로 정의된다.")
    lines.append("- `target`: 해당 유형에서 기대되는 정규화 값 (0-1)")
    lines.append("- `weight`: 해당 피처가 이 유형 판별에서 갖는 중요도")
    lines.append("- 점수 = sum( weight * (1 - |norm - target|) ) / sum(weight)\n")

    lines.append("| Type | ratio target | ratio w | jaw target | jaw w | cheek target | cheek w | forehead target | forehead w |")
    lines.append("|------|-------------|---------|------------|-------|--------------|---------|-----------------|------------|")

    for shape, sig in SIGNATURES.items():
        lines.append(
            f"| {shape} | {sig['ratio'][0]:.2f} | {sig['ratio'][1]:.1f} "
            f"| {sig['jaw'][0]:.2f} | {sig['jaw'][1]:.1f} "
            f"| {sig['cheek'][0]:.2f} | {sig['cheek'][1]:.1f} "
            f"| {sig['forehead'][0]:.2f} | {sig['forehead'][1]:.1f} |"
        )
    lines.append("")

    lines.append("### 시그니처 해석\n")
    lines.append(f"- **oval**: 중간값 유형 (penalty {OVAL_PENALTY} 적용으로 다른 유형과 공정 경쟁)")
    lines.append("- **round**: 짧은 얼굴(ratio low), 넓은 턱(jaw high) - 핵심 차별화 피처에 높은 weight(2.5)")
    lines.append("- **oblong**: 긴 얼굴(ratio high, weight 3.0) -> 가장 강한 차별화")
    lines.append("- **square**: 짧은 얼굴, 매우 각진 턱(jaw very low, weight 3.0)")
    lines.append("- **heart**: 좁은 턱 + 매우 넓은 이마(forehead 0.80, weight 2.5)")
    lines.append("- **inverted_triangle**: 좁은 턱 + 높은 광대(cheek 0.80, weight 2.5)")
    lines.append("- **diamond**: 매우 높은 광대(cheek 0.85, weight 3.0) + 좁은 이마(forehead 0.25, weight 2.5)")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 3. 시뮬레이션 (퍼센타일 격자점에서의 분류 결과)
# ──────────────────────────────────────────────

def simulate_distribution(cal: dict) -> str:
    """
    퍼센타일 격자점 조합에서 새 분류 알고리즘의 예상 분포를 시뮬레이션한다.
    """
    r = cal["face_length_ratio"]
    j = cal["jaw_angle"]
    c = cal["cheekbone_prominence"]
    f = cal["forehead_ratio"]

    r_vals = [r["p5"], r["p10"], r["p25"], r["p50"], r["p75"], r["p90"], r["p95"]]
    j_vals = [j["p5"], j["p10"], j["p25"], j["p50"], j["p75"], j["p90"], j["p95"]]
    c_vals = [c["p5"], c["p10"], c["p25"], c["p50"], c["p75"], c["p90"], c["p95"]]
    f_vals = [f["p5"], f["p10"], f["p25"], f["p50"], f["p75"], f["p90"], f["p95"]]

    # 각 격자점이 대표하는 구간 폭 (총합 100)
    weights = [7.5, 7.5, 17.5, 25.0, 17.5, 7.5, 7.5]

    counts = {s: 0.0 for s in ALL_SHAPES}
    total_weight = 0.0

    for ir, rv in enumerate(r_vals):
        for ij, jv in enumerate(j_vals):
            for ic, cv in enumerate(c_vals):
                for ifh, fv in enumerate(f_vals):
                    rn = _normalize(rv, r["min"], r["max"])
                    jn = _normalize(jv, j["min"], j["max"])
                    cn = _normalize(cv, c["min"], c["max"])
                    fn = _normalize(fv, f["min"], f["max"])

                    scores = _score_shape(rn, jn, cn, fn, SIGNATURES)
                    best = max(scores, key=scores.get)

                    w = weights[ir] * weights[ij] * weights[ic] * weights[ifh]
                    counts[best] += w
                    total_weight += w

    lines = []
    lines.append("## 3. 시뮬레이션 결과 (새 알고리즘)\n")
    lines.append("퍼센타일 격자점(7x7x7x7 = 2401개 조합, 가중치 적용) 기반 예상 분포:\n")
    lines.append("| Type | 예상 비율 | 상태 |")
    lines.append("|------|----------|------|")

    all_ok = True
    for shape in ALL_SHAPES:
        pct = counts[shape] / total_weight * 100
        if pct < 5:
            status = "LOW (< 5%)"
            all_ok = False
        elif pct > 35:
            status = "HIGH (> 35%)"
            all_ok = False
        else:
            status = "OK"
        lines.append(f"| {shape} | {pct:.1f}% | {status} |")

    if all_ok:
        lines.append("\n모든 유형이 목표 범위(5-35%) 내에 있습니다.")
    lines.append("")

    # 대표 프로파일
    lines.append("### 유형별 대표 프로파일\n")
    lines.append("각 유형에서 가장 높은 점수를 받는 퍼센타일 조합:\n")

    for shape in ALL_SHAPES:
        best_score = -1.0
        best_combo = (0, 0, 0, 0)
        for rv in r_vals:
            for jv in j_vals:
                for cv in c_vals:
                    for fv in f_vals:
                        rn = _normalize(rv, r["min"], r["max"])
                        jn = _normalize(jv, j["min"], j["max"])
                        cn = _normalize(cv, c["min"], c["max"])
                        fn = _normalize(fv, f["min"], f["max"])
                        scores = _score_shape(rn, jn, cn, fn, SIGNATURES)
                        if scores[shape] > best_score:
                            best_score = scores[shape]
                            best_combo = (rv, jv, cv, fv)

        lines.append(f"**{shape}** (score={best_score:.3f}):")
        lines.append(f"  ratio={best_combo[0]:.3f}, jaw={best_combo[1]:.1f}, "
                     f"cheek={best_combo[2]:.3f}, forehead={best_combo[3]:.3f}")

    lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# 4. 제안 코드 생성
# ──────────────────────────────────────────────

def _format_sig_for_code(sig: dict, key_map: dict) -> str:
    """시그니처를 Python 코드 문자열로 포맷한다."""
    parts = []
    for old_key, new_key in key_map.items():
        target, weight = sig[old_key]
        parts.append(f'"{new_key}": ({target}, {weight})')
    return "{" + ", ".join(parts) + "}"


def generate_proposed_code(cal: dict) -> str:
    """face.py 에 적용할 새 분류 함수 코드를 생성한다."""
    r = cal["face_length_ratio"]
    j = cal["jaw_angle"]
    c = cal["cheekbone_prominence"]
    f = cal["forehead_ratio"]

    # code 에서 사용하는 key 매핑: forehead -> fore
    key_map = {"ratio": "ratio", "jaw": "jaw", "cheek": "cheek", "forehead": "fore"}

    sig_lines = []
    for shape, sig in SIGNATURES.items():
        formatted = _format_sig_for_code(sig, key_map)
        padding = " " * (20 - len(shape))
        sig_lines.append(f'    "{shape}":{padding}{formatted},')
    sig_block = "\n".join(sig_lines)

    code = f'''\
## 4. 제안 코드: `_classify_face_shape` (v2)

다음 코드를 `face.py`의 `_classify_face_shape` 함수를 교체하는 데 사용한다.

```python
# ── 얼굴형 분류 (v2: SCUT-FBP5500 캘리브레이션 기반) ──

# 캘리브레이션 범위 (SCUT-FBP5500 AF, n=2000)
_FACE_CAL = {{
    "ratio": ({r["min"]:.3f}, {r["max"]:.3f}),   # face_length_ratio (min, max)
    "jaw":   ({j["min"]:.1f}, {j["max"]:.1f}),  # jaw_angle (min, max)
    "cheek": ({c["min"]:.3f}, {c["max"]:.3f}),   # cheekbone_prominence (min, max)
    "fore":  ({f["min"]:.3f}, {f["max"]:.3f}),    # forehead_ratio (min, max)
}}

# oval 의 target 이 데이터 중앙값과 거의 일치하여 항상 높은 점수를 받으므로,
# oval 점수에 penalty 를 곱하여 다른 유형과 공정하게 경쟁시킨다.
# 이 값을 낮추면 oval 비율 감소, 높이면 증가.
_OVAL_PENALTY = {OVAL_PENALTY}

# 얼굴형 시그니처: (target_normalized, weight)
# target: 0-1 정규화 공간에서 해당 유형의 이상적 위치
# weight: 이 피처가 해당 유형 판별에 미치는 중요도
_FACE_SHAPE_SIGNATURES = {{
{sig_block}
}}


def _normalize_feature(value: float, vmin: float, vmax: float) -> float:
    """피처 값을 [0, 1] 범위로 정규화한다."""
    if vmax == vmin:
        return 0.5
    return max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))


def _classify_face_shape(ratio: float, jaw_angle: float,
                         cheekbone: float, forehead: float) -> str:
    """
    얼굴형 분류 (v2: 점수 기반 + oval penalty).

    캘리브레이션 데이터로 정규화한 뒤, 7가지 유형별 시그니처와의
    가중 유사도를 계산하여 최고 점수 유형을 반환한다.
    oval 점수에는 _OVAL_PENALTY 를 곱하여 중앙값 편향을 보정한다.

    Returns:
        "oval" | "round" | "heart" | "square" | "oblong"
        | "inverted_triangle" | "diamond"
    """
    cal = _FACE_CAL
    norms = {{
        "ratio": _normalize_feature(ratio, *cal["ratio"]),
        "jaw":   _normalize_feature(jaw_angle, *cal["jaw"]),
        "cheek": _normalize_feature(cheekbone, *cal["cheek"]),
        "fore":  _normalize_feature(forehead, *cal["fore"]),
    }}

    best_shape = "oval"
    best_score = -1.0

    for shape, sig in _FACE_SHAPE_SIGNATURES.items():
        weighted_sum = 0.0
        weight_total = 0.0
        for feat, (target, weight) in sig.items():
            similarity = 1.0 - abs(norms[feat] - target)
            weighted_sum += weight * similarity
            weight_total += weight
        score = weighted_sum / weight_total if weight_total > 0 else 0.0
        if shape == "oval":
            score *= _OVAL_PENALTY
        if score > best_score:
            best_score = score
            best_shape = shape

    return best_shape
```

### 핵심 변경 사항

1. **if-elif 체인 제거** -> 점수 기반 분류
2. **매직 넘버 제거** -> `_FACE_CAL` 딕셔너리로 캘리브레이션 범위 관리
3. **5가지 -> 7가지 유형** 확장 (inverted_triangle, diamond 추가)
4. **시그니처 테이블**로 유형별 특성을 선언적으로 정의
5. **가중 유사도 + oval penalty**로 중앙값 편향 보정
6. **함수 시그니처 동일** -> 기존 호출 코드 변경 불필요
7. **OVAL_PENALTY 조정**으로 oval 비율을 쉽게 튜닝 가능
'''

    return code


# ──────────────────────────────────────────────
# 5. 피부톤 분석
# ──────────────────────────────────────────────

def analyze_skin_tone(cal: dict) -> str:
    """피부톤 분류 개선안을 제안한다."""
    sb = cal["skin_brightness"]

    lines = []
    lines.append("## 5. 피부톤 (skin_tone) 분석 및 개선안\n")

    lines.append("### 현재 로직\n")
    lines.append("```python")
    lines.append("warmth = (b_mean - 128) + (a_mean - 128) * 0.5")
    lines.append('if warmth > 8:      tone = "warm"')
    lines.append('elif warmth < -3:   tone = "cool"')
    lines.append('else:               tone = "neutral"')
    lines.append("```\n")

    lines.append("### 문제점\n")
    lines.append("1. **임계값 (8, -3) 의 근거 없음**: 아시안 피부에 대한 캘리브레이션 없이 설정됨")
    lines.append("2. **비대칭 범위**: warm 임계값(8)과 cool 임계값(-3)이 0을 중심으로 대칭이 아님")
    lines.append("3. **캘리브레이션 데이터에 warmth 없음**: "
                 f"`skin_brightness` 만 존재 (mean={sb['mean']:.3f}, std={sb['std']:.3f})")
    lines.append("4. **LAB 색공간 특성 미반영**: 아시안 피부톤의 a*, b* 분포 특성을 고려하지 않음\n")

    lines.append("### 아시안 피부톤의 LAB 색공간 특성 (문헌 기반)\n")
    lines.append("동아시아 여성 피부의 일반적인 LAB 값 범위 (조명 보정 후):\n")
    lines.append("| Parameter | 일반 범위 | 설명 |")
    lines.append("|-----------|----------|------|")
    lines.append("| L* | 55-75 | 밝기 (0=black, 100=white) |")
    lines.append("| a* | 5-15 | 적색-녹색 축 (양수=적색) |")
    lines.append("| b* | 15-30 | 황색-청색 축 (양수=황색) |")
    lines.append("")
    lines.append("OpenCV LAB 인코딩: L* -> [0, 255], a* -> a_mean (128=neutral), b* -> b_mean (128=neutral)")
    lines.append("따라서 아시안 피부의 전형적 OpenCV LAB 값:")
    lines.append("- a_mean: ~133-143 (약간 적색)")
    lines.append("- b_mean: ~143-158 (황색 편향)")
    lines.append("")
    lines.append("이 경우 warmth = (b_mean - 128) + (a_mean - 128) * 0.5:")
    lines.append("- 전형적 범위: (15~30) + (5~15) * 0.5 = 17.5 ~ 37.5")
    lines.append("- **대부분 warmth > 8 -> 거의 모든 얼굴이 'warm'으로 분류됨**\n")

    lines.append("### 개선안\n")
    lines.append("#### 방법 1: 상대적 warmth (아시안 피부톤 중심값 기준 편차) [권장]\n")
    lines.append("```python")
    lines.append("# 아시안 피부 기준 중앙값 (SCUT-FBP5500 기반 추정)")
    lines.append("# 추후 실제 a_mean, b_mean 캘리브레이션 데이터로 교체 필요")
    lines.append("_SKIN_WARMTH_CENTER = 22.0  # 전형적 아시안 피부의 warmth 중앙값 추정")
    lines.append("_SKIN_WARMTH_STD = 6.0      # warmth 표준편차 추정")
    lines.append("")
    lines.append("warmth_raw = (b_mean - 128) + (a_mean - 128) * 0.5")
    lines.append("warmth_z = (warmth_raw - _SKIN_WARMTH_CENTER) / _SKIN_WARMTH_STD")
    lines.append("")
    lines.append('if warmth_z > 0.5:        tone = "warm"')
    lines.append('elif warmth_z < -0.5:     tone = "cool"')
    lines.append('else:                     tone = "neutral"')
    lines.append("```\n")

    lines.append("#### 방법 2: 밝기 + warmth 결합 분류\n")
    lines.append("```python")
    lines.append(f"# skin_brightness 캘리브레이션: mean={sb['mean']:.3f}, std={sb['std']:.3f}")
    lines.append(f"# p25={sb['p25']:.3f}, p50={sb['p50']:.3f}, p75={sb['p75']:.3f}")
    lines.append("")
    lines.append("warmth_raw = (b_mean - 128) + (a_mean - 128) * 0.5")
    lines.append("")
    lines.append("# 밝기에 따라 warmth 기준값 보정")
    lines.append("# 어두운 피부 -> warmth 값이 낮아지는 경향 반영")
    lines.append(f"brightness_norm = (l_mean - {sb['min']:.3f}) / ({sb['max']:.3f} - {sb['min']:.3f})")
    lines.append("warmth_threshold_warm = 15 + brightness_norm * 10   # 밝을수록 높은 기준")
    lines.append("warmth_threshold_cool = 10 + brightness_norm * 8    # 밝을수록 높은 기준")
    lines.append("")
    lines.append("if warmth_raw > warmth_threshold_warm:   tone = 'warm'")
    lines.append("elif warmth_raw < warmth_threshold_cool: tone = 'cool'")
    lines.append("else:                                    tone = 'neutral'")
    lines.append("```\n")

    lines.append("### 권장 사항\n")
    lines.append("1. **즉시 적용 가능**: 방법 1 (상대적 warmth)")
    lines.append("   - `_SKIN_WARMTH_CENTER`와 `_SKIN_WARMTH_STD`는 추정값")
    lines.append("   - 추후 실제 a_mean, b_mean 캘리브레이션으로 정밀화 가능")
    lines.append("")
    lines.append("2. **캘리브레이션 보완 필요**: 향후 `calibrate_face_stats.py` 실행 시")
    lines.append("   `skin_warmth_score` (= warmth raw 값)의 통계도 캘리브레이션 JSON에 추가하면")
    lines.append("   정확한 CENTER/STD 를 사용할 수 있음")
    lines.append("")
    lines.append("3. **다인종 확장 시**: 인종별 CENTER/STD 테이블을 두고, "
                 "사용자 프로파일 또는 자동 감지로 선택")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 6. 리포트 생성
# ──────────────────────────────────────────────

def generate_report():
    """전체 EDA 리포트를 생성한다."""
    cal = load_calibration()

    sections = []
    sections.append("# EDA + Calibration Report: face_shape & skin_tone")
    sections.append("")
    sections.append("> 데이터 소스: SCUT-FBP5500 AF (Asian Female), n=2000")
    sections.append("> 캘리브레이션 파일: `experiments/scut-fbp5500/calibration_af_insightface.json`")
    sections.append("> 분석 대상: `sigak/pipeline/face.py`")
    sections.append("")

    sections.append(analyze_current_thresholds(cal))
    sections.append(propose_new_thresholds(cal))
    sections.append(simulate_distribution(cal))
    sections.append(generate_proposed_code(cal))
    sections.append(analyze_skin_tone(cal))

    sections.append("## 6. 다음 단계\n")
    sections.append("1. 이 리포트의 시그니처 가중치를 리뷰하고, 필요시 조정")
    sections.append("2. face.py 의 `_classify_face_shape` 함수를 제안 코드로 교체")
    sections.append("3. `_analyze_skin_tone_from_image`에 상대적 warmth 방식 적용")
    sections.append("4. `calibrate_face_stats.py` 에 `skin_warmth_score` 통계 추가")
    sections.append("5. 교체 후 기존 테스트 이미지로 분포 검증 실행")
    sections.append("")

    report = "\n".join(sections)
    REPORT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUTPUT.write_text(report, encoding="utf-8")
    print(f"Report written to: {REPORT_OUTPUT}")
    print(f"Report size: {len(report):,} characters")


if __name__ == "__main__":
    generate_report()
