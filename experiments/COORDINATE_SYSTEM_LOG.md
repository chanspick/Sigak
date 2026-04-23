# SIGAK 좌표계 실험 로그

> 기간: 2026-04-06 ~ 04-07
> 상태: **중단 — 제품 우선, 좌표계는 후행**
> 재개 시 시작점: "Phase 6: LDA 반지도학습" (이 문서 하단)

---

## 실험 배경

SIGAK은 유저 얼굴을 좌표 공간에 매핑하여 "포지션 + 방향"을 제시하는 서비스.
원래 가설: 3축 (structure sharp↔soft / impression warm↔cool / maturity fresh↔mature)
이 3축이 실제 데이터에서 존재하는지, 어떻게 산출하는지를 검증하는 실험 시리즈.

---

## Phase 1: CLIP 클러스터링 → 구조적 특징 전환

### 문제 제기
CLIP ViT-L-14 768d 임베딩으로 셀럽 클러스터링 시 "한국 여성 셀카" 카테고리가 같아서 전원 한 통에 뭉침. 수지↔화사 0.705는 얼굴 구조가 아니라 "사진 분위기" 유사도.

### 실행
- `celeb_features_cache.json`의 13개 구조적 수치 특징 사용
- StandardScaler 정규화 → K-Means k=4
- CLIP 임베딩 코드 주석 처리, structural 모드 기본값

### 결과
- 4개 클러스터 생성 (쿨갓데스 7명, 아이스프린세스 3명, 웜내추럴 3명, 엘레강트클래식 2명)
- PCA loadings: PC1(34.5%) = eye_tilt + philtrum_ratio, PC2(26.4%) = symmetry + eye_width

### 파일 변경
- `sigak/pipeline/cluster.py` — `mode="structural"` 추가, CLIP 주석 처리
- `sigak/pipeline/face.py` — `skin_warmth_score` 필드 추가

---

## Phase 2: 퍼스널컬러 상대 분류

### 문제 제기
`skin_tone` 절대 분류(LAB a* 임계값)로 16명 중 cool이 0명. 한국 셀럽 사진이 전반적으로 웜톤 보정됨.

### 실행
- `_assign_color_subtype`을 앵커 풀 상대 분류로 전환
- warmth_score P33/P67 → cool/neutral/warm, brightness median → dark/light

### 결과
- 4계절 전부 등장 (가을뉴트럴 4, 봄웜 3, 겨울쿨 3, 여름쿨 2, 봄뉴트럴 2, 가을웜 1)
- 하지만 상식과 불일치 다수 (윈터→봄웜 등)

### 판단
- 퍼스널컬러 코드는 유지하되 리포트 노출 보류
- 통제된 촬영 조건 없이는 신뢰도 부족
- skin_warmth_score raw 값을 Claude 프롬프트에 주입하여 AI가 서술하는 방식이 적합

---

## Phase 3: AI 생성 이미지 대표성 검증

### 배경
셀럽 초상권 법적 리스크 → DeeVid AI로 8개 유형 대표 얼굴 생성 (3축 극점 조합)

### 실행
- 8타입 × 3장 = 24장 + 3-1 변형 3장
- InsightFace 136d 랜드마크 추출 → `structural_to_axis_scores()` → 의도 좌표 vs 실측 좌표

### 결과
- **3/9 타입 얼굴 감지 실패** (Type 3, 3-1, 8 — 미소+앞머리)
- **의도 vs 실측 통과율: 33%** (18 체크 중 6개만 부호 일치)
- structure 축 전멸 — AI 이미지가 전체적으로 V라인으로 수렴
- impression(쿨/웜) 구분 불가 — 구조적 피처만으로 인상 축 미작동

### 확정
> **AI 생성 이미지로는 좌표축 앵커를 세울 수 없다**

---

## Phase 4: 136d 랜드마크 vs 17개 파생 피처

### 실행
- AI 이미지 감지 성공 6타입에 대해 17개 피처 vs 136d raw 랜드마크 PCA + 실루엣 스코어

### 결과
| 지표 | 17개 피처 | 136d 랜드마크 |
|------|----------|-------------|
| 실루엣 스코어 | -0.016 | +0.151 |
| centroid 최대 거리 | 7.0 | 27.9 |

### 확정
> **136d raw 랜드마크가 17개 hand-picked 피처보다 낫다**

하지만 +0.151도 충분하지 않음 → AI 이미지의 구조적 다양성 부족이 근본 원인

---

## Phase 5: SCUT-FBP5500 학술 데이터셋 축 검증

### 데이터셋
- SCUT-FBP5500: 아시안 여성 2000장, 86개 랜드마크, 60명 평가 매력도 점수(1~5)
- 500장 샘플링 → InsightFace 감지 295장 성공 (59%)
- 위치: `experiments/scut-fbp5500/`

### 실험 5-1: 136d 랜드마크 단독 UMAP
| 축 | 판정 | max |r| | 핵심 피처 |
|---|---|---|---|
| structure | WEAK | 0.237 | jaw_angle (UMAP1) |
| impression | CONFIRMED | 0.340 | symmetry (UMAP2) |
| maturity | WEAK | 0.287 | forehead (UMAP1) |

**발견: structure와 maturity가 같은 UMAP 차원에 로딩 — 분리 불가**
**발견: skin_warmth r≈0 — 피부톤은 랜드마크/CLIP과 완전 직교**

### 실험 5-2: 136d + 768d CLIP = 904d 결합
| 모드 | structure | maturity | impression | struct/mat split |
|------|-----------|----------|-----------|-----------------|
| 136d LM | 0.357 | 0.287 | 0.351 | NO |
| 768d CLIP | 0.550 | 0.409 | 0.433 | NO |
| 904d 결합 | **0.603** | **0.478** | **0.499** | **NO** |

**확정: CLIP 추가 시 모든 축 신호 강화 (2~2.5배). 904d 결합이 최선.**
**확정: structure/maturity 분리 불가 — 3모드 전부 NO. morphology로 합산.**

### 실험 5-3: 3D UMAP + Beauty Score + 클러스터 수
- beauty × morphology: r=0.758 (매우 강한 상관)
- 핵심 beauty 피처: jaw_angle(-0.611), eye_tilt(+0.560), forehead(+0.540)
- 자연 클러스터 최적 k=3 (silhouette=0.368)

**판단: beauty는 축이 아니라 "트렌드 레이어". 축은 비판단적 morphology로.**

### 실험 5-4: 한국 셀럽 48장 → SCUT PCA 공간 projection
- 6유형(morphology 3단계 × tone 2단계) 전부 채워짐, 최대 집중도 25%
- 단, SCUT 경계 사용 시 전원 Soft+Cool에 몰림 → 셀럽 데이터 기준 경계 필요

### 실험 5-5: PC1 정체 진단 (장원영 문제)
- 장원영이 soft 끝에 위치 — 상식과 반대
- **원인: 904d PCA의 PC1이 90.6% CLIP에 지배당함**
- CLIP이 "사진 분위기"를 잡아서 구조적 sharp/soft와 무관한 축이 됨
- 피처 비교: soft 그룹(한소희, 민지)이 실제로 jaw_angle 더 낮음(더 sharp)

### 실험 5-6: LM/CLIP 분리 PCA
- LM 136d PCA 단독: PC1이 피처와 상관 없음 (전부 |r|<0.3)
- **PC2가 morphology에 가까움** (cheekbone +0.66, forehead +0.77)
- CLIP 안정성: 사진 간 std = 1.67 (LM의 10.73보다 5배 안정적) → "촬영 컨디션 축" 우려 기각
- Morphology × Impression 독립성: r=0.087 → 완전 독립

### 실험 5-7: face_width 정규화 후 PCA
- 정규화 적용: 모든 랜드마크를 face_width 대비 비율로 변환
- 결과: PC1 설명력 37.0%, 하지만 피처 상관 여전히 |r|<0.3
- **3축 직교성은 개선됨** (Morph×Impr=0.087, Morph×Tone=0.060)
- **6유형 전부 채워짐**
- **하지만 카리나(jaw 101°)=Soft, 수지(jaw 105°)=Sharp — 상식 반대 여전**

### 근본 진단
> PCA의 한계: "분산이 가장 큰 방향" ≠ "의미 있는 방향"
> PC1이 잡는 기하학적 변동이 사람이 인식하는 "sharp↔soft"와 일치하지 않음

---

## Phase 6: LDA 반지도학습 (미실행 — 재개 시 시작점)

### 제안된 방법
- 16명 셀럽에 sharp/balanced/soft 라벨 **수동 부여**
- 136d (face_width 정규화) 공간에서 **LDA** → 그룹 간 최대 분리 방향 벡터
- 이 방향이 morphology 축의 constant

### PCA와의 차이
- PCA: "분산이 큰 방향" → 의미와 무관한 변동을 잡을 수 있음
- LDA: "사람이 정의한 그룹을 가장 잘 구분하는 방향" → 방향의 의미는 사람이 정해줌

### 필요한 것
1. 16명 셀럽 sharp/balanced/soft 라벨 (수동)
2. face_width 정규화된 136d 벡터 (이미 추출 완료)
3. LDA 피팅 → discriminant 방향 벡터 = morphology 축 constant
4. 이 방향과 jaw_angle, cheekbone 등의 상관 확인

### 기대 효과
- PC1이 못 잡는 "사람이 인식하는 sharp↔soft"를 데이터 기반으로 찾음
- 가중치가 데이터에서 나오되, 방향의 의미는 사람이 정해줌
- 카리나→sharp, 수지→soft로 올바르게 분류될 가능성

---

## 확정된 사항 요약

| # | 확정 사항 | 근거 실험 |
|---|---------|----------|
| 1 | AI 생성 이미지로 좌표축 앵커 불가 | Phase 3 (통과율 33%) |
| 2 | 136d raw 랜드마크 > 17개 파생 피처 | Phase 4 (실루엣 -0.016 vs +0.151) |
| 3 | structure/maturity 분리 불가 → morphology 1축으로 합산 | Phase 5-2 (3모드 전부 NO) |
| 4 | skin_warmth는 랜드마크/CLIP과 직교 (r≈0.06) | Phase 5-1, 5-7 |
| 5 | CLIP은 사진 간 안정적 (LM보다 5배 안정) | Phase 5-6 |
| 6 | Morphology × Impression 독립 (r=0.087) | Phase 5-6, 5-7 |
| 7 | Beauty는 축이 아니라 트렌드 레이어 | Phase 5-3 + 설계 판단 |
| 8 | PCA PC1이 "sharp↔soft"를 못 잡음 → LDA 필요 | Phase 5-5, 5-6, 5-7 |
| 9 | 자연 클러스터 최적 k=3, 6유형(3×2)은 경계 설정으로 | Phase 5-3 |
| 10 | SCUT 경계가 아닌 셀럽 데이터 기준 경계 사용해야 | Phase 5-4 |

## 기각된 가설

| 가설 | 기각 근거 |
|------|----------|
| CLIP으로 클러스터링 | 사진 분위기가 지배, 구조 무시 |
| AI 이미지로 앵커 구축 | 구조적 다양성 부족, 감지 실패 |
| 17개 hand-pick 피처로 충분 | 136d가 더 나음 |
| structure/maturity 독립 2축 | 3모드 전부 같은 차원에 로딩 |
| 8유형 체계 | 자연 클러스터 k=3 |
| PCA PC1 = morphology | PC1은 의미 없는 기하 변동 |
| 904d concat PCA | CLIP 90.6% 지배, 스케일 불균형 |

## 확정된 3축 구조 (상수 미확정)

```
축1 — Morphology: LM 136d(face_width 정규화) → LDA 방향벡터 (미산출)
축2 — Impression: CLIP 768d PCA PC1 (안정성 검증 완료)
축3 — Tone: skin_warmth (독립성 검증 완료)
```

## 코드베이스 변경 이력

| 파일 | 변경 | 상태 |
|------|------|------|
| `sigak/pipeline/cluster.py` | structural 클러스터링 모드, 컬러 서브타입, PCA loadings | 변경됨 |
| `sigak/pipeline/face.py` | `skin_warmth_score` 필드 + FaceFeatures 확장 | 변경됨 |
| `sigak/data/celeb_features_cache.json` | 새 앵커 사진 기반 재추출 | 갱신됨 |

## 실험 스크립트 위치

| 스크립트 | 용도 |
|---------|------|
| `experiments/scut-fbp5500/axis_validation.py` | v1: 136d UMAP 축 검증 |
| `experiments/scut-fbp5500/axis_validation_v2_clip.py` | v2: 136d+CLIP 비교 |
| `experiments/scut-fbp5500/axis_v3_3d_beauty.py` | v3: 3D UMAP + beauty + 클러스터 |
| `experiments/scut-fbp5500/celeb_projection.py` | 셀럽 → SCUT PCA 6유형 분포 |
| `experiments/scut-fbp5500/split_pca_validation.py` | LM/CLIP 분리 PCA + 안정성 |
| `experiments/scut-fbp5500/normalized_3axis.py` | face_width 정규화 3축 |

## 데이터 위치

| 데이터 | 경로 |
|--------|------|
| SCUT-FBP5500 | `experiments/scut-fbp5500/SCUT-FBP5500_v2/` |
| 셀럽 사진 48장 | `sigak/data/anchors/celeb/` |
| AI 생성 이미지 | `sigak/data/anchors/female/` |
| 셀럽 특징 캐시 | `sigak/data/celeb_features_cache.json` |

---

> **중단 사유**: 좌표계를 제품보다 먼저 완성하려는 순서 오류.
> 좌표계는 moat이지 product가 아님. 유저가 원하는 건 "정확하고 유용한 말"이지 "PC1 로딩".
> 재개 시: Phase 6 (LDA 반지도학습)부터, 셀럽 라벨 수동 부여 후 진행.
