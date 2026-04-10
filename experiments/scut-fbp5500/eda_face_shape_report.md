# EDA + Calibration Report: face_shape & skin_tone

> 데이터 소스: SCUT-FBP5500 AF (Asian Female), n=2000
> 캘리브레이션 파일: `experiments/scut-fbp5500/calibration_af_insightface.json`
> 분석 대상: `sigak/pipeline/face.py`

## 1. 현재 임계값 분석

### 현재 `_classify_face_shape` 로직

```python
def _classify_face_shape(ratio, jaw_angle, cheekbone, forehead) -> str:
    if ratio > 1.5 and jaw_angle < 125:     return "oblong"
    elif ratio < 1.2 and jaw_angle > 140:   return "round"
    elif ratio < 1.3 and jaw_angle < 120:   return "square"
    elif cheekbone > 0.5 and forehead > 0.38: return "heart"
    else:                                    return "oval"
```

### 캘리브레이션 데이터 요약

| Metric | mean | std | min | p5 | p25 | p50 | p75 | p95 | max |
|--------|------|-----|-----|-----|------|------|------|------|-----|
| face_length_ratio | 1.227 | 0.052 | 1.048 | 1.138 | 1.190 | 1.232 | 1.265 | 1.307 | 1.367 |
| jaw_angle | 102.925 | 10.705 | 84.700 | 88.600 | 92.600 | 103.600 | 111.700 | 119.905 | 131.800 |
| cheekbone_prominence | 0.628 | 0.088 | 0.336 | 0.494 | 0.565 | 0.625 | 0.687 | 0.781 | 0.913 |
| forehead_ratio | 0.412 | 0.044 | 0.308 | 0.347 | 0.370 | 0.421 | 0.448 | 0.475 | 0.530 |

### 조건별 문제점

**1) oblong (ratio > 1.5 AND jaw_angle < 125)**
- face_length_ratio max = 1.367, p95 = 1.307
- ratio > 1.5 을 만족하는 얼굴이 데이터 범위 밖 (max 1.367)
- 결과: **0%** 의 얼굴이 oblong 으로 분류됨

**2) round (ratio < 1.2 AND jaw_angle > 140)**
- jaw_angle max = 131.8
- jaw_angle > 140 을 만족하는 얼굴이 전혀 없음 (max 131.8)
- 결과: **0%** 의 얼굴이 round 로 분류됨

**3) square (ratio < 1.3 AND jaw_angle < 120)**
- ratio < 1.3: 약 93% (p90=1.293)
- jaw_angle < 120: 약 95% (p90=117.2)
- 두 조건의 교집합이 크므로, 대부분 heart/oval 전에 square로 잡힘

**4) heart (cheekbone > 0.5 AND forehead > 0.38)**
- cheekbone > 0.5: 약 94% (p5=0.494)
- forehead > 0.38: 약 70% (p10=0.354)
- 두 조건 모두 대다수가 만족 -> square에 안 잡힌 나머지가 대부분 heart

**5) oval (else / catch-all)**
- square와 heart가 대부분 흡수하므로, oval 비율이 매우 낮을 수 있음
- 또는 square 조건이 너무 넓어서 oval이 거의 없음

### 예상 분포 (현재 로직)

| Type | 예상 비율 | 문제 |
|------|----------|------|
| oblong | ~0% | ratio > 1.5 조건 도달 불가 |
| round | ~0% | jaw_angle > 140 조건 도달 불가 |
| square | ~60-70% | ratio < 1.3 AND jaw_angle < 120 조건이 너무 관대 |
| heart | ~25-35% | square 에 안 잡힌 나머지 대부분 |
| oval | ~0-5% | catch-all 이지만 도달 어려움 |

## 2. 새로운 분류 시스템 제안

### 설계 원칙

1. **점수 기반 분류 + oval penalty**: 모든 유형에 가중 선형 유사도 계산 후, oval 점수에만 penalty 계수를 곱하여 중앙값 편향 보정
2. **퍼센타일 기반 정규화**: 원시 값 대신 0-1 정규화 점수를 사용하여 각 피처의 스케일 차이를 제거
3. **7가지 유형**: oval, round, heart, square, oblong, inverted_triangle, diamond
4. **목표 분포**: 각 유형 5-35%, 단일 유형 최대 35%
5. **OVAL_PENALTY**: 0.88 (낮출수록 oval 비율 감소)

### 퍼센타일 기반 정규화 기준

각 피처를 [0, 1] 범위로 정규화한다. 0 = 데이터 최소 방향, 1 = 최대 방향.

```
face_length_ratio: min=1.048, max=1.367
  -> norm = (value - 1.048) / (1.367 - 1.048)
  -> p25_norm = 0.445
  -> p50_norm = 0.577
  -> p75_norm = 0.680

jaw_angle: min=84.700, max=131.800
  -> norm = (value - 84.700) / (131.800 - 84.700)
  -> p25_norm = 0.168
  -> p50_norm = 0.401
  -> p75_norm = 0.573

cheekbone_prominence: min=0.336, max=0.913
  -> norm = (value - 0.336) / (0.913 - 0.336)
  -> p25_norm = 0.397
  -> p50_norm = 0.501
  -> p75_norm = 0.608

forehead_ratio: min=0.308, max=0.530
  -> norm = (value - 0.308) / (0.530 - 0.308)
  -> p25_norm = 0.279
  -> p50_norm = 0.509
  -> p75_norm = 0.631

```

### 얼굴형별 시그니처 정의

각 얼굴형은 4개 피처에 대한 `(target, weight)` 쌍으로 정의된다.
- `target`: 해당 유형에서 기대되는 정규화 값 (0-1)
- `weight`: 해당 피처가 이 유형 판별에서 갖는 중요도
- 점수 = sum( weight * (1 - |norm - target|) ) / sum(weight)

| Type | ratio target | ratio w | jaw target | jaw w | cheek target | cheek w | forehead target | forehead w |
|------|-------------|---------|------------|-------|--------------|---------|-----------------|------------|
| oval | 0.55 | 1.5 | 0.45 | 1.5 | 0.50 | 1.5 | 0.50 | 1.5 |
| round | 0.15 | 2.0 | 0.85 | 2.5 | 0.40 | 1.0 | 0.50 | 0.5 |
| oblong | 0.90 | 2.5 | 0.50 | 0.5 | 0.45 | 0.5 | 0.50 | 0.5 |
| square | 0.30 | 1.5 | 0.10 | 2.5 | 0.35 | 1.0 | 0.55 | 1.0 |
| heart | 0.50 | 0.5 | 0.25 | 2.0 | 0.55 | 1.5 | 0.80 | 2.5 |
| inverted_triangle | 0.55 | 0.5 | 0.15 | 2.0 | 0.80 | 2.5 | 0.60 | 1.5 |
| diamond | 0.60 | 1.0 | 0.20 | 1.5 | 0.85 | 3.0 | 0.25 | 2.5 |

### 시그니처 해석

- **oval**: 중간값 유형 (penalty 0.88 적용으로 다른 유형과 공정 경쟁)
- **round**: 짧은 얼굴(ratio low), 넓은 턱(jaw high) - 핵심 차별화 피처에 높은 weight(2.5)
- **oblong**: 긴 얼굴(ratio high, weight 3.0) -> 가장 강한 차별화
- **square**: 짧은 얼굴, 매우 각진 턱(jaw very low, weight 3.0)
- **heart**: 좁은 턱 + 매우 넓은 이마(forehead 0.80, weight 2.5)
- **inverted_triangle**: 좁은 턱 + 높은 광대(cheek 0.80, weight 2.5)
- **diamond**: 매우 높은 광대(cheek 0.85, weight 3.0) + 좁은 이마(forehead 0.25, weight 2.5)

## 3. 시뮬레이션 결과 (새 알고리즘)

퍼센타일 격자점(7x7x7x7 = 2401개 조합, 가중치 적용) 기반 예상 분포:

| Type | 예상 비율 | 상태 |
|------|----------|------|
| oval | 8.3% | OK |
| round | 9.3% | OK |
| oblong | 20.2% | OK |
| square | 20.3% | OK |
| heart | 17.3% | OK |
| inverted_triangle | 10.4% | OK |
| diamond | 14.1% | OK |

모든 유형이 목표 범위(5-35%) 내에 있습니다.

### 유형별 대표 프로파일

각 유형에서 가장 높은 점수를 받는 퍼센타일 조합:

**oval** (score=0.861):
  ratio=1.232, jaw=103.6, cheek=0.625, forehead=0.421
**round** (score=0.912):
  ratio=1.138, jaw=119.9, cheek=0.565, forehead=0.421
**oblong** (score=0.928):
  ratio=1.307, jaw=111.7, cheek=0.625, forehead=0.421
**square** (score=0.978):
  ratio=1.138, jaw=90.1, cheek=0.522, forehead=0.421
**heart** (score=0.941):
  ratio=1.190, jaw=92.6, cheek=0.625, forehead=0.475
**inverted_triangle** (score=0.974):
  ratio=1.232, jaw=92.6, cheek=0.781, forehead=0.448
**diamond** (score=0.952):
  ratio=1.232, jaw=92.6, cheek=0.781, forehead=0.370

## 4. 제안 코드: `_classify_face_shape` (v2)

다음 코드를 `face.py`의 `_classify_face_shape` 함수를 교체하는 데 사용한다.

```python
# ── 얼굴형 분류 (v2: SCUT-FBP5500 캘리브레이션 기반) ──

# 캘리브레이션 범위 (SCUT-FBP5500 AF, n=2000)
_FACE_CAL = {
    "ratio": (1.048, 1.367),   # face_length_ratio (min, max)
    "jaw":   (84.7, 131.8),  # jaw_angle (min, max)
    "cheek": (0.336, 0.913),   # cheekbone_prominence (min, max)
    "fore":  (0.308, 0.530),    # forehead_ratio (min, max)
}

# oval 의 target 이 데이터 중앙값과 거의 일치하여 항상 높은 점수를 받으므로,
# oval 점수에 penalty 를 곱하여 다른 유형과 공정하게 경쟁시킨다.
# 이 값을 낮추면 oval 비율 감소, 높이면 증가.
_OVAL_PENALTY = 0.88

# 얼굴형 시그니처: (target_normalized, weight)
# target: 0-1 정규화 공간에서 해당 유형의 이상적 위치
# weight: 이 피처가 해당 유형 판별에 미치는 중요도
_FACE_SHAPE_SIGNATURES = {
    "oval":                {"ratio": (0.55, 1.5), "jaw": (0.45, 1.5), "cheek": (0.5, 1.5), "fore": (0.5, 1.5)},
    "round":               {"ratio": (0.15, 2.0), "jaw": (0.85, 2.5), "cheek": (0.4, 1.0), "fore": (0.5, 0.5)},
    "oblong":              {"ratio": (0.9, 2.5), "jaw": (0.5, 0.5), "cheek": (0.45, 0.5), "fore": (0.5, 0.5)},
    "square":              {"ratio": (0.3, 1.5), "jaw": (0.1, 2.5), "cheek": (0.35, 1.0), "fore": (0.55, 1.0)},
    "heart":               {"ratio": (0.5, 0.5), "jaw": (0.25, 2.0), "cheek": (0.55, 1.5), "fore": (0.8, 2.5)},
    "inverted_triangle":   {"ratio": (0.55, 0.5), "jaw": (0.15, 2.0), "cheek": (0.8, 2.5), "fore": (0.6, 1.5)},
    "diamond":             {"ratio": (0.6, 1.0), "jaw": (0.2, 1.5), "cheek": (0.85, 3.0), "fore": (0.25, 2.5)},
}


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
    norms = {
        "ratio": _normalize_feature(ratio, *cal["ratio"]),
        "jaw":   _normalize_feature(jaw_angle, *cal["jaw"]),
        "cheek": _normalize_feature(cheekbone, *cal["cheek"]),
        "fore":  _normalize_feature(forehead, *cal["fore"]),
    }

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

## 5. 피부톤 (skin_tone) 분석 및 개선안

### 현재 로직

```python
warmth = (b_mean - 128) + (a_mean - 128) * 0.5
if warmth > 8:      tone = "warm"
elif warmth < -3:   tone = "cool"
else:               tone = "neutral"
```

### 문제점

1. **임계값 (8, -3) 의 근거 없음**: 아시안 피부에 대한 캘리브레이션 없이 설정됨
2. **비대칭 범위**: warm 임계값(8)과 cool 임계값(-3)이 0을 중심으로 대칭이 아님
3. **캘리브레이션 데이터에 warmth 없음**: `skin_brightness` 만 존재 (mean=0.617, std=0.162)
4. **LAB 색공간 특성 미반영**: 아시안 피부톤의 a*, b* 분포 특성을 고려하지 않음

### 아시안 피부톤의 LAB 색공간 특성 (문헌 기반)

동아시아 여성 피부의 일반적인 LAB 값 범위 (조명 보정 후):

| Parameter | 일반 범위 | 설명 |
|-----------|----------|------|
| L* | 55-75 | 밝기 (0=black, 100=white) |
| a* | 5-15 | 적색-녹색 축 (양수=적색) |
| b* | 15-30 | 황색-청색 축 (양수=황색) |

OpenCV LAB 인코딩: L* -> [0, 255], a* -> a_mean (128=neutral), b* -> b_mean (128=neutral)
따라서 아시안 피부의 전형적 OpenCV LAB 값:
- a_mean: ~133-143 (약간 적색)
- b_mean: ~143-158 (황색 편향)

이 경우 warmth = (b_mean - 128) + (a_mean - 128) * 0.5:
- 전형적 범위: (15~30) + (5~15) * 0.5 = 17.5 ~ 37.5
- **대부분 warmth > 8 -> 거의 모든 얼굴이 'warm'으로 분류됨**

### 개선안

#### 방법 1: 상대적 warmth (아시안 피부톤 중심값 기준 편차) [권장]

```python
# 아시안 피부 기준 중앙값 (SCUT-FBP5500 기반 추정)
# 추후 실제 a_mean, b_mean 캘리브레이션 데이터로 교체 필요
_SKIN_WARMTH_CENTER = 22.0  # 전형적 아시안 피부의 warmth 중앙값 추정
_SKIN_WARMTH_STD = 6.0      # warmth 표준편차 추정

warmth_raw = (b_mean - 128) + (a_mean - 128) * 0.5
warmth_z = (warmth_raw - _SKIN_WARMTH_CENTER) / _SKIN_WARMTH_STD

if warmth_z > 0.5:        tone = "warm"
elif warmth_z < -0.5:     tone = "cool"
else:                     tone = "neutral"
```

#### 방법 2: 밝기 + warmth 결합 분류

```python
# skin_brightness 캘리브레이션: mean=0.617, std=0.162
# p25=0.498, p50=0.644, p75=0.751

warmth_raw = (b_mean - 128) + (a_mean - 128) * 0.5

# 밝기에 따라 warmth 기준값 보정
# 어두운 피부 -> warmth 값이 낮아지는 경향 반영
brightness_norm = (l_mean - 0.129) / (0.944 - 0.129)
warmth_threshold_warm = 15 + brightness_norm * 10   # 밝을수록 높은 기준
warmth_threshold_cool = 10 + brightness_norm * 8    # 밝을수록 높은 기준

if warmth_raw > warmth_threshold_warm:   tone = 'warm'
elif warmth_raw < warmth_threshold_cool: tone = 'cool'
else:                                    tone = 'neutral'
```

### 권장 사항

1. **즉시 적용 가능**: 방법 1 (상대적 warmth)
   - `_SKIN_WARMTH_CENTER`와 `_SKIN_WARMTH_STD`는 추정값
   - 추후 실제 a_mean, b_mean 캘리브레이션으로 정밀화 가능

2. **캘리브레이션 보완 필요**: 향후 `calibrate_face_stats.py` 실행 시
   `skin_warmth_score` (= warmth raw 값)의 통계도 캘리브레이션 JSON에 추가하면
   정확한 CENTER/STD 를 사용할 수 있음

3. **다인종 확장 시**: 인종별 CENTER/STD 테이블을 두고, 사용자 프로파일 또는 자동 감지로 선택

## 6. 다음 단계

1. 이 리포트의 시그니처 가중치를 리뷰하고, 필요시 조정
2. face.py 의 `_classify_face_shape` 함수를 제안 코드로 교체
3. `_analyze_skin_tone_from_image`에 상대적 warmth 방식 적용
4. `calibrate_face_stats.py` 에 `skin_warmth_score` 통계 추가
5. 교체 후 기존 테스트 이미지로 분포 검증 실행
