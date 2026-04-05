# SPEC-COORD-003: 구현 계획

## 전략

데이터 퍼스트 접근법 채택. 셀럽 사진 수집 -> CLIP 임베딩 -> UMAP 시각화 -> 축 방향 발견 순서.
파운더 태스크(사진 수집)와 개발자 태스크(파이프라인 구축)를 분리하여 병렬 진행.
좌표 정밀도보다 리포트 내러티브 품질이 만족도의 70%를 결정한다는 핵심 인사이트 반영.

---

## 역할 분담

### 파운더 태스크 (사진 큐레이션)

| 태스크 | 설명 | 기준 | 의존성 |
|--------|------|------|--------|
| F1 | 셀럽 리스트 20-30명 확정 | 3축 극점별 균형 배분 | 없음 |
| F2 | 셀럽당 캐주얼 사진 수집 | 공항샷/브이로그/일상만, 화보 배제 | F1 |
| F3 | 사진을 `sigak/data/anchors/{name}/` 폴더에 정리 | 폴더당 최소 3장 | F2 |
| F4 | 축 극점 가이드라인 태깅 | 각 셀럽이 어느 극점에 가까운지 초기 판단 | F1 |
| F5 | UMAP 시각화 결과 검토 + 축 방향 최종 확정 | 개발자와 함께 리뷰 | P0 완료 후 |

---

## P0: 데이터 수집 + CLIP 임베딩 + 축 발견

**목적**: CLIP 임베딩 공간에서 미감 축의 자연적 방향을 발견한다.

### T1: CLIP 파이프라인 모듈 [R3]

파일: `sigak/pipeline/clip.py`

- `CLIPEmbedder` 클래스: open-clip-torch + clip-vit-large-patch14
- 모델 싱글턴 로딩 (GPU 메모리 관리)
- `extract()`: 얼굴 크롭 -> 768d 임베딩
- `mock_embedding()`: 768d 의사 임베딩 폴백
- 단위 테스트: 출력 차원 768, L2 정규화, 결정론적 mock

### T2: config.py 업데이트 [R3]

파일: `sigak/config.py`

- `clip_model`: "ViT-B-32" -> "ViT-L-14"
- `embedding_dim`: 512 -> 768
- `coordinate_axes`: 4 -> 3

### T3: 앵커 임베딩 + 시각화 스크립트 [R4, R5]

파일: `sigak/scripts/embed_anchors.py`

- `sigak/data/anchors/` 디렉토리 순회
- 각 셀럽 사진 -> CLIP 임베딩 추출
- 임베딩 `.npy` 파일 저장
- UMAP 2D + t-SNE 2D 시각화 PNG 저장
- 파운더와 클러스터 방향 관찰 -> 3축 방향 확정

### T4: 앵커 이미지 디렉토리 구조 [R5]

디렉토리: `sigak/data/anchors/` + README.md (수집 가이드라인)

**P0 완료 조건**: UMAP/t-SNE 시각화에서 3축 방향 벡터 확정. 파운더 승인.
**의존성**: F1-F4 완료 필수 (파운더 사진 수집).

---

## P1: 축 방향 벡터 + 유저 셀피 프로젝션 파이프라인

**목적**: 확정된 축 방향 벡터로 유저 셀피를 3축 좌표계에 매핑.

### T5: coordinate.py 완전 재작성 [R1, R2]

파일: `sigak/pipeline/coordinate.py`

- 4축 AXES -> 3축 (impression, tone, mood) 교체
- `structural_to_axis_scores()` 완전 제거
- `AnchorProjector` 768d 대응, 3축 프로젝션
- `compute_coordinates()`: CLIP 임베딩만 입력
- `to_user_scale()`: `(score + 1) / 2`
- `compute_gap()`: 3축 갭 분석

### T6: DB 스키마 마이그레이션 [R6]

파일: `sigak/db.py`, Alembic 마이그레이션

- Vector(512) -> Vector(768)
- 좌표 컬럼 4축 -> 3축
- Alembic revision 파일 생성

### T7: main.py API 업데이트 [R1]

- `GET /api/v1/axes`: 3축 정의 응답
- 분석 파이프라인: CLIP -> 좌표 경로 변경
- 리포트 JSON: 3축 좌표 + 갭 벡터

**P1 완료 조건**: 유저 셀피 -> 3축 좌표 e2e 동작.
**의존성**: P0 완료.

---

## P2: LLM 리포트 프롬프트 리디자인 (P1과 병렬 가능)

**목적**: 리포트 내러티브 품질 극대화. 만족도의 70% 결정.

### T8: LLM 프롬프트 3축 전환 [R11]

파일: `sigak/pipeline/llm.py`

- 인터뷰 해석: 4축 -> 3축 좌표 산출
- 셀럽 좌표 레퍼런스: 3축 기준
- 리포트 프롬프트 재설계: 수치 나열 금지, 방향성 스토리 필수

### T9: 구조적 특징 내러티브 파이프라인 [R2, R11]

- `face.py` 메트릭을 한국어 설명으로 변환
- LLM이 내러티브에 자연스럽게 통합

**P2 완료 조건**: 3축 리포트 생성, 내러티브 품질 검토 통과.
**의존성**: R1 축 정의 확정 (P0). P1과 병렬 가능.

---

## P3: 리포트 UI 리디자인 + 피드백 루프 (P1 이후)

### T10: 삼각형 레이더 차트 [R7]

파일: `sigak-web/components/report/sections/coordinate-map.tsx`

- 4축 프로그레스 바 -> 3축 정삼각형 레이더 차트 (SVG)
- 현재: filled polygon, 추구미: dashed polygon
- 축 라벨: 꼭짓점 한국어, 스케일 동심 삼각형
- 반응형: 모바일 최소 240px

### T11: 셀럽 레퍼런스 사진 포함 [R8]

파일: `sigak-web/components/report/sections/celeb-reference.tsx`

- 셀럽 사진 + Next.js Image
- 이니셜 아바타 폴백
- 블러 호환

### T12: 컬러 팔레트 스와치 [R9]

파일: `sigak-web/components/ui/color-swatch.tsx`

- 컬러명 + hex + 원형 스와치
- 카테고리별 그룹핑

### T13: TypeScript 타입 + Mock 업데이트 [R1, R7]

파일: `report.ts`, `mock-report.ts`

- 3축 타입, celeb_photo_url 추가, mock 데이터 업데이트

### T14: 얼굴 구조 오버레이 [R10]

파일: `sigak/pipeline/overlay.py`

- OpenCV 서버사이드 랜드마크 오버레이
- PNG -> S3 -> `<img>` 태그

### T15: 50인 피드백 + 축 캘리브레이션

- 50명 피드백, 상관관계 분석, 축 미세 조정

**P3 완료 조건**: UI 전체 e2e 동작. 빌드/타입/린트 에러 0.

---

## 아키텍처 변경 개요

```
AS-IS:
  사진 -> face.py (구조 메트릭)
       -> mock_clip (512d)
       -> coordinate.py (structural_to_axis_scores + AnchorProjector 4축)
       -> llm.py (4축 프롬프트)
       -> 리포트 (4축 프로그레스 바)

TO-BE:
  사진 -> face.py (구조 메트릭 -> 내러티브용만)
       -> clip.py (768d 실제 임베딩)
       -> coordinate.py (AnchorProjector 3축, CLIP-only)
       -> llm.py (3축 + 내러티브 강화)
       -> 리포트 (삼각형 차트 + 셀럽 사진 + 컬러 스와치)
```

---

## 위험 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| 파운더 사진 수집 지연 | P0 블로킹 | T1-T2 먼저 진행, F1-F4 마감 설정 |
| CLIP에서 3축 미관찰 | 축 정의 실패 | PCA 변경, 축 수 재검토 |
| 768d GPU 메모리 부족 | 추론 불가 | float16, CPU 폴백 |
| 캐주얼 사진 품질 편차 | 임베딩 노이즈 | 셀럽당 3장+, 이상치 필터링 |
| 내러티브 품질 저하 | 만족도 하락 | P2 병렬 진행, 프롬프트 A/B |
| DB 마이그레이션 실패 | 서비스 중단 | WoZ: drop+recreate, 백업 |

---

## 범위 외

- 토스페이먼츠 PG 자동 결제 / 실시간 CLIP 최적화 / 다중 사진 앙상블
- CLIP fine-tuning / CI/CD / 모바일 카메라 최적화 / A/B 테스트 인프라

---

## Traceability

| 요구사항 | 태스크 | 마일스톤 |
|--|--|--|
| R1 | T5 | P1 |
| R2 | T5 | P1 |
| R3 | T1, T2 | P0 |
| R4 | T3 | P0 |
| R5 | T4 | P0 |
| R6 | T6 | P1 |
| R7 | T10 | P3 |
| R8 | T11 | P3 |
| R9 | T12 | P3 |
| R10 | T14 | P3 |
| R11 | T8, T9 | P2 |
| R12 | T5 | P1 |
