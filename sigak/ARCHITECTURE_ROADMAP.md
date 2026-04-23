# SIGAK 모델 아키텍처 로드맵

## 현재 (v0.1 — WoZ 파일럿)

유저 사진 → [InsightFace] → 106 랜드마크 → 17개 구조적 특징
         → [CLIP ViT-L-14] → 768d 임베딩 → 셀럽 분위기 유사도
         → [coordinate.py] → 4축 좌표 (구조특징 + CLIP 가중합)

### 모델 구성

| 모델 | 역할 | 입력 | 출력 | VRAM |
|------|------|------|------|------|
| InsightFace buffalo_l | 얼굴 검출 + 106 랜드마크 | BGR 이미지 | bbox, landmarks, embedding | ~2GB |
| MediaPipe FaceMesh | 폴백 — 468 3D 랜드마크 | RGB 이미지 | landmarks | CPU only |
| CLIP ViT-L-14 | 미적 임베딩 (분위기/스타일) | 크롭 얼굴 | 768d 벡터 | ~2GB |
| Claude API | 인터뷰 해석 + 리포트 생성 | 구조화 텍스트 | JSON | API |

### 제한사항

- CLIP은 헤어/메이크업/옷 포함한 전체 분위기를 잡아서, 순수 얼굴 구조 유사도가 부정확
- coordinate.py의 축 가중치가 수동 설정 (데이터 기반 캘리브레이션 전)
- 앵커 15명의 임베딩이 아직 mock 상태

---

## v0.2 (파일럿 50명 후)

### 추가: AdaFace 512d 얼굴 임베딩

- 목적: CLIP이 잡지 못하는 "얼굴 구조 유사도" 보완
- CLIP = 전체 분위기(헤어, 메이크업, 옷 포함), AdaFace = 순수 얼굴 구조
- 유사도 = CLIP × 0.4 + AdaFace × 0.6 (얼굴 가중치 높게)
- 설치: pip install adaface-pytorch
- 모델: ir_101 pretrained (ResNet-100, 512d output)
- VRAM: 추론 ~2GB, LoRA 학습 ~6GB

### 추가: DINOv2 + 커스텀 헤드 (미감 축 직접 예측)

- 목적: 4축 좌표를 수동 계산이 아닌 학습 모델로 직접 예측
- 현재는 coordinate.py가 구조특징×가중치+CLIP×가중치로 계산 → 가중치가 수동
- DINOv2 ViT-B/16의 [CLS] 768d → Linear(256) → ReLU → Linear(4) → Tanh
- 학습 데이터: 앵커 45장(수동라벨) + 파일럿 50명(LLM pseudo-label)
- LoRA rank=8, lr=1e-4, epochs=50, batch_size=8
- VRAM: 학습 ~6-8GB (4070 Ti Super 16GB 내)
- 이 모델이 성숙하면 coordinate.py의 수동 가중치 계산을 대체

---

## v1.0 (유저 500명+)

### Taste Graph 자동 업데이트

- 유저 좌표 데이터 축적 → DINOv2 주기적 재학습
- 클러스터 자동 발견 → 라벨 자동 갱신
- community_score 크롤러 → 인기도 실시간 반영

### 파이프라인 자동화

- 유저 사진 업로드 → 전체 분석 → 리포트 → 결제 → 발송 완전 자동화
- 스태프 개입 없이 5분 내 리포트 생성
- Toss Payments 연동으로 수동 결제 확인 제거

---

## 하드웨어 요구사항

| 단계 | GPU | VRAM 사용 |
|------|-----|----------|
| v0.1 추론 | 4070 Ti Super | ~6GB (InsightFace + CLIP) |
| v0.2 추론 | 4070 Ti Super | ~8GB (+ AdaFace) |
| v0.2 학습 | 4070 Ti Super | ~12GB (DINOv2 LoRA) |
| v1.0 학습 | 4070 Ti Super | ~14GB (DINOv2 full) |
