# SIGAK v3 — Claude Code 실행 지시서

> 이 문서를 Phase 단위로 순서대로 실행하세요.
> 각 Phase 완료 후 반드시 해당 Phase의 검증을 통과한 뒤 다음으로 넘어가세요.
> 전체 컨텍스트는 `SIGAK_ACTION_PLAN_V3.md`를 참조하세요.

---

# Phase 0: 사전 확인

## 지시

아래 파일 위치와 구조를 확인하고 보고하세요.

1. `report_formatter.py` 위치 확인 — 아래 항목 찾기:
    - `FACE_STATS` 딕셔너리 (mean/std 하드코딩)
    - `METRIC_RANGES` 딕셔너리
    - `scipy.stats.norm.cdf` 호출부 (percentile 계산)
    - `gap_analysis` 섹션 포맷팅 함수 (direction_items 생성부)
    - `face_interpretation` 섹션 포맷팅 함수
    - `action_plan` 섹션 포맷팅 함수 (delta_contribution 계산부)
    - `type_reference` 섹션 포맷팅 함수
    - `trend_context` 섹션 포맷팅 함수

2. `llm.py` 위치 확인 — 아래 항목 찾기:
    - `generate_report()` 함수의 system prompt
    - `generate_report()` 함수의 user message payload 구성부
    - face_interpretation 생성 관련 프롬프트

3. `coordinate.py` 위치 확인:
    - `OBSERVED_RANGES` 딕셔너리

4. `action_spec.py` 위치 확인:
    - `recommended_actions`의 score/priority 필드명

## 보고 형식

```
report_formatter.py: [경로]
  FACE_STATS: L{시작줄}~L{끝줄}
  percentile 계산: L{줄번호} (함수명)
  gap direction_items 생성: L{줄번호} (함수명)
  face_interpretation 포맷: L{줄번호} (함수명)
  action_plan delta_contribution: L{줄번호}
  type_reference 포맷: L{줄번호} (함수명)
  trend_context 포맷: L{줄번호} (함수명)

llm.py: [경로]
  generate_report system prompt: L{줄번호}
  generate_report user payload: L{줄번호}

coordinate.py: [경로]
  OBSERVED_RANGES: L{시작줄}~L{끝줄}

action_spec.py: [경로]
  score/priority 필드: [필드명]
```

## 완료 조건
- 위 항목 모두 위치 파악 완료
- 못 찾는 항목 있으면 가장 가까운 코드 위치와 이유 보고

---

# Phase 1: percentile 즉시 안정화

> 가장 적은 코드 변경으로 극단 p값 문제를 완화합니다.

## 수정 1-1: percentile clamp 적용

**파일:** `report_formatter.py` — percentile 계산 함수

**변경:** `norm.cdf()` 결과에 clamp 적용

```python
# 기존 코드 패턴 (찾아서 수정):
# percentile = int(round(norm.cdf(value, mean, std) * 100))

# 다음으로 교체:
raw_p = norm.cdf(value, mean, std) * 100
percentile = max(5, min(95, int(round(raw_p))))
```

## 수정 1-2: percentile 기반 서술 어휘 테이블 추가

**파일:** `report_formatter.py` — 상단 상수 영역

**추가:**

```python
def percentile_to_tone_kr(p: int) -> str:
    """percentile → 서술 어휘. interpretation 생성 시 입력으로 사용."""
    if p <= 10:  return "매우 낮은 편"
    if p <= 25:  return "낮은 편"
    if p <= 40:  return "다소 낮은 편"
    if p <= 60:  return "보통 수준"
    if p <= 75:  return "다소 높은 편"
    if p <= 90:  return "높은 편"
    return "매우 높은 편"
```

이 함수는 Phase 3에서 interpretation 생성 시 사용됩니다. 지금은 추가만 하세요.

## 검증 1

```python
# 테스트: 홍길순/조찬형 사진으로 리포트 재생성 후
report = generate_full_report(...)  # 기존 테스트 방식
sections = {s["id"]: s for s in report["formatted"]["sections"]}
fs = sections["face_structure"]["content"]

for m in fs["metrics"]:
    p = m["percentile"]
    assert 5 <= p <= 95, f"FAIL: {m['key']} percentile={p}"
    print(f"  ✅ {m['key']}: percentile={p}")

print("Phase 1 통과")
```

---

# Phase 2: gap_analysis 비문 수정

> direction_items의 recommendation 문장을 deterministic 템플릿으로 교체합니다.

## 수정 2-1: 축별 recommendation 템플릿 테이블 추가

**파일:** `report_formatter.py` — 상단 상수 영역

```python
GAP_RECOMMENDATION_TEMPLATES = {
    "structure": {
        "increase": "구조 축에서는 좀 더 선명하고 또렷한 윤곽을 만드는 방향이 핵심이에요.",
        "decrease": "구조 축에서는 라인을 부드럽게 풀어주는 방향이 핵심이에요.",
    },
    "impression": {
        "increase": "인상 축에서는 눈매와 이목구비를 또렷하게 살리는 방향이 중요해요.",
        "decrease": "인상 축에서는 눈매와 라인을 부드럽게 풀어주는 방향이 중요해요.",
    },
    "maturity": {
        "increase": "성숙도 축에서는 세련되고 성숙한 분위기를 더하는 방향이에요.",
        "decrease": "성숙도 축에서는 어려 보이고 생기 있는 느낌을 더하는 방향이 잘 맞아요.",
    },
    "intensity": {
        "increase": "강도 축에서는 존재감 있고 임팩트 있는 표현이 포인트예요.",
        "decrease": "강도 축에서는 자연스럽고 힘을 뺀 표현이 포인트예요.",
    },
}
```

## 수정 2-2: recommendation 생성 로직 교체

**파일:** `report_formatter.py` — direction_items 생성부

기존 f-string 조합 코드를 찾아서 아래로 교체:

```python
def build_gap_recommendation(axis: str, delta: float) -> str:
    direction = "decrease" if delta < 0 else "increase"
    return GAP_RECOMMENDATION_TEMPLATES.get(axis, {}).get(
        direction, 
        f"이 방향으로 스타일링을 조정하면 원하는 이미지에 가까워질 수 있어요."
    )
```

direction_items 루프 안에서:
```python
# 기존: recommendation = f"..." (문제의 f-string)
# 교체:
recommendation = build_gap_recommendation(axis, delta)
```

## 수정 2-3: gap_summary 한국어 조사 처리

**파일:** `report_formatter.py` — gap_summary 생성부

```python
def _postposition(word: str, with_batchim: str, without_batchim: str) -> str:
    """한국어 조사 자동 선택 (받침 유무 기반)"""
    if not word:
        return with_batchim
    last_char = ord(word[-1])
    if 0xAC00 <= last_char <= 0xD7A3:
        has_batchim = (last_char - 0xAC00) % 28 != 0
        return with_batchim if has_batchim else without_batchim
    return with_batchim

# 축 이름 한글 매핑
AXIS_LABEL_KR = {
    "structure": "구조",
    "impression": "인상",
    "maturity": "성숙도",
    "intensity": "강도",
}
```

gap_summary 생성 시:
```python
primary_kr = AXIS_LABEL_KR.get(primary_axis, primary_axis)
secondary_kr = AXIS_LABEL_KR.get(secondary_axis, secondary_axis)

pp1 = _postposition(primary_kr, "이", "가")
pp2 = _postposition(secondary_kr, "이", "가")

gap_summary = f"주요 변화 방향은 {primary_kr}{pp1}고, {secondary_kr}{pp2} 보조 방향이에요."
```

## 검증 2

```python
import re

report = generate_full_report(...)
sections = {s["id"]: s for s in report["formatted"]["sections"]}
gap = sections["gap_analysis"]["content"]

# 비문 패턴 검사
BANNED = [
    r"더\s+\S+\s+필요한",
    r"방향에서 더 \S+ 필요",
]

for item in gap["direction_items"]:
    for pattern in BANNED:
        assert not re.search(pattern, item["recommendation"]), \
            f"FAIL 비문: {item['recommendation']}"
    print(f"  ✅ {item['axis']}: {item['recommendation'][:40]}...")

# 조사 검사
assert "도이 " not in gap["gap_summary"], f"FAIL 조사: {gap['gap_summary']}"
assert "도이보" not in gap["gap_summary"]
print(f"  ✅ gap_summary: {gap['gap_summary']}")

print("Phase 2 통과")
```

---

# Phase 3: face_interpretation raw 수치 제거

> 해석문에서 숫자를 제거합니다. 프롬프트 + 후처리 이중 방어.

## 수정 3-1: 후처리 필터 함수 추가

**파일:** `report_formatter.py` — 상단 유틸 영역

```python
import re

RAW_NUMBER_PATTERNS = [
    r"\d+(\.\d+)?°",       # 93.7°
    r"\d+(\.\d+)?%",       # 87%
    r"\b0\.\d{2,}\b",      # 0.644, 0.872
    r"\b1\.\d{2,}\b",      # 1.366
    r"\d{2,}\.\d+의\s",    # "93.7의 " — 숫자+의 패턴
]

def contains_raw_metric(text: str) -> bool:
    """해석문에 raw 수치가 포함되어 있는지 검사"""
    return any(re.search(p, text) for p in RAW_NUMBER_PATTERNS)

def sanitize_interpretation(text: str) -> str:
    """해석문에서 raw 수치 패턴을 제거하고 문장을 정리"""
    if not contains_raw_metric(text):
        return text

    # 패턴별 제거
    # "93.7°의 턱선 각도는" → "턱선 각도는" / "턱선은"
    text = re.sub(r"\d+(\.\d+)?°의\s*", "", text)
    # "0.719의 광대 돌출도는" → "광대 돌출도는"
    text = re.sub(r"\b[01]\.\d+의\s*", "", text)
    # "11.01°의 " → ""
    text = re.sub(r"\d+(\.\d+)?°의?\s*", "", text)
    # 남은 소수점 숫자
    text = re.sub(r"\b0\.\d{2,}\b", "", text)
    text = re.sub(r"\b1\.\d{2,}\b", "", text)
    # 정리
    text = re.sub(r"\s{2,}", " ", text).strip()
    # 문장 시작이 조사로 시작하면 제거
    text = re.sub(r"^의\s+", "", text)
    text = re.sub(r"^는\s+", "", text)
    return text
```

## 수정 3-2: face_interpretation 포맷팅에 sanitize 적용

**파일:** `report_formatter.py` — face_interpretation 섹션 포맷팅 함수

해당 함수에서 아래 필드들에 `sanitize_interpretation()` 적용:

```python
# overall_impression
content["overall_impression"] = sanitize_interpretation(content["overall_impression"])

# 각 feature_interpretation
for feat in content["feature_interpretations"]:
    feat["interpretation"] = sanitize_interpretation(feat["interpretation"])

# harmony_note
if "harmony_note" in content:
    content["harmony_note"] = sanitize_interpretation(content["harmony_note"])

# distinctive_points
if "distinctive_points" in content:
    content["distinctive_points"] = [
        sanitize_interpretation(p) for p in content["distinctive_points"]
    ]
```

## 수정 3-3: LLM 프롬프트에 수치 금지 규칙 추가

**파일:** `llm.py` — generate_report()의 system prompt

기존 system prompt에 아래 규칙 블록을 추가하세요:

```
## 해석문 작성 규칙 (필수)
- 해석 문장에 숫자, 소수점, 도(°), 퍼센트(%)를 절대 포함하지 마세요.
- 숫자는 구조화 JSON 필드(value, percentile)에만 남기세요.
- 서술문은 의미와 인상만 설명하세요.
- 금지 예: "93.7°의 턱선 각도는 날카로운 편으로"
- 허용 예: "턱선이 날카로운 편이라 또렷하고 의지적인 인상을 만들어요"
- 금지 예: "0.719의 광대 돌출도는 상당히 뚜렷한 편으로"  
- 허용 예: "광대가 뚜렷한 편이라 입체적이고 개성 있는 인상을 줘요"
```

## 검증 3

```python
import re

report = generate_full_report(...)
sections = {s["id"]: s for s in report["formatted"]["sections"]}
fi = sections["face_interpretation"]["content"]

# overall_impression 숫자 검사
assert not contains_raw_metric(fi["overall_impression"]), \
    f"FAIL: overall_impression에 수치: {fi['overall_impression']}"
print(f"  ✅ overall_impression: {fi['overall_impression'][:50]}...")

# 각 feature interpretation 숫자 검사
for feat in fi["feature_interpretations"]:
    assert not contains_raw_metric(feat["interpretation"]), \
        f"FAIL: {feat['feature']} interpretation에 수치: {feat['interpretation']}"
    print(f"  ✅ {feat['feature']}: {feat['interpretation'][:40]}...")

# harmony_note
if fi.get("harmony_note"):
    assert not contains_raw_metric(fi["harmony_note"]), \
        f"FAIL: harmony_note에 수치: {fi['harmony_note']}"

# distinctive_points
for dp in fi.get("distinctive_points", []):
    assert not contains_raw_metric(dp), f"FAIL: distinctive_point에 수치: {dp}"

print("Phase 3 통과")
```

---

# Phase 4: SCUT-FBP5500 캘리브레이션

> FACE_STATS를 실측 기반으로 교체합니다.

## 수정 4-1: 캘리브레이션 스크립트 생성

**파일:** `scripts/calibrate_face_stats.py` (신규 생성)

```python
"""
SCUT-FBP5500 AF subset → SIGAK Step 1 배치 실행 → FACE_STATS 실측값 산출

사용법:
    python scripts/calibrate_face_stats.py \
        --image-dir ./data/scut-fbp5500/Images/ \
        --subset AF \
        --output ./data/calibration_result.json

출력: metric별 mean, std, p5, p25, p50, p75, p95, min, max, n
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

# 프로젝트 root를 path에 추가 (경로는 실제 구조에 맞게 조정)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sigak.face import analyze_face  # Step 1 함수 — 실제 import 경로 확인 필요

METRICS_TO_CALIBRATE = [
    "jaw_angle",
    "face_length_ratio",
    "symmetry_score",
    "golden_ratio_score",
    "cheekbone_prominence",
    "eye_tilt",
    "eye_width_ratio",
    "nose_bridge_height",
    "lip_fullness",
    "brow_arch",
    "eye_ratio",
    "forehead_ratio",
    "philtrum_ratio",
    "nose_bridge_height",
    "skin_brightness",
]

def run_calibration(image_dir: Path, subset: str, output_path: Path):
    results = {m: [] for m in METRICS_TO_CALIBRATE}
    total = 0
    failed = 0

    pattern = f"{subset}*.jpg"
    image_files = sorted(image_dir.glob(pattern))
    if not image_files:
        # SCUT 파일명이 다를 수 있음 — 패턴 조정
        image_files = sorted(image_dir.glob("*.jpg"))
        image_files = [f for f in image_files if f.stem.startswith(subset)]

    print(f"Found {len(image_files)} images matching '{pattern}'")

    for i, img_path in enumerate(image_files):
        total += 1
        try:
            features = analyze_face(img_path.read_bytes())
            feat_dict = features.to_dict()
            for m in METRICS_TO_CALIBRATE:
                val = feat_dict.get(m)
                if val is not None and isinstance(val, (int, float)):
                    results[m].append(float(val))
        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  SKIP {img_path.name}: {e}")
            continue

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(image_files)} (failed: {failed})")

    # 통계 산출
    stats = {}
    for m, values in results.items():
        if len(values) < 10:
            print(f"  WARNING: {m} has only {len(values)} samples, skipping")
            continue
        arr = np.array(values)
        stats[m] = {
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr)), 4),
            "p5": round(float(np.percentile(arr, 5)), 4),
            "p10": round(float(np.percentile(arr, 10)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p50": round(float(np.percentile(arr, 50)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
            "p90": round(float(np.percentile(arr, 90)), 4),
            "p95": round(float(np.percentile(arr, 95)), 4),
            "min": round(float(np.min(arr)), 4),
            "max": round(float(np.max(arr)), 4),
            "n": len(values),
        }

    stats["_meta"] = {
        "source": f"SCUT-FBP5500 {subset} subset",
        "total_attempted": total,
        "successful": total - failed,
        "failed": failed,
        "note": "연구 캘리브레이션용. 유저 데이터 확보 시 교체 예정.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\nCalibration complete → {output_path}")

    # FACE_STATS 교체용 코드 스니펫 출력
    print("\n# --- FACE_STATS 교체용 (report_formatter.py에 복사) ---")
    print("FACE_STATS = {")
    for m in METRICS_TO_CALIBRATE:
        if m in stats:
            s = stats[m]
            print(f'    "{m}": {{"mean": {s["mean"]}, "std": {s["std"]}}},')
    print("}")

    # OBSERVED_RANGES 비교용 출력
    print("\n# --- OBSERVED_RANGES 비교용 (p10~p90) ---")
    for m in METRICS_TO_CALIBRATE:
        if m in stats:
            s = stats[m]
            print(f'#   "{m}": ({s["p10"]}, {s["p90"]}),  # measured')

    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--subset", default="AF", help="AF, AM, CF, CM")
    parser.add_argument("--output", type=Path, default=Path("data/calibration_result.json"))
    args = parser.parse_args()
    run_calibration(args.image_dir, args.subset, args.output)
```

## 수정 4-2: 캘리브레이션 실행

```bash
# 1. SCUT-FBP5500 다운로드 (수동 — 학술 신청 필요)
# 또는 Kaggle/HuggingFace에서 접근 가능한 버전 사용

# 2. 실행
python scripts/calibrate_face_stats.py \
    --image-dir ./data/scut-fbp5500/Images/ \
    --subset AF \
    --output ./data/calibration_af.json

# 3. 출력된 FACE_STATS 스니펫을 report_formatter.py에 복사
```

## 수정 4-3: FACE_STATS 교체

**파일:** `report_formatter.py` — `FACE_STATS` 딕셔너리

캘리브레이션 출력 결과로 교체합니다.
**주의:** 기존 FACE_STATS는 주석으로 보존하세요.

```python
# AS-IS (교과서 추정값 — 보존용 주석)
# FACE_STATS_LEGACY = {
#     "jaw_angle": {"mean": 124.0, "std": 8.0},
#     ...
# }

# TO-BE (SCUT-FBP5500 AF 실측값)
FACE_STATS = {
    # calibrate_face_stats.py 출력 결과를 여기에 붙여넣기
}
```

## 검증 4

```bash
# 캘리브레이션 결과 확인
python -c "
import json
stats = json.load(open('data/calibration_af.json'))
meta = stats.pop('_meta')
print(f'Source: {meta[\"source\"]}')
print(f'Success: {meta[\"successful\"]}/{meta[\"total_attempted\"]}')
print()
for k, v in stats.items():
    print(f'{k:25s}  mean={v[\"mean\"]:8.4f}  std={v[\"std\"]:8.4f}  range=[{v[\"p5\"]:.4f}, {v[\"p95\"]:.4f}]  n={v[\"n\"]}')
"
```

FACE_STATS 교체 후 리포트 재생성:
```python
report = generate_full_report(...)
sections = {s["id"]: s for s in report["formatted"]["sections"]}
fs = sections["face_structure"]["content"]

for m in fs["metrics"]:
    p = m["percentile"]
    assert 5 <= p <= 95, f"FAIL: {m['key']} percentile={p}"
    # 극단 집중 해소 확인
    print(f"  {m['key']:25s}  value={m['value']:.3f}  percentile={p}")

# jaw_angle이 더 이상 1이 아닌지 확인
jaw = next(m for m in fs["metrics"] if m["key"] == "jaw_angle")
assert jaw["percentile"] > 5, f"jaw_angle still extreme: {jaw['percentile']}"
print("Phase 4 통과")
```

---

# Phase 5: executive_summary 구체성 복구

> summary에 추구미 방향 연결을 복구합니다.

## 수정 5-1: generate_report 입력 payload 확장

**파일:** `llm.py` — `generate_report()` user message 구성부

기존 payload에 아래 필드 추가:

```python
# generate_report()에 넘기는 payload 구성 시 추가
summary_context = {
    "current_type_label": matched_type["name_kr"],
    "aspiration_summary": aspiration.get("interpretation", ""),
    "primary_gap_axis": gap["primary_direction"],
    "primary_gap_direction_kr": gap["primary_shift_kr"],
    "top_action_goals": [
        a.goal for a in action_spec.recommended_actions[:2]
    ],
}
# 이 summary_context를 user message payload에 포함
```

실제 변수명은 코드 확인 후 맞추세요. 핵심은 `generate_report()`가 받는 정보에 **추구미 해석 + primary gap 방향 + top action 목표**가 포함되는 것.

## 수정 5-2: system prompt에 summary 규칙 추가

**파일:** `llm.py` — `generate_report()` system prompt

```
## executive_summary 규칙 (필수)
- 반드시 현재 인상과 추구 방향의 차이를 1문장 이상 포함하세요
- 핵심 action 방향을 1문장 이상 포함하세요
- 최소 2문장, 최대 4문장
- 금지: "스타일링을 추천해요" 수준의 일반론만으로 끝내기
- 필수 포함: current_type_label, aspiration 방향, 구체적 포인트 1개 이상
```

## 검증 5

```python
report = generate_full_report(...)
sections = {s["id"]: s for s in report["formatted"]["sections"]}
es = sections["executive_summary"]["content"]

summary = es["summary"]
assert len(summary) >= 40, f"FAIL: summary 너무 짧음 ({len(summary)}자)"
# 일반론만 있는지 체크 (gap 관련 키워드 최소 1개)
direction_keywords = ["부드", "선명", "생기", "성숙", "자연", "또렷", "강한", "차가운", "따뜻"]
has_direction = any(kw in summary for kw in direction_keywords)
assert has_direction, f"FAIL: summary에 방향성 키워드 없음: {summary}"
print(f"  ✅ summary ({len(summary)}자): {summary[:60]}...")

print("Phase 5 통과")
```

---

# Phase 6: type_reference + delta_contribution + trend_context

> 남은 P1/P2 항목을 한번에 처리합니다.

## 수정 6-1: type_reference styling_tips deterministic 생성

**파일:** `report_formatter.py` — type_reference 포맷팅 함수

```python
DIRECTION_STYLING_TIPS = {
    ("structure", "decrease"): "각진 라인을 부드럽게 감싸는 쉐딩이 효과적이에요.",
    ("structure", "increase"): "윤곽을 또렷하게 잡아주는 하이라이트가 효과적이에요.",
    ("impression", "decrease"): "눈매와 눈썹 라인을 둥글게 잡아주면 인상이 부드러워져요.",
    ("impression", "increase"): "눈꼬리와 눈썹 끝을 살려주면 인상이 선명해져요.",
    ("maturity", "decrease"): "볼과 눈 아래에 생기를 더하면 어려 보이는 효과가 있어요.",
    ("maturity", "increase"): "음영을 깊게 주면 세련되고 성숙한 분위기가 나요.",
    ("intensity", "decrease"): "전체적으로 힘을 빼고 자연스럽게 마무리하는 게 좋아요.",
    ("intensity", "increase"): "포인트 부위를 과감하게 강조하면 존재감이 살아요.",
}

def build_type_styling_tips(type_label: str, primary_axis: str, delta: float, top_zones: list[str]) -> list[str]:
    tips = []
    tips.append(f"{type_label} 유형의 장점을 살리면서 변화를 주는 게 포인트예요.")

    direction = "decrease" if delta < 0 else "increase"
    key = (primary_axis, direction)
    if key in DIRECTION_STYLING_TIPS:
        tips.append(DIRECTION_STYLING_TIPS[key])

    if top_zones:
        zone_str = ", ".join(top_zones[:2])
        tips.append(f"특히 {zone_str} 부분에 집중하면 변화가 빠르게 느껴져요.")

    return tips
```

type_reference 포맷팅 시 `styling_tips`가 빈 배열이면 위 함수로 생성:

```python
# type_reference 포맷팅부에서
if not content.get("styling_tips"):
    content["styling_tips"] = build_type_styling_tips(
        type_label=content["type_name"],
        primary_axis=gap["primary_direction"],       # 변수명 확인 필요
        delta=gap["vector"][gap["primary_direction"]], # 변수명 확인 필요
        top_zones=[a["category"] for a in action_items[:2]],
    )
```

## 수정 6-2: delta_contribution score 기반 차등화

**파일:** `report_formatter.py` — action_plan 포맷팅부

기존 `1/N` 균등 분배를 score 기반으로 교체:

```python
# 기존 패턴 찾기 (추정):
# delta_contribution = round(1.0 / len(items), 2)

# 교체:
def compute_delta_contributions(action_items: list, action_spec) -> list[float]:
    """ActionSpec의 score/priority 기반으로 contribution 차등 계산"""
    scores = []
    for i, item in enumerate(action_items):
        # action_spec.recommended_actions[i]에서 score 추출
        # 필드명은 Phase 0에서 확인한 것 사용
        if hasattr(action_spec, 'recommended_actions') and i < len(action_spec.recommended_actions):
            action = action_spec.recommended_actions[i]
            score = getattr(action, 'score', None) or getattr(action, 'priority', None) or 1.0
            # priority가 int(1=HIGH, 4=LOW)이면 반전
            if isinstance(score, int) and 1 <= score <= 4:
                score = 5 - score  # 1→4, 2→3, 3→2, 4→1
            scores.append(float(score))
        else:
            scores.append(1.0)

    total = sum(scores) or 1.0
    return [round(s / total, 2) for s in scores]

# 사용:
contributions = compute_delta_contributions(action_items, action_spec)
for i, item in enumerate(action_items):
    item["recommendations"][0]["delta_contribution"] = contributions[i]
```

**주의:** `action_spec` 객체에 접근 가능한지 확인 필요. 포맷팅 함수의 인자로 받고 있는지 체크. 안 받고 있으면 인자 추가.

## 수정 6-3: trend_context fallback + z축 필드 예약

**파일:** `report_formatter.py` — trend_context 포맷팅부

```python
def build_trend_context_fallback(action_spec, user_name: str) -> dict:
    """trend_context가 비어있거나 너무 짧을 때 사용하는 fallback"""
    top_zones = []
    if hasattr(action_spec, 'recommended_actions'):
        top_zones = [a.zone for a in action_spec.recommended_actions[:2]]

    zone_str = ", ".join(top_zones) if top_zones else "주요 포인트"

    return {
        "trends": [{
            "title": "적용 가이드",
            "description": (
                f"{user_name}님의 리포트에서 가장 변화가 큰 포인트는 "
                f"{zone_str} 부분이에요. "
                f"하나씩 순서대로 적용해보면서 자신에게 맞는 강도를 찾아보세요. "
                f"처음엔 가볍게 시작하고, 익숙해지면 점차 강도를 올리는 게 자연스러워요."
            ),
        }],
    }
```

trend_context 포맷팅 시:
```python
tc = content.get("trends", [])
if not tc or len(tc[0].get("description", "")) < 20:
    content = build_trend_context_fallback(action_spec, user_name)
```

z축 필드 예약 (gap_analysis 포맷팅부):
```python
# gap_analysis content에 추가 (값은 None)
gap_content["trend_coordinates"] = None       # 다음 스프린트: 시즌별 트렌드 중심 좌표
gap_content["gap_to_trend"] = None            # 다음 스프린트: 현재 → 트렌드 gap
gap_content["blend_weights"] = None           # 다음 스프린트: aspiration vs trend 비율
```

## 검증 6

```python
report = generate_full_report(...)
sections = {s["id"]: s for s in report["formatted"]["sections"]}

# 6-1: styling_tips 비어있지 않음
tr = sections["type_reference"]["content"]
assert len(tr["styling_tips"]) >= 1, f"FAIL: styling_tips 비어있음"
print(f"  ✅ styling_tips: {tr['styling_tips']}")

# 6-2: delta_contribution 차별화
ap = sections["action_plan"]["content"]
contribs = [item["recommendations"][0]["delta_contribution"] for item in ap["items"]]
assert len(set(contribs)) > 1, f"FAIL: delta_contribution 전부 동일: {contribs}"
print(f"  ✅ delta_contributions: {contribs}")

# 6-3: trend_context 최소 내용
tc = sections["trend_context"]["content"]
assert len(tc["trends"]) >= 1
assert len(tc["trends"][0]["description"]) >= 20, \
    f"FAIL: trend description 짧음: {tc['trends'][0]['description']}"
print(f"  ✅ trend_context: {tc['trends'][0]['description'][:50]}...")

# 6-3: z축 필드 존재 (null이어도 OK)
gap = sections["gap_analysis"]["content"]
assert "trend_coordinates" in gap, "FAIL: trend_coordinates 필드 없음"
assert "gap_to_trend" in gap, "FAIL: gap_to_trend 필드 없음"
print(f"  ✅ z축 필드 예약: trend_coordinates={gap['trend_coordinates']}")

print("Phase 6 통과")
```

---

# Phase 7: 통합 QA

> 전체 수정사항 통합 검증.

## 실행

홍길순 사진 + 인터뷰 데이터, 조찬형 사진 + 인터뷰 데이터 각각으로 리포트 재생성 후 아래 실행.

```python
import re

def qa_report_v3(report: dict, label: str = ""):
    """v3 통합 QA — 모든 Phase 검증 항목 포함"""
    print(f"\n{'='*50}")
    print(f"QA v3: {label or report['formatted']['user_name']}")
    print(f"{'='*50}")

    sections = {s["id"]: s for s in report["formatted"]["sections"]}
    passed = 0
    failed = 0

    def check(name, condition, msg=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}: {msg}")

    # --- Phase 1: percentile ---
    fs = sections["face_structure"]["content"]
    for m in fs["metrics"]:
        check(
            f"percentile_{m['key']}",
            5 <= m["percentile"] <= 95,
            f"percentile={m['percentile']}"
        )

    # --- Phase 2: gap 비문 ---
    gap = sections["gap_analysis"]["content"]
    for item in gap["direction_items"]:
        has_bad = bool(re.search(r"더\s+\S+\s+필요한", item["recommendation"]))
        check(f"gap_rec_{item['axis']}", not has_bad, item["recommendation"][:40])

    check("gap_summary_조사", "도이 " not in gap["gap_summary"], gap["gap_summary"])

    # --- Phase 3: raw 수치 ---
    fi = sections["face_interpretation"]["content"]
    check(
        "overall_no_numbers",
        not contains_raw_metric(fi["overall_impression"]),
        fi["overall_impression"][:50]
    )
    for feat in fi["feature_interpretations"]:
        check(
            f"interp_no_numbers_{feat['feature']}",
            not contains_raw_metric(feat["interpretation"]),
            feat["interpretation"][:40]
        )

    # --- Phase 4: percentile 분포 ---
    percentiles = [m["percentile"] for m in fs["metrics"]]
    all_extreme = all(p <= 10 or p >= 90 for p in percentiles)
    check("percentile_spread", not all_extreme, f"전부 극단: {percentiles}")

    # --- Phase 5: summary ---
    es = sections["executive_summary"]["content"]
    check("summary_length", len(es["summary"]) >= 40, f"{len(es['summary'])}자")
    direction_kw = ["부드", "선명", "생기", "성숙", "자연", "또렷", "강한", "차가운", "따뜻"]
    check("summary_direction", any(k in es["summary"] for k in direction_kw), es["summary"][:50])

    # --- Phase 6 ---
    tr = sections["type_reference"]["content"]
    check("styling_tips", len(tr.get("styling_tips", [])) >= 1)

    ap = sections["action_plan"]["content"]
    contribs = [item["recommendations"][0]["delta_contribution"] for item in ap["items"]]
    check("delta_diff", len(set(contribs)) > 1, f"{contribs}")

    tc = sections["trend_context"]["content"]
    check("trend_content", len(tc["trends"][0].get("description", "")) >= 20)

    check("z_field_reserved", "trend_coordinates" in gap)

    # --- 결과 ---
    total = passed + failed
    print(f"\n{'='*50}")
    print(f"결과: {passed}/{total} 통과, {failed} 실패")
    if failed == 0:
        print("🎉 QA v3 전체 통과")
    else:
        print("⚠️  실패 항목 수정 필요")
    print(f"{'='*50}")
    return failed == 0


# 실행
report_hong = generate_full_report(hong_image, hong_interview, hong_context)
report_cho = generate_full_report(cho_image, cho_interview, cho_context)

ok1 = qa_report_v3(report_hong, "홍길순 (v3)")
ok2 = qa_report_v3(report_cho, "조찬형 (v3)")

assert ok1 and ok2, "QA 실패 — 위 로그 확인"
```

---

# 실행 순서 요약

```
Phase 0  사전 확인 — 파일/함수 위치 파악                    (10분)
Phase 1  percentile clamp 5~95                             (15분)
Phase 2  gap recommendation 비문 → 템플릿 교체              (30분)
Phase 3  interpretation raw 수치 제거 (후처리 + 프롬프트)    (30분)
Phase 4  SCUT 캘리브레이션 → FACE_STATS 교체                (1~2시간)
Phase 5  executive_summary 구체성 복구                      (30분)
Phase 6  styling_tips + delta_contribution + trend_context  (45분)
Phase 7  통합 QA (홍길순 + 조찬형)                          (15분)
```

Phase 1~3은 캘리브레이션 데이터 없이 바로 실행 가능.
Phase 4는 SCUT-FBP5500 이미지 필요 — 없으면 Phase 5~6 먼저 진행 후 나중에 4 실행.