# 남성 헤어 파이프라인 gap audit

> 2026-04-21 audit. Phase B 백로그용 문서. 이번 단계에선 수정 없음, 목록화만.
> 결론: `build_hair_spec(gender="male")` 는 **crashes 없이 돌지만 여성 스타일을 반환**.

## 실행 요약

현재 상태에서 남성 유저가 PI 리포트를 해제하면:

- 리포트는 500 없이 완주 (nobody crashes)
- `hair_recommendation` 섹션에 **여성 스타일 그대로 추천됨** (풀뱅, 시스루뱅, 칼단발, 단발 레이어드컷 등)
- confidence 점수도 정상 범위로 뿌려져서 유저가 **틀린 추천을 확신하며 볼 가능성** 있음

즉 "침묵의 여성 디폴트" (silent female default) 상태.

## 원인 · 코드 경로

`build_hair_spec(gender)` 가 `gender` 인자를 받지만 본문에서 한 번도 참조하지 않음.
여성이든 남성이든 같은 `HAIR_STYLES` 딕셔너리 (24개 여성 코드) 순회.

```
main.py:970
  build_hair_spec(face_features, interview, gap, gender=user.gender)
    → hair_spec.py:424-513
      → gender 파라미터 받지만 line 449-513 어디에서도 사용 0회
      → HAIR_STYLES 딕셔너리 전체 순회 (pipeline/hair_styles.py:17-316, 24개 모두 여성)
      → 반환값을 report_formatter._build_hair_recommendation 이 렌더
        → 여기서도 gender 인자 받지만 사용 안 함 (report_formatter.py:1038-1117)
```

## 상세 gap 목록

| # | 위치 | 문제 | 심각도 | 타입 |
|---|---|---|---|---|
| 1 | `sigak/pipeline/hair_spec.py:424-426` | `build_hair_spec()` 시그니처에 `gender` 있지만 본문 미사용 | critical | silent_female_default |
| 2 | `sigak/pipeline/hair_spec.py:456-469` | 스타일 순회 시 gender 필터링 없음 | critical | missing_branch |
| 3 | `sigak/pipeline/hair_styles.py:17-316` | HAIR_STYLES 24개 전부 여성 코드 (풀뱅, 칼단발 등). gender 필드 없음 | critical | hardcoded_female |
| 4 | `sigak/pipeline/hair_styles.py:319-328` | `get_front_styles()` / `get_back_styles()` / `get_etc_styles()` 에 gender 파라미터 없음 | medium | missing_branch |
| 5 | `sigak/pipeline/report_formatter.py:1038-1042` | `_build_hair_recommendation()` 가 gender 받지만 미사용 | medium | silent_female_default |
| 6 | `sigak/main.py:970` | gender 를 `build_hair_spec` 에 넘기지만 내부에서 소실됨 | medium | missing_branch |
| 7 | `sigak/tests/test_hair_spec.py:53,71,92,107,123,133,149` | 모든 테스트가 implicit default `gender="female"` 로만 돌음. 남성 케이스 커버리지 0 | high | missing_test_coverage |

## 관련 자산 현황 (참고)

- ✓ 남성 앵커 임베딩 8개 (`sigak/data/embeddings/male/`) — 2026-04-21 커밋 `740979e`
- ✓ 남성 헤어 레퍼런스 이미지 12개 (`sigak/data/anchors/hair/male_hair/`) — 동 커밋
- ✓ `hair_styles.json` 에 `male_styles` 12 entries — 2026-04-21 커밋 `3c37423`
- ✗ `HAIR_STYLES` Python 딕셔너리 (`hair_styles.py`) 에 남성 entry 없음
- ✗ 남성 스타일별 scoring 규칙 (volume/texture/age_fit 태그) 미정의

## Phase B 수정 map

**order 는 의존 순서. 시간 추정 포함 금지 (본인 요청).**

1. `hair_styles.py:17-316` — 각 style dict 에 `"gender": ["female"]` 또는 `["male", "female"]` 필드 추가
2. `hair_styles.py:17+` — 남성 12개 style 추가 (id `h-m01`~`h-m12`, `hair_styles.json::male_styles` 와 동일 ID). image_vector / curl_intensity / gaze_effect 스코링 속성 정의 필요
3. `hair_styles.py:319-328` — `get_front_styles(gender=None)` 등 helper 에 gender 필터 추가
4. `hair_spec.py:456-469` — 스타일 순회 전 gender 필터링 (`get_front_styles(gender=gender)` 사용)
5. `hair_spec.py:424-513` — `gender` 파라미터 실제 사용. 남성 전용 scoring 가중치 조정 (여성 `image_vector` 5축 [러블리/청순/시크/우아/개성] 이 남성에도 유효한지 재검토 필요)
6. `hair_rules.py` — FEATURE_MODIFIERS / CROSS_EFFECTS 의 여성 특화 문구 감사 (예: "앞머리 길이" 가정이 남성 cut 체계와 안 맞을 가능성)
7. `report_formatter.py:1038-1117` — `gender` 가드 추가. 반환된 style id 가 유저 성별과 일치하는지 검증, 불일치 시 fallback 문구
8. `main.py:957, 970, 983-989` — gender 가 파이프라인 전 구간 전파되는지 로깅으로 검증
9. `test_hair_spec.py` — `test_build_hair_spec_male()` 신규 테스트 추가. output 이 여성 결과와 다른지 검증

## MVP 임시 방어 옵션 (Phase B 전까지)

이 audit 이 "수정 안 함" 이지만 MVP 유저 보호 관점에서 3가지 중 하나가 권장됨:

- **(A) 남성 PI 해제 잠정 차단**: `routes/pi.py::unlock_pi` 에서 gender=="male" 시 409 반환 ("남성 PI 리포트 준비 중"). 베타 기간 여성만 오픈
- **(B) 남성 hair_recommendation 섹션 숨김**: `format_report_for_frontend` 가 남성일 때 hair_recommendation 을 리턴 dict 에서 제거. 다른 8개 섹션은 정상
- **(C) 렌더 시 경고 배지**: 남성 hair_recommendation 에 "데이터 확장 중, 참고용" 배지 표시 (유저에게 신뢰도 낮다고 명시적 공지)

MVP 의사결정 필요 항목.

## 관련 커밋

- `740979e` feat(data): male type anchor pipeline activation
- `3c37423` feat(data): hair_styles.json male_styles section (minimal)
- 이 문서: audit 만, 코드 변경 없음

## 참조

- `sigak/data/anchors/male/description.md` — 남성 8유형 좌표/특징 정의
- `sigak/data/type_anchors.json::type_1m..type_8m` — JSON 엔트리
