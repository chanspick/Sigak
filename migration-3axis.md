# SIGAK 3축 좌표계 — 현행 시스템 문서

> 마이그레이션 완료: 2026-04-09
> 상태: **Phase 0~5 전부 완료, 남성 파이프라인 확장 완료**

---

## 좌표계 개요

3축 미감 좌표계 (shape/volume/age). 모든 정의는 YAML SSOT에서 로드.

| 축 | name_kr | -1 (low) | +1 (high) | 피처 수 |
|---|---|---|---|---|
| shape | 외형 | Soft (소프트) | Sharp (샤프) | 5 |
| volume | 존재감 | Subtle (서틀) | Bold (볼드) | 4 |
| age | 무드 | Fresh (프레시) | Mature (매추어) | 3 |

피처 겹침: **0건** (12피처가 3축에 배타적 배치)

### SSOT 파일

| 파일 | 역할 |
|------|------|
| `sigak/data/axis_config.yaml` | 축 정의, 피처 매핑, 가중치, 방향 |
| `sigak/data/calibration_3axis.yaml` | observed_ranges, 캘리브레이션 통계 |
| `sigak/data/type_anchors.json` | 16앵커 (여성 8 + 남성 8), 3축 coords |

---

## 앵커 체계

### 여성 (type_1 ~ type_8, id 1~8)

| type | name_kr | coords | quadrant |
|---|---|---|---|
| 1 | 따뜻한 첫사랑 | S:-0.8, V:-0.7, A:-0.8 | Soft Fresh |
| 2 | 사랑스러운 인형 | S:-0.8, V:+0.7, A:-0.8 | Soft Fresh |
| 3 | 차갑지만 동안 | S:+0.8, V:-0.7, A:-0.8 | Sharp Fresh |
| 4 | 또렷한 에너지 | S:+0.8, V:+0.7, A:-0.8 | Sharp Fresh |
| 5 | 편안한 우아함 | S:-0.8, V:-0.7, A:+0.8 | Soft Mature |
| 6 | 부드러운 카리스마 | S:-0.8, V:+0.7, A:+0.8 | Soft Mature |
| 7 | 절제된 시크 | S:+0.8, V:-0.7, A:+0.8 | Sharp Mature |
| 8 | 날카로운 카리스마 | S:+0.8, V:+0.7, A:+0.8 | Sharp Mature |

### 남성 (type_1m ~ type_8m, id 11~18)

| type | name_kr | coords | quadrant |
|---|---|---|---|
| 1m | 따뜻한 소년 | S:-0.8, V:-0.7, A:-0.8 | Soft Fresh |
| 2m | 귀여운 존재감 | S:-0.8, V:+0.8, A:-0.8 | Soft Fresh |
| 3m | 차가운 동안 | S:+0.8, V:-0.7, A:-0.8 | Sharp Fresh |
| 4m | 또렷한 에너지 | S:+0.8, V:+0.8, A:-0.8 | Sharp Fresh |
| 5m | 편안한 형 | S:-0.8, V:-0.7, A:+0.8 | Soft Mature |
| 6m | 부드러운 카리스마 | S:-0.8, V:+0.8, A:+0.8 | Soft Mature |
| 7m | 절제된 시크 | S:+0.8, V:-0.7, A:+0.8 | Sharp Mature |
| 8m | 날카로운 카리스마 | S:+0.8, V:+0.8, A:+0.8 | Sharp Mature |

> "따뜻한" = 온화한 인상. 색채 warm tone이 아님.

---

## 파이프라인 흐름

```
사진(bytes) → face.py → FaceFeatures (24필드 + brow_eye_distance)
  → coordinate.py → 3축 좌표 {shape, volume, age}  [axis_config.yaml + calibration_3axis.yaml]
  → similarity.py → similar_types (gender 필터링, type_anchors.json coords 매칭)
  → cluster.py → cluster_result (3축 시그니처 라벨링)
인터뷰(text) → llm.py → aspiration_coords {shape, volume, age}
  → coordinate.py compute_gap() → {vector, magnitude, primary_direction}
  → action_spec.py → ActionSpec (gender별: 여성=메이크업, 남성=그루밍+체형)
  → report_formatter.py → ReportData (aesthetic_map + direction_items + API 계약)
  → 프론트 렌더링
```

### Gender 분기

| 모듈 | 여성 | 남성 |
|------|------|------|
| AXIS_ACTION_RULES | 메이크업 18규칙 | 그루밍+체형 22규칙 |
| report_mode | makeup_female_v0 | grooming_male_v0 |
| overlay | 메이크업 시뮬레이션 | 비활성 (텍스트 추천만) |
| 폴백 카테고리 | 메이크업/헤어/스타일링 | 헤어/그루밍/체형관리/스킨케어 |
| 앵커 매칭 | type_1~8 (female) | type_1m~8m (male) |

---

## API 계약: direction_items

```typescript
interface DirectionItem {
  axis: string;              // "shape" | "volume" | "age"
  name_kr: string;           // "외형" | "존재감" | "무드"
  axis_description: string;
  label_low: string;         // "소프트" | "서틀" | "프레시"
  label_high: string;        // "샤프" | "볼드" | "매추어"
  from_score: number;        // [-1, 1]
  to_score: number;          // [-1, 1]
  delta: number;
  from_label: string;        // "약간 소프트"
  to_label: string;          // "샤프 방향으로" | "현재 유지"
  difficulty: string;        // "유지" | "작은 변화" | "중간 변화" | "큰 변화"
  recommendation: string;
}
```

delta < 0.15: "현재 유지" 표시. delta < 0.05: 카드 숨김.

---

## 2D 미적 맵

```
X축: Shape (Soft ↔ Sharp) — 고정
Y축: Age (Fresh ↔ Mature) — 고정
점 크기: Volume (Subtle=작은 점, Bold=큰 점)
사분면: Soft Fresh / Sharp Fresh / Soft Mature / Sharp Mature
```

백엔드에서 `aesthetic_map` JSON으로 내려줌. 프론트는 자체 축 라벨 없이 백엔드 라벨만 사용.

---

*Updated: 2026-04-09*
*마이그레이션 이력: archive/feedback-legacy.md, archive/problems-legacy.md, archive/roadmap-legacy.md*
