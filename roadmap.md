# SIGAK 전체 로드맵 — Phase 0 ~ Phase 12

> 생성일: 2026-04-09
> 현재 상태: Phase 0 진행 중 (4/10 런칭 대응)
> 이 문서는 런칭 핫픽스부터 장기 확장까지 전체 경로를 담는다.

---

## 현재 위치

```
✅ 완료: v4 UX 오버홀 (Phase 1 백엔드 7개 + 프론트 6개)
         스킨톤 6타입 파이프라인
         오버레이 렌더러 v0
🔧 진행: Phase 0 핫픽스 (극성 반전, 라벨 통일)
📋 예정: 3축 전환, 캘리브레이션, 오버레이 통합, 동적 팔레트, 3D 시각화
```

---

# Phase 0: 런칭 핫픽스 (4/10 전)

> 4축 유지. 치명적 버그만 수정. 결제 활성화.

| # | 작업 | 파일 | 상태 |
|---|------|------|------|
| 0-1 | similarity.py 극성 반전 수정 | similarity.py | 🔧 |
| 0-2 | gap_summary 라벨 소스 통일 | report_formatter.py | 🔧 |
| 0-3 | v4.1 UI 잔수정 마무리 | 프론트 전반 | 🔧 |
| 0-4 | 결제 시스템 활성화 | 결제 모듈 | 📋 |
| 0-5 | 모바일 갤러리 업로드 (capture 속성 제거) | 업로드 컴포넌트 | 🔧 |

### 검증
```
[ ] 리포트 1건 생성 → 유형 매칭 방향 정상
[ ] 극성 반전 해소 확인
[ ] 결제 플로우 정상
[ ] 모바일 갤러리 접근 정상
```

### 런칭 KPI
- Primary: 7일 내 50 paid diagnostics
- Meta Ads F/20s 서울 타겟

---

# Phase 0.5: 3축 캘리브레이션

> 3축 전환 전 필수 선행 단계.
> SCUT-FBP5500 AF 2000장으로 정규화 범위와 분포를 실측.

### 선행 조건
- 3축 migration spec v2 확정
- axis_config.yaml 초안 작성
- face.py에 brow_eye_distance 계산 추가
- 3축 compute_coordinates() 임시 구현

### 작업

| # | 작업 | 산출물 |
|---|------|--------|
| 0.5-1 | axis_config.yaml 초안 | sigak/data/axis_config.yaml |
| 0.5-2 | brow_eye_distance 계산 추가 | face.py |
| 0.5-3 | compute_coordinates() 3축 임시 구현 | coordinate.py (임시) |
| 0.5-4 | calibrate_ranges.py 작성 및 실행 | scripts/calibrate_ranges.py |
| 0.5-5 | 캘리브레이션 결과 검토 및 반영 | sigak/data/calibration_results.yaml |
| 0.5-6 | (조건부) suggest_weights.py | scripts/suggest_weights.py |
| 0.5-7 | 호감도 메타데이터 분석 | calibration_results.yaml에 포함 |

### calibrate_ranges.py 산출물
```yaml
# calibration_results.yaml
observed_ranges:
  jaw_angle: {p5: TBD, p95: TBD, mean: TBD, std: TBD}
  # ... 12개 피처 전부

axis_distribution:
  shape:  {mean: TBD, std: TBD, min: TBD, max: TBD}
  volume: {mean: TBD, std: TBD, min: TBD, max: TBD}
  age:    {mean: TBD, std: TBD, min: TBD, max: TBD}

axis_correlation:
  shape_volume: TBD    # |corr| > 0.30이면 확인 필요
  shape_age: TBD
  volume_age: TBD

anchor_proximity:
  type_1: {count: TBD, avg_distance: TBD}
  # ... 8개 앵커

sigma_recommendation: TBD  # 기본값 1.0, 실측 기반 추천

skin_tone_thresholds:
  warmth_warm_min: TBD
  warmth_cool_max: TBD
  chroma_clear_min: TBD

attractiveness_analysis:
  axis_correlation:
    shape: TBD     # 낮을수록 좋음 (미인 편향 없음)
    volume: TBD
    age: TBD
  anchor_distribution:
    type_1: {count: TBD, avg_score: TBD}
    # ... 8개
  verdict: TBD
```

### suggest_weights.py (조건부 실행)
```
실행 조건: calibrate_ranges 결과에서 축 분포가 뭉치는 경우만
대상: volume, age 축만 (shape 고정)
방법: grid search, 현재값 ±0.10 범위, 합 1.0 유지
산출물: 후보 weight 세트 5개 + 점수 리포트
반영: 자동 반영 금지, 수동 확정
```

### 검증
```
[ ] 12개 피처 추출 성공률 확인
[ ] observed_ranges 전 피처 생성 완료
[ ] 3축 좌표 평균이 과도하게 한쪽으로 치우치지 않음
[ ] volume 축 분산 충분
[ ] 축 간 상관계수 |corr| < 0.30
[ ] sigma 추천값 산출 완료
[ ] 8앵커 인근 분포 확인 완료
[ ] 호감도-축 상관 낮음 확인
[ ] Phase 1 진입 판단: OK / NG (피처 배치 재조정 필요)
```

---

# Phase 1: 백엔드 좌표계 교체

> coordinate.py 전면 재작성. 3축 YAML config 로드 구조.

| # | 작업 | 파일 |
|---|------|------|
| 1-1 | AXIS_DEFINITIONS → axis_config.yaml 로드 | coordinate.py |
| 1-2 | compute_coordinates() 3축 재작성 | coordinate.py |
| 1-3 | compute_gap() 3축 재작성 | coordinate.py |
| 1-4 | get_axis_labels() / get_all_axis_labels() | coordinate.py |
| 1-5 | OBSERVED_RANGES → calibration_results에서 로드 | coordinate.py |
| 1-6 | 기존 4축 AxisDefinition 클래스 삭제 | coordinate.py |

### 핵심 원칙
- coordinate.py + axis_config.yaml이 유일한 라벨 소스
- 다른 파일은 get_axis_labels()로만 접근
- 가중치 변경은 YAML 수정으로 해결, 코드 배포 불필요

### 검증
```
[ ] 3축 좌표 출력 정상
[ ] 전 축 [-1, +1] 범위
[ ] missing 피처(brow_eye_distance=None) fallback 정상
[ ] primary_shift_kr 라벨 일치
```

---

# Phase 2: 앵커 데이터 + similarity 교체

> 16앵커 → 8앵커. similarity.py 3축 기반.

| # | 작업 | 파일 |
|---|------|------|
| 2-1 | type_anchors.json 전면 교체 (8앵커) | data/type_anchors.json |
| 2-2 | 기존 16앵커 → 8앵커 매핑 정리 | 데이터 |
| 2-3 | similarity.py 3축 유클리드 거리 재작성 | similarity.py |
| 2-4 | sigma=1.0 적용 (캘리브레이션 결과 반영) | similarity.py |
| 2-5 | 기존 axis_labels dict 전량 삭제 | similarity.py |
| 2-6 | axes_3d, axes_3d_definition, axis_roles 삭제 | type_anchors.json |

### 검증
```
[ ] 8앵커 3D 공간 배포 확인
[ ] 테스트 피처 → 직관적 앵커 매칭
[ ] 극성 반전 잔재 제로
```

---

# Phase 3: formatter + llm + action_spec 교체

> 리포트 레이어를 3축에 맞게 재작성.

| # | 작업 | 파일 |
|---|------|------|
| 3-1 | AXIS_LABELS 삭제 → coordinate.py import | report_formatter.py |
| 3-2 | get_position_label() 3축 재작성 | report_formatter.py |
| 3-3 | direction_items 3축 생성 | report_formatter.py |
| 3-4 | gap_summary 3축 기반 | report_formatter.py |
| 3-5 | GAP_RECOMMENDATION_TEMPLATES 3축 재작성 | report_formatter.py |
| 3-6 | FACE_INTERPRET_SYSTEM 3축 프롬프트 | llm.py |
| 3-7 | 인터뷰 프롬프트 3축 전환 | llm.py |
| 3-8 | action_spec 상세 설계서 작성 | 별도 문서 |
| 3-9 | action_spec 3축 delta_contribution | action_spec.py |
| 3-10 | zone별 축 기여 매핑 3축 기준 | action_spec.py |

### 검증
```
[ ] 리포트 전체 생성 정상
[ ] 3축 디테일 카드 정상
[ ] gap_summary 라벨 정확
[ ] LLM 해설에 4축 잔재 없음
[ ] action_plan zone별 방향 태그 3축 기반
```

---

# Phase 4: 프론트엔드 교체

> 4축 하드코딩 전량 삭제. 백엔드 라벨만 사용.

| # | 작업 | 파일 |
|---|------|------|
| 4-1 | gap-scatter-plot.tsx 전면 재작성 | gap-scatter-plot.tsx |
| 4-2 | aesthetic_map 기반 고정 2D (Shape×Age, Volume=점크기) | gap-scatter-plot.tsx |
| 4-3 | 사분면: Soft Fresh / Sharp Fresh / Soft Mature / Sharp Mature | gap-scatter-plot.tsx |
| 4-4 | Volume 점 크기 + 텍스트 라벨 병행 | gap-scatter-plot.tsx |
| 4-5 | gap-analysis.tsx 3축 디테일 카드 | gap-analysis.tsx |
| 4-6 | AXIS_META, AXIS_END_LABELS, CONNECTIVE_MAP 삭제 | 프론트 전반 |
| 4-7 | Coordinates 타입 3축으로 변경 | 타입 정의 |

### 검증
```
[ ] 2D 맵 현재/추구 점 정상
[ ] 사분면 라벨 4개 정상
[ ] Volume 점 크기 시각 구분 가능
[ ] 3축 디테일 카드 정상
[ ] structure/impression/maturity/intensity 검색 0건
```

---

# Phase 5: 앵커 이미지 생성 + 역검증

> 8앵커 AI 이미지 → InsightFace 역검증 → 좌표 캘리브레이션.

| # | 작업 |
|---|------|
| 5-1 | 8앵커 프롬프트 작성 (16앵커 가이드 기반 축소) |
| 5-2 | DeeVid AI / Midjourney 생성 (앵커당 2~3장 후보) |
| 5-3 | InsightFace 역검증 — 12피처 추출 + 3축 좌표 계산 |
| 5-4 | 의도 좌표 근처 위치 확인, 이탈 시 프롬프트 조정 |
| 5-5 | type_anchors.json coords를 실측값으로 보정 |
| 5-6 | 프론트 앵커 이미지 교체 (/images/types/) |

### 검증
```
[ ] 8장 확보, 시리즈 통일감 확인
[ ] 특정 셀럽으로 식별 불가
[ ] 다른 유형과 나란히 놓았을 때 차이 직관적
[ ] coords 최종 보정 완료
```

---

# Phase 6: 레거시 삭제 + 최종 검증

> 4축 잔재 완전 제거. end-to-end 테스트.

### 코드베이스 검색 — 전부 0건이어야 함
```bash
grep -r "structure" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "impression" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "maturity" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "intensity" --include="*.py" --include="*.tsx" --include="*.json"
grep -r "axes_3d" --include="*.json"
grep -r "axis_roles" --include="*.json"
grep -r "AXIS_META" --include="*.tsx"
grep -r "AXIS_END_LABELS" --include="*.tsx"
grep -r "CONNECTIVE_MAP" --include="*.tsx"
```

### 통합 테스트
```
[ ] 신규 사진 업로드 → 전체 파이프라인 정상
[ ] 리포트 전체 렌더링 (8섹션 + 3축 디테일)
[ ] 8앵커 중 하나로 매칭
[ ] 3축 gap 정상
[ ] 2D 맵 정상
[ ] action plan 정상
[ ] 결제 플로우 정상
[ ] 기존 리포트 접근 시 재진단 유도 메시지
```

---

# Phase 7: 오버레이 파이프라인 통합

> overlay_renderer.py v0 (이미 완료) → 파이프라인 연결 → 리포트 삽입.

| # | 작업 | 상태 |
|---|------|------|
| 7-1 | face.py에 landmarks_2d_106 저장 추가 | 🔧 |
| 7-2 | main.py에서 리포트 생성 시 오버레이 자동 생성 | 📋 |
| 7-3 | report JSON에 overlay_image_url 포함 | 📋 |
| 7-4 | BeforeAfterOverlay.jsx 프론트 삽입 | 📋 |
| 7-5 | ACTION PLAN 섹션에 오버레이 이미지 연결 | 📋 |

### 검증
```
[ ] 리포트 생성 시 오버레이 이미지 자동 생성
[ ] Before/After 슬라이더 정상 작동
[ ] 오버레이가 자연스러운지 (v0 튜닝 결과 기반)
```

---

# Phase 8: 오버레이 고도화

> v0 → v0.5 → v1 순차 개선.

### v0.5: 추구미 반영 팔레트
```
현재: 모든 유저에게 같은 블러셔 색
변경: gap vector 방향별 컬러 팔레트 매핑

ASPIRATION_PALETTES = {
    "soft_fresh": {"blush": "#F4C2B0", "lip": "#D4907A"},
    "sharp_fresh": {"blush": "#D4899B", "lip": "#B85670"},
    "soft_mature": {"blush": "#C9A89A", "lip": "#A07060"},
    "sharp_mature": {"blush": "#B08898", "lip": "#8A4560"},
}
```

### v1: 풀 오버레이
- blend mode 분기 (highlight → screen, shading → multiply)
- yaw/roll fallback (정면이 아닌 각도 대응)
- brow tint 추가 (은율 피드백: "요즘 눈썹 염색이 유행")
- 컬러 스와치 UI (나연 피드백)

---

# Phase 9: 스킨톤 고도화

> 6타입 하드코딩 → 동적 추천 전환.

### 9-1. ROI 확장
- 양 볼 + 이마로 ROI 확장
- landmarks_2d_106 zone 매핑 구조 재사용
- 상위/하위 5% 픽셀 트리밍

### 9-2. 동적 컬러 추천
```
유저 피부 LAB → 용도별 색상 공식:
  립:    피부색 대비 + 채도 부스트
  블러셔: 피부색 유사 + 약간 따뜻하게
  베이스: 피부색 거의 동일 + 밝기 조정
  포인트: 보색 or 삼색조화 계열
```
- 6타입 하드코딩을 baseline으로, 동적 결과와 비교하며 튜닝
- why_recommended 필드 추가 (6타입 × 4색 = 24개 문장)

### 9-3. SKIN_TONE_THRESHOLDS 캘리브레이션
- Phase 0.5 calibration_results 반영
- 실 유저 50명+ 데이터 기반 threshold 재조정

### 9-4. 명도(L*) 축 추가 검토
- 조명 보정 파이프라인 도입 후 L* 기반 라이트/딥 분류
- 6타입 → 12타입 확장 가능성

---

# Phase 10: 콘텐츠 + UX 개선

> 유저 피드백 기반 리포트 품질 강화.

### 10-1. 설문지 수정
- "현재 고민" 필드 삭제
- placeholder 해요체 전환
- 최소 답변 기준 6→5, 4→3

### 10-2. 랜딩페이지 카피 리뉴얼
- 서연 인터뷰 반영: "효율적으로 끝내고 싶은 사람" 포지셔닝
- "봄웰" → 일반 용어 교체
- 사회적 증거 섹션 추가 (리뷰, before/after)

### 10-3. WHY THIS TYPE 고도화
- Phase 3에서 3 bullet deterministic fallback 적용 완료
- LLM 프롬프트 + 파싱으로 품질 향상
- 3 bullet 포맷 강제, bracket/placeholder 감지 시 fallback

### 10-4. 리포트 이후 실행 지원
- 제품 링크 연결 (서연 피드백: "실행 지원 갭")
- 단계별 가이드 (오늘/이번 주/이번 달)

---

# Phase 11: 데이터 파이프라인 + 피드백 루프

> 유저 데이터 축적 → 파라미터 보정 → 장기적 학습 기반.

### 11-1. 피드백 수집 구조
```
리포트 끝에:
- "유형 매칭이 맞다고 느꼈나요?" (Y/N)
- "추천 컬러가 어울렸나요?" (Y/N)
- "액션플랜을 따라해봤나요?" (Y/N → 만족도)
```

### 11-2. 실 유저 데이터 기반 재캘리브레이션
- 50명+ 축적 시 OBSERVED_RANGES 재보정 (한국 20대 여성 기준)
- 축 분포, 상관계수 재확인
- 앵커 coords 미세 조정

### 11-3. 가중치 학습 (장기)
- 유저 피드백("유형 맞아요/아니에요") 수집
- 가중치를 학습으로 최적화 (supervised)
- 정답 라벨 100건+ 필요

### 11-4. 추천 모델 (장기)
- "이 색 어울렸어요/안 어울렸어요" → 팔레트 추천 모델
- 유저 사진 + 만족도 → 액션플랜 추천 모델

---

# Phase 12: 확장

> 제품 범위 확대.

### 12-1. 남성 파이프라인 분기
- 뉴가 피드백: "남성 분기 필요"
- 앵커 8개 남성 버전 생성
- 피처 가중치 남성용 YAML config 분리
- 액션플랜 남성화 (메이크업 → 헤어/스킨케어 중심)

### 12-2. z축 트렌드 좌표 설계
- 셀럽 데이터 + 인스타 트렌드 분석
- 시간에 따라 변하는 "트렌드 좌표" 도입
- 유저 좌표와 트렌드 좌표 비교 → "지금 트렌드에 가까운 정도"

### 12-3. 3D 인터랙티브 시각화
- 3축이니까 3D 시각화 가능
- 회전 가능한 큐브 위에 유저 점 + 8앵커 표시
- WebGL / Three.js 기반

### 12-4. B2B 캐스팅/브랜드 매칭
- 좌표계 기반 "이 모델은 Sharp Fresh 유형" 분류
- 브랜드 이미지 → 좌표 매핑 → 모델-브랜드 적합도 점수
- 캐스팅 디렉터용 대시보드

### 12-5. 셀럽 좌표 맵
- 유명인 얼굴 사진 → 파이프라인 → 3축 좌표
- "나는 OO 근처에 있다" 기능
- 앵커 8개 + 셀럽 N명 → 미적 지도

---

# 타임라인 요약

| Phase | 작업 | 예상 | 의존성 |
|-------|------|------|--------|
| **0** | **런칭 핫픽스** | **4/10 전** | **없음** |
| 0.5 | 3축 캘리브레이션 | 0.5~1일 | v2 확정 |
| 1 | coordinate.py 3축 교체 | 1일 | Phase 0.5 |
| 2 | 앵커 + similarity 교체 | 1일 | Phase 1 |
| 3 | formatter + llm + action_spec | 1일 | Phase 1 |
| 4 | 프론트 교체 | 1일 | Phase 2, 3 |
| 5 | 앵커 이미지 + 역검증 | 2~3일 | Phase 2 (병렬 가능) |
| 6 | 레거시 삭제 + 최종 검증 | 0.5일 | 전체 |
| 7 | 오버레이 통합 | 1~2일 | Phase 6 |
| 8 | 오버레이 고도화 | 3~5일 | Phase 7 |
| 9 | 스킨톤 고도화 | 3~5일 | Phase 6 |
| 10 | 콘텐츠 + UX | 2~3일 | Phase 6 |
| 11 | 데이터 + 피드백 루프 | 지속 | 유저 축적 |
| 12 | 확장 (남성, 트렌드, 3D, B2B) | 장기 | 전체 |

```
4/10 ──→ Phase 0 (런칭)
         │
    1주 ──→ Phase 0.5~6 (3축 전환, ~7일)
         │
    2주 ──→ Phase 7~8 (오버레이)
         ├→ Phase 9 (스킨톤) ← 병렬 가능
         ├→ Phase 10 (콘텐츠) ← 병렬 가능
         │
    1개월 ─→ Phase 11 (피드백 루프 시작)
         │
    3개월 ─→ Phase 12 (확장)
```

---

# 문서 의존성

| 문서 | 역할 | 해당 Phase |
|------|------|-----------|
| SIGAK_V4_1_FINAL_SPEC.md | v4 UI 수정 스펙 (완료) | Phase 0 |
| SIGAK_3AXIS_MIGRATION_SPEC.md | 3축 전환 상세 스펙 | Phase 0.5~6 |
| SIGAK_16_ANCHOR_TYPES.md | 16→8 앵커 유형 정의 | Phase 2, 5 |
| SIGAK_OVERLAY_RENDERER_v0.2.md | 오버레이 렌더러 설계 | Phase 7~8 |
| (미작성) 3축 action_spec 상세 설계서 | Phase 3 착수 전 작성 | Phase 3 |
| (미작성) 앵커 AI 이미지 프롬프트 v2 | Phase 5 착수 전 작성 | Phase 5 |

---

*Generated: 2026-04-09*
*이 문서는 SIGAK 프로젝트의 전체 기술 로드맵이다.*
*Phase 0은 즉시, Phase 0.5~6은 다음 스프린트, Phase 7~12는 순차 진행.*