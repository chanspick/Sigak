---
id: SPEC-COORD-003
version: "1.0.0"
status: "planned"
created: "2026-04-05"
updated: "2026-04-05"
author: ""
priority: "high"
lifecycle: "spec-anchored"
---

# SPEC-COORD-003: 미감 좌표계 리디자인 (4축 -> 3축 + CLIP 전환)

## HISTORY

- 2026-04-05: 초안 생성 (파운더 논의 기반, 데이터 퍼스트 접근법 채택)

---

## Environment

### 현재 상태

- `sigak/pipeline/coordinate.py`: 4축 시스템 (Structure, Impression, Maturity, Intensity)
  - `structural_to_axis_scores()`: 매직 넘버 기반 구조 점수 변환
  - `AnchorProjector`: 512d CLIP 앵커 프로젝션
  - `compute_coordinates()`: 구조 가중치 + CLIP 가중치 혼합
  - `mock_clip_embedding()`: SHA256 해시 기반 512d 의사 임베딩
- `sigak/config.py`: `clip_model="ViT-B-32"`, `embedding_dim=512`, `coordinate_axes=4`, `use_mock_clip=True`
- `sigak/db.py`: `Vector(512)` 컬럼 (face_analyses, celeb_anchors)
- `sigak/pipeline/face.py`: MediaPipe 468점 + 11개 구조적 메트릭 (유지)
- `sigak/pipeline/llm.py`: 4축 셀럽 좌표 레퍼런스 + 리포트 생성 프롬프트
- `sigak-web/components/report/sections/coordinate-map.tsx`: 4축 프로그레스 바 UI
- `sigak-web/components/report/sections/celeb-reference.tsx`: 텍스트 기반 셀럽 유사도
- `sigak-web/lib/types/report.ts`: CoordinateMapContent

### 목표 상태

- 3축 미감 좌표계: 인상(Impression), 톤(Tone), 무드(Mood)
- CLIP-only 좌표 산출 (구조 점수 -> 축 변환 로직 제거)
- clip-vit-large-patch14 (768d) 모델
- 데이터 발견형 축 방향 벡터 (UMAP/t-SNE 시각화 기반)
- 삼각형 레이더 차트 UI
- 셀럽 매칭에 실제 사진 포함
- 컬러 팔레트 스와치 컴포넌트
- 얼굴 구조 오버레이 이미지 (서버사이드 OpenCV 렌더링)

### 기술 환경

- GPU: RTX 4070 12GB (CLIP 추론 충분)
- 백엔드: FastAPI, SQLAlchemy 2.0, PostgreSQL 16 + pgvector
- 프론트엔드: Next.js 16, React 19, TypeScript 5.9+, Tailwind CSS v4
- CLIP: open-clip-torch + clip-vit-large-patch14 (768d)
- 시각화: matplotlib + umap-learn (데이터 탐색 단계)
- 오버레이 렌더링: OpenCV (서버사이드)

### 핵심 제약

- **데이터 의존성**: 파운더가 셀럽 사진 20-30장을 직접 큐레이션해야 P0 진행 가능
- **도메인 갭 최소화**: 캐주얼 사진(공항샷, 브이로그)만 사용, 화보/에디토리얼 배제
- **DB 마이그레이션**: Vector(512) -> Vector(768) 변경 시 기존 데이터 무효화

---

## Assumptions

1. 파운더가 P0 시작 전에 20-30명 셀럽의 캐주얼 사진을 수집/제공할 수 있다
2. clip-vit-large-patch14 (768d)가 RTX 4070 12GB에서 원활하게 추론 가능하다
3. CLIP 임베딩 공간에서 미감 축이 자연스럽게 관찰 가능한 방향으로 존재한다
4. 3축으로 충분한 미감 표현력을 확보할 수 있다 (4축 대비 정보 손실 허용)
5. 현재 WoZ 단계이므로 실 유저 데이터 마이그레이션 불필요 (celeb_anchors만 재구축)
6. 셀럽 사진의 저작권은 서비스 내부 분석용으로 fair use 범위에 해당한다
7. 좌표 정밀도(0.6 vs 0.65)보다 리포트 내러티브 품질이 사용자 만족도에 더 중요하다
8. 얼굴 구조 오버레이는 S3 업로드 후 정적 이미지로 제공한다

---

## Requirements

### R1: 3축 미감 좌표계 정의 [Ubiquitous]

시스템은 항상 3개의 미감 축으로 사용자 좌표를 산출해야 한다.

| 축 | 내부명 | 0극 (Negative) | 1극 (Positive) | CV 입력 |
|----|--------|---------------|----------------|---------|
| 인상 | impression | 소프트(Soft) | 샤프(Sharp) | 턱 각도, 광대뼈, 눈꼬리 각도 |
| 톤 | tone | 웜/내추럴(Warm/Natural) | 쿨/글램(Cool/Glam) | 피부 HSV, CLIP 임베딩 |
| 무드 | mood | 프레시/큐트(Fresh/Cute) | 성숙/시크(Mature/Chic) | 얼굴 비율, CLIP 임베딩 |

- R1.1: 사용자 대면 스케일은 0~1 (음수 없음)
- R1.2: 내부 연산 스케일은 -1~+1
- R1.3: 변환 공식: `user_score = (internal_score + 1) / 2`
- R1.4: 기존 4축(structure, impression, maturity, intensity) 정의 완전 대체

### R2: CLIP-only 좌표 산출 [Ubiquitous]

시스템은 항상 좌표를 CLIP 임베딩 프로젝션만으로 산출해야 한다.

- R2.1: `structural_to_axis_scores()` 함수를 좌표 산출에서 완전 제거
- R2.2: `face.py`의 구조적 특징은 리포트 내러티브용으로만 사용
- R2.3: 좌표 산출에 매직 넘버 없음
- R2.4: `AnchorProjector`가 3축 방향 벡터로 프로젝션 수행

### R3: CLIP 모델 전환 [Event-Driven]

WHEN 시스템이 CLIP 추론을 수행할 때 THEN clip-vit-large-patch14 (768d) 모델을 사용해야 한다.

- R3.1: `config.py`: `clip_model="ViT-L-14"`, `embedding_dim=768`
- R3.2: `sigak/pipeline/clip.py` 신규 모듈
- R3.3: 얼굴 영역 크롭 후 CLIP 입력
- R3.4: GPU 메모리 관리: 모델 싱글턴 로딩
- R3.5: mock_clip 폴백 유지 (768d 의사 임베딩)

### R4: 데이터 발견형 축 구축 [Event-Driven]

WHEN 20-30명 셀럽 임베딩이 수집되면 THEN UMAP/t-SNE 시각화를 통해 축 방향을 발견해야 한다.

- R4.1: `sigak/scripts/embed_anchors.py` 스크립트 생성
- R4.2: 셀럽 사진 -> CLIP 임베딩 추출 -> 768d 벡터 저장
- R4.3: UMAP 2D 시각화 생성
- R4.4: t-SNE 2D 시각화 생성
- R4.5: 클러스터/방향 관찰 후 축 방향 벡터 수동 결정
- R4.6: 결정된 방향 벡터를 앵커 데이터로 저장

### R5: 앵커 이미지 전략 [Ubiquitous]

시스템은 항상 캐주얼 사진만을 앵커 이미지로 사용해야 한다.

- R5.1: 공항샷, 브이로그 캡처, 일상 사진만 허용
- R5.2: 프로페셔널 화보/에디토리얼 사진 배제
- R5.3: 축 극점당 최소 20장 앵커 이미지
- R5.4: 앵커 이미지 디렉토리: `sigak/data/anchors/{celeb_name}/`

### R6: DB 스키마 변경 [Event-Driven]

WHEN CLIP 모델이 768d로 전환되면 THEN DB 벡터 차원을 업데이트해야 한다.

- R6.1: `face_analyses.clip_embedding`: Vector(512) -> Vector(768)
- R6.2: `celeb_anchors.clip_embedding`: Vector(512) -> Vector(768)
- R6.3: `celeb_anchors` 좌표 컬럼: 4축 -> 3축
- R6.4: `face_analyses` 좌표 컬럼: 4축 -> 3축
- R6.5: `reports` JSON 필드: 3축 형태
- R6.6: Alembic 마이그레이션 스크립트 생성

### R7: 삼각형 레이더 차트 UI [Event-Driven]

WHEN 리포트 좌표계 섹션을 렌더링할 때 THEN 삼각형 레이더 차트를 표시해야 한다.

- R7.1: 3축 -> 정삼각형 꼭짓점 매핑
- R7.2: 현재 좌표 = 채워진(filled) 삼각형
- R7.3: 추구미 좌표 = 대시(dashed) 삼각형 오버레이
- R7.4: 큰 삼각형 = 샤프/쿨/시크, 작은 삼각형 = 소프트/웜/프레시
- R7.5: 기존 4축 프로그레스 바 UI 완전 대체
- R7.6: 반응형 대응 (모바일 최소 240px)

### R8: 셀럽 매칭 사진 포함 [Event-Driven]

WHEN 셀럽 레퍼런스 섹션 렌더링 THEN 셀럽 실제 사진을 함께 표시해야 한다.

- R8.1: 셀럽 사진 + 유사도 표시
- R8.2: `celeb_anchors.photo_url`에서 조회
- R8.3: 사진 없는 경우 이니셜 아바타 폴백
- R8.4: 블러 시 이름+유사도 선명, 사진+이유+팁 블러

### R9: 컬러 팔레트 스와치 [Event-Driven]

WHEN 리포트에 컬러 추천 표시 THEN 실제 컬러 스와치로 표시해야 한다.

- R9.1: `sigak-web/components/ui/color-swatch.tsx` 컴포넌트
- R9.2: 컬러명 + hex 코드 + 원형 스와치
- R9.3: 카테고리별 그룹핑

### R10: 얼굴 구조 오버레이 [Event-Driven]

WHEN 리포트 얼굴 구조 섹션 렌더링 THEN MediaPipe 랜드마크 오버레이 이미지를 표시해야 한다.

- R10.1: `sigak/pipeline/overlay.py`: OpenCV 기반 반투명 오버레이
- R10.2: 서버사이드 렌더링
- R10.3: S3 업로드
- R10.4: 프론트엔드 `<img>` 태그로 표시

### R11: LLM 프롬프트 리디자인 [Event-Driven]

WHEN 리포트 생성 THEN 3축 기반 프롬프트와 내러티브 중심 출력을 사용해야 한다.

- R11.1: 4축 셀럽 좌표 -> 3축 업데이트
- R11.2: 인터뷰 해석 프롬프트: 3축 추구미 좌표 산출
- R11.3: 내러티브 품질 강화 (수치 나열 금지, 방향성 스토리 필수)
- R11.4: 구조적 특징을 내러티브 소재로 전달

### R12: 비허용 행위 [Unwanted]

- R12.1: 좌표 산출에 `structural_to_axis_scores()` 사용 금지
- R12.2: 좌표 산출에 매직 넘버 가중치 사용 금지
- R12.3: 사용자에게 내부 스케일(-1~+1) 직접 노출 금지
- R12.4: 프로페셔널 화보 사진을 앵커로 사용 금지
- R12.5: 수동 GT 할당 후 데이터 맞추기 방식 금지

---

## Specifications

### S1: 신규/변경 파일 구조

백엔드:
- `sigak/pipeline/coordinate.py` - 완전 재작성 (3축, CLIP-only)
- `sigak/pipeline/clip.py` - 신규: CLIP 모델 + 임베딩 추출
- `sigak/pipeline/overlay.py` - 신규: MediaPipe 오버레이
- `sigak/pipeline/face.py` - 유지 (내러티브용)
- `sigak/pipeline/llm.py` - 수정: 3축 프롬프트
- `sigak/config.py` - 수정: CLIP 모델, 차원, 축 수
- `sigak/db.py` - 수정: Vector(768), 3축 컬럼
- `sigak/data/anchors/` - 신규: 셀럽 앵커 이미지
- `sigak/scripts/embed_anchors.py` - 신규: 시각화 스크립트

프론트엔드:
- `coordinate-map.tsx` - 재작성: 삼각형 레이더 차트
- `celeb-reference.tsx` - 수정: 사진 포함
- `color-swatch.tsx` - 신규: 컬러 스와치
- `lib/types/report.ts` - 수정: 3축 타입
- `lib/constants/mock-report.ts` - 수정: 3축 mock

### S2: 3축 좌표계 Python 데이터 구조

```python
@dataclass
class AxisDefinition:
    name: str
    name_kr: str
    negative_label: str
    positive_label: str
    negative_label_kr: str
    positive_label_kr: str

AXES = [
    AxisDefinition("impression", "인상", "soft", "sharp", "소프트", "샤프"),
    AxisDefinition("tone", "톤", "warm_natural", "cool_glam", "웜/내추럴", "쿨/글램"),
    AxisDefinition("mood", "무드", "fresh_cute", "mature_chic", "프레시/큐트", "성숙/시크"),
]
```

### S3: 3축 좌표계 TypeScript 타입

```typescript
interface CoordinateMapContent {
  axes: ["impression", "tone", "mood"];
  axisLabels: {
    impression: { negative: string; positive: string };
    tone: { negative: string; positive: string };
    mood: { negative: string; positive: string };
  };
  position: [number, number, number];
  target: [number, number, number];
}
```

---

## Traceability

| 요구사항 | 구현 파일 | 인수 조건 |
|--|--|--|
| R1 | coordinate.py | AC-1 |
| R2 | coordinate.py | AC-2 |
| R3 | clip.py, config.py | AC-3 |
| R4 | embed_anchors.py | AC-4 |
| R5 | data/anchors/ | AC-5 |
| R6 | db.py, alembic | AC-6 |
| R7 | coordinate-map.tsx | AC-7 |
| R8 | celeb-reference.tsx | AC-8 |
| R9 | color-swatch.tsx | AC-9 |
| R10 | overlay.py | AC-10 |
| R11 | llm.py | AC-11 |
| R12 | 전체 | AC-12 |
