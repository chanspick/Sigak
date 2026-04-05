# SPEC-COORD-003: 인수 조건

---

## AC-1: 3축 미감 좌표계 정의 [R1]

### Scenario 1: 축 정의 정확성
```gherkin
Given 좌표계 시스템이 초기화되면
When AXES 리스트를 조회할 때
Then 정확히 3개의 축이 정의되어 있다
  And 축 이름은 "impression", "tone", "mood" 이다
  And 각 축의 한국어 이름은 "인상", "톤", "무드" 이다
```

### Scenario 2: 사용자 스케일 변환
```gherkin
Given 내부 좌표가 {-1, 0, +1} 범위일 때
When to_user_scale()을 호출하면
Then 결과는 {0, 0.5, 1.0}으로 변환된다
  And 사용자 대면 스케일에 음수가 존재하지 않는다
```

### Scenario 3: 내부 스케일 범위
```gherkin
Given 임의의 CLIP 임베딩이 입력되면
When compute_coordinates()를 호출할 때
Then 각 축의 내부 좌표는 -1 이상 +1 이하이다
  And 결과에 "impression", "tone", "mood" 키만 존재한다
  And "structure", "intensity", "maturity" 키는 존재하지 않는다
```

---

## AC-2: CLIP-only 좌표 산출 [R2]

### Scenario 1: 구조 점수 미사용
```gherkin
Given coordinate.py의 compute_coordinates() 함수에서
When 좌표를 산출할 때
Then structural_to_axis_scores() 함수가 호출되지 않는다
  And 함수 시그니처에 clip_embedding만 입력으로 받는다
```

### Scenario 2: 매직 넘버 부재
```gherkin
Given coordinate.py 소스 코드에서
When 좌표 산출 로직을 검사할 때
Then structural_weight, clip_weight 같은 혼합 가중치가 없다
```

### Scenario 3: 구조적 특징의 역할
```gherkin
Given face.py에서 추출된 구조적 메트릭이 있을 때
When 분석 파이프라인이 실행되면
Then 구조적 메트릭은 LLM 리포트 내러티브에만 전달된다
  And coordinate.py에는 전달되지 않는다
```

---

## AC-3: CLIP 모델 전환 [R3]

### Scenario 1: 모델 설정
```gherkin
Given config.py의 Settings가 로드되면
When 기본 설정을 확인할 때
Then clip_model은 "ViT-L-14" 이다
  And embedding_dim은 768 이다
  And coordinate_axes는 3 이다
```

### Scenario 2: CLIP 임베딩 추출
```gherkin
Given CLIPEmbedder가 초기화되고
When 얼굴 이미지와 bbox를 입력하면
Then 768차원 numpy 배열이 반환된다
  And 배열의 L2 노름은 1.0 (오차 1e-5 이내) 이다
```

### Scenario 3: Mock 폴백
```gherkin
Given use_mock_clip=True 설정일 때
When mock_embedding()을 호출하면
Then 768차원 numpy 배열이 반환된다
  And 같은 이미지 바이트에 대해 동일한 결과 반환 (결정론적)
```

---

## AC-4: 데이터 발견형 축 구축 [R4]

### Scenario 1: 앵커 임베딩 스크립트
```gherkin
Given sigak/data/anchors/ 디렉토리에 셀럽 사진이 있을 때
When embed_anchors 스크립트를 실행하면
Then 각 셀럽별 768d 임베딩이 .npy 파일로 저장된다
  And UMAP 2D 시각화 PNG가 생성된다
  And t-SNE 2D 시각화 PNG가 생성된다
```

---

## AC-5: 앵커 이미지 전략 [R5]

### Scenario 1: 이미지 품질 기준
```gherkin
Given sigak/data/anchors/ 디렉토리의 이미지를 검사할 때
When 이미지를 확인하면
Then 프로페셔널 화보/에디토리얼 이미지가 포함되지 않는다
  And 각 셀럽 폴더에 최소 3장 이상의 이미지가 있다
```

---

## AC-6: DB 스키마 변경 [R6]

### Scenario 1: 벡터 차원 변경
```gherkin
Given Alembic 마이그레이션을 실행하면
When face_analyses, celeb_anchors 테이블을 확인할 때
Then clip_embedding 컬럼은 Vector(768) 타입이다
```

### Scenario 2: 좌표 컬럼 3축
```gherkin
Given 마이그레이션이 완료되면
When celeb_anchors 테이블을 확인할 때
Then coord_impression, coord_tone, coord_mood 컬럼이 존재한다
  And coord_structure, coord_intensity 컬럼은 존재하지 않는다
```

---

## AC-7: 삼각형 레이더 차트 UI [R7]

### Scenario 1: 삼각형 렌더링
```gherkin
Given 3축 좌표 데이터가 전달되면
When coordinate-map.tsx가 렌더링될 때
Then 정삼각형 형태의 레이더 차트가 표시된다
  And 각 꼭짓점에 "인상", "톤", "무드" 라벨이 표시된다
  And 현재 좌표는 filled 삼각형으로 표시된다
  And 추구미 좌표는 dashed 삼각형으로 오버레이된다
```

### Scenario 2: 직관적 크기
```gherkin
Given 모든 축이 1.0인 좌표가 입력되면
Then 삼각형이 최대 크기로 표시된다

Given 모든 축이 0.0인 좌표가 입력되면
Then 삼각형이 중심점으로 수렴한다
```

### Scenario 3: 블러 호환
```gherkin
Given locked=true일 때
Then 축 이름 라벨은 선명, 삼각형 차트와 수치는 블러 처리
```

---

## AC-8: 셀럽 매칭 사진 포함 [R8]

### Scenario 1: 사진 표시
```gherkin
Given celeb_photo_url이 제공된 데이터가 있을 때
When celeb-reference.tsx가 렌더링되면
Then 셀럽 사진이 이름과 함께 표시된다
```

### Scenario 2: 사진 없는 경우
```gherkin
Given celeb_photo_url이 null일 때
Then 이니셜 기반 아바타가 폴백으로 표시된다
```

---

## AC-9: 컬러 팔레트 스와치 [R9]

### Scenario 1: 스와치 렌더링
```gherkin
Given 컬러 데이터 {name, hex, category}가 있을 때
When color-swatch.tsx가 렌더링되면
Then hex 색상의 원형 스와치 + 컬러명이 표시된다
  And 카테고리별로 그룹핑된다
```

---

## AC-10: 얼굴 구조 오버레이 [R10]

### Scenario 1: 오버레이 생성
```gherkin
Given 유저 사진과 468점 랜드마크가 있을 때
When overlay.py의 render_overlay()를 호출하면
Then 반투명 랜드마크 오버레이된 PNG가 생성된다
  And S3 업로드 후 <img> 태그로 표시 가능하다
```

---

## AC-11: LLM 프롬프트 리디자인 [R11]

### Scenario 1: 3축 인터뷰 해석
```gherkin
Given 유저 인터뷰 응답이 있을 때
When LLM 해석을 실행하면
Then 3축 (impression, tone, mood) 추구미 좌표가 반환된다
  And 4축 좌표는 반환되지 않는다
```

### Scenario 2: 내러티브 품질
```gherkin
Given 리포트 생성이 실행되면
When 리포트 텍스트를 검사할 때
Then 단순 수치 나열이 없다
  And 방향성 스토리가 포함되어 있다
  And 구조적 특징 설명이 자연스럽게 통합되어 있다
```

---

## AC-12: 비허용 행위 검증 [R12]

### Scenario 1: structural_to_axis_scores 미사용
```gherkin
Given coordinate.py에서
When "structural_to_axis_scores" 를 검색하면
Then 함수 정의와 호출이 존재하지 않는다
```

### Scenario 2: 사용자 대면 음수 좌표 없음
```gherkin
Given 리포트 API 응답의 position/target 값을 검사할 때
Then 모든 값이 0 이상 1 이하이다
```

---

## 빌드 품질 게이트

```gherkin
Given 모든 코드 변경이 완료되면
Then pnpm build / tsc --noEmit / ESLint / pytest / ruff 전체 통과
  And 4축 관련 좌표 타입 참조가 없다
```

---

## 마일스톤별 완료 정의

### P0 완료 기준
- [ ] CLIPEmbedder 768d 임베딩 추출 동작
- [ ] config.py ViT-L-14, 768d, 3축 설정
- [ ] embed_anchors.py 스크립트 동작
- [ ] UMAP/t-SNE 시각화에서 3축 방향 확인
- [ ] 파운더와 축 방향 벡터 최종 확정

### P1 완료 기준
- [ ] coordinate.py 3축 CLIP-only 재작성
- [ ] structural_to_axis_scores() 완전 제거
- [ ] DB 마이그레이션 (Vector(768), 3축 컬럼)
- [ ] 유저 셀피 -> 3축 좌표 e2e 동작

### P2 완료 기준
- [ ] LLM 프롬프트 3축 전환
- [ ] 내러티브 품질 검토 통과

### P3 완료 기준
- [ ] 삼각형 레이더 차트 + 블러 호환
- [ ] 셀럽 사진 + 폴백
- [ ] 컬러 스와치
- [ ] 얼굴 오버레이
- [ ] 빌드/타입/린트 에러 0

---

## Traceability

| 인수 조건 | 요구사항 | 태스크 | 마일스톤 |
|--|--|--|--|
| AC-1 | R1 | T5 | P1 |
| AC-2 | R2 | T5 | P1 |
| AC-3 | R3 | T1, T2 | P0 |
| AC-4 | R4 | T3 | P0 |
| AC-5 | R5 | T4 | P0 |
| AC-6 | R6 | T6 | P1 |
| AC-7 | R7 | T10 | P3 |
| AC-8 | R8 | T11 | P3 |
| AC-9 | R9 | T12 | P3 |
| AC-10 | R10 | T14 | P3 |
| AC-11 | R11 | T8, T9 | P2 |
| AC-12 | R12 | 전체 | P1+ |
