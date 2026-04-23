# SIGAK 앵커 시스템 설계서

## 1. 현재 상태 분석

### 1.1 데이터 흐름 (AS-IS)

```
[사진 업로드]
    │
    ▼
face.py ─── MediaPipe 468 랜드마크 ─── structural features
    │
    ▼
coordinate.py ─── mock_clip_embedding(512d) ──┐
    │                                          │
    ├── structural_to_axis_scores()            │
    │      (jaw, cheek, lip → 4축 점수)        │
    │                                          │
    └── mock_anchor_projector(512d) ───────────┘
           (랜덤 시드 기반 가짜 축 벡터)         │
                                               ▼
                                    compute_coordinates()
                                    (structural × weight + clip × weight)
                                               │
                                               ▼
llm.py ─── 하드코딩 8명 좌표 레퍼런스 ─── generate_report()
    │                                          │
    │   similar_celebs = LLM이 감으로 선택      │
    │                                          │
    ▼                                          ▼
[리포트 JSON]
    │
    ▼
celeb-reference.tsx ─── 단일 셀럽 1명만 표시
    │                    {celeb: "수지", similarity: 85}
    │
    ▼
PaywallGate ─── unlock_level: "full" (₩20,000)
    │
    ▼
[유저에게 표시]
    티저: "수지와 85% 유사" (블러 처리)
    풀: 유사 이유 + 스타일링 팁
```

### 1.2 발견된 문제점

#### P0: 차원 불일치 (치명적)

| 위치 | 차원 | 비고 |
|------|------|------|
| `clip.py` CLIPEmbedder | **768d** | ViT-L-14 실제 출력 |
| `clip.py` mock_embedding | **768d** | 해시 기반 의사 임베딩 |
| `coordinate.py` mock_clip_embedding | **512d** | 다른 함수, 다른 차원 |
| `coordinate.py` mock_anchor_projector | **512d** | 프로젝터도 512d |
| `embed_anchors.py` | **768d** | clip.py의 mock_embedding 사용 |

**영향**: `main.py`는 `coordinate.py`의 512d mock을 사용하고, `embed_anchors.py`는 768d를 사용.
실제 CLIP 통합 시 `coordinate.py`의 프로젝터가 768d 임베딩을 받으면 **차원 오류로 크래시**.

#### P1: 유사도 계산 부재

현재 `similar_celebs`는 LLM이 프롬프트 컨텍스트만 보고 추측하는 값.
CLIP 임베딩 간 코사인 유사도를 계산하는 코드가 **전혀 없음**.

- 유저 사진의 CLIP 벡터 ↔ 앵커 셀럽 CLIP 벡터 비교 로직 없음
- `embed_anchors.py`가 `.npy`로 저장하지만, 이를 읽어서 비교하는 코드 없음
- `main.py`의 `run_analysis()`에서 유사도 계산을 호출하지 않음

#### P2: 프론트엔드 단일 셀럽 한계

`celeb-reference.tsx`는 **셀럽 1명**만 표시 가능:
```typescript
content: {
  celeb: string,        // 단일 이름
  similarity: number,   // 단일 수치
  reasons: string[],
  styling_tips: string[]
}
```

실제로는 top-3를 보여주고, 각각과의 축별 차이를 시각화해야
유저가 "나는 수지에 가깝지만, 인상 축에서는 카리나 쪽" 같은 인사이트를 얻음.

#### P3: NER/정규화 부재

`llm.py` INTERVIEW_SYSTEM에 8명이 하드코딩:
```python
- 수지: structure=0.4, impression=-0.2, ...
- 제니: structure=-0.5, impression=0.6, ...
```

문제:
- 유저가 "원영이" "카리나짱" 같은 비정규 이름 입력 시 LLM이 맥락에서 추론해야 함
- 앵커 추가/삭제 시 코드 수정 필요 (데이터가 코드에 박혀있음)
- 좌표값이 앵커 시스템의 실제 CLIP 프로젝션과 독립적으로 관리됨

#### P4: 앵커 ↔ 축 매핑 설정 부재

`AnchorProjector.fit()`은 축별 negative/positive 극의 평균 임베딩을 받지만,
"카리나는 structure.negative 극" 같은 **배정 설정이 없음**.

현재는 `embed_anchors.py`가 전체 임베딩만 저장하고, 축 배정은 수동으로 해야 하는 상태.

---

## 2. 목표 상태 (TO-BE)

### 2.1 데이터 흐름

```
[사진 업로드]
    │
    ▼
face.py ─── MediaPipe 랜드마크 ─── structural features
    │
    ▼
clip.py ─── CLIPEmbedder.extract() ─── 768d 임베딩
    │
    ▼
┌─────────────────────────────────────────────┐
│  celeb_anchors.json (마스터 데이터)          │
│  ├─ 15명 메타데이터 + NER 사전              │
│  ├─ 축 역할 배정 (structure.negative 등)    │
│  └─ community_score (커뮤 인기 지수)        │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
coordinate.py  similarity.py  llm.py
(768d 프로젝터) (top-K 매칭)  (동적 프롬프트)
    │          │          │
    └──────────┼──────────┘
               ▼
        main.py run_analysis()
               │
               ▼
        [리포트 JSON]
        ├─ current_coords: 4축 좌표
        ├─ similar_celebs: CLIP 코사인 유사도 top-3
        │   ├─ 셀럽별 유사도 %
        │   ├─ 축별 차이 벡터
        │   └─ 스타일링 인사이트
        └─ celeb_comparison: 유저↔앵커 대비점
               │
               ▼
        celeb-reference.tsx (확장)
        ├─ top-3 셀럽 카드
        ├─ 축별 비교 차트
        └─ 인기도 컨텍스트
```

### 2.2 UX 플로우 — 유저가 보는 화면

#### 무료 티저 (access_level: free)

```
┌─────────────────────────────────────┐
│  셀럽 레퍼런스                       │
│                                     │
│  "장원영과 78% 유사"                 │
│                                     │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  ░░░ (블러 처리된 상세 내용) ░░░░░  │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│                                     │
└─────────────────────────────────────┘
```

**티저 전략**: 가장 유사한 셀럽 1명 이름 + % 만 공개.
이름이 유명할수록 클릭 욕구가 강함 → 전환율에 직결.

#### 풀 언락 (access_level: full)

```
┌─────────────────────────────────────┐
│  셀럽 레퍼런스                       │
│                                     │
│  ┌───────┐ ┌───────┐ ┌───────┐    │
│  │장원영  │ │수지   │ │안유진  │    │
│  │ 78%   │ │ 71%   │ │ 68%   │    │
│  └───────┘ └───────┘ └───────┘    │
│                                     │
│  [축별 비교]                         │
│  구조:   당신 ──●────── 장원영       │
│  인상:   당신 ────●──── 장원영       │
│  성숙도: 당신 ●──────── 장원영       │
│  강도:   당신 ──────●── 장원영       │
│                                     │
│  "구조 축에서 장원영과 가장 가까우며, │
│   성숙도에서는 수지 쪽에 더 가깝습니다.│
│   현재 커뮤니티에서 장원영은           │
│   미모 인기도 1위입니다."             │
│                                     │
│  [스타일링 인사이트]                  │
│  • 장원영처럼 구조를 살리려면 ...     │
│  • 수지의 부드러운 인상을 참고하면 ... │
│                                     │
└─────────────────────────────────────┘
```

#### 데이터 무결성 체크포인트

| 체크포인트 | 검증 내용 | 실패 시 처리 |
|-----------|----------|-------------|
| 사진 → CLIP | 얼굴 미검출 또는 임베딩 실패 | structural only 모드 (clip_weight=0) |
| 앵커 로딩 | `.npy` 파일 존재 + 768d 검증 | mock 프로젝터 폴백 |
| 유사도 계산 | top-K 결과가 threshold 이상 | threshold 미만이면 "유사 셀럽 없음" 표시 |
| LLM 프롬프트 | JSON 셀럽 데이터 로드 성공 | 하드코딩 폴백 |
| 리포트 생성 | similar_celebs 배열 비어있지 않음 | LLM 추론 폴백 |
| 프론트엔드 | content.celebs[] 존재 | 단일 셀럽 폴백 렌더링 |

---

## 3. 데이터 스키마

### 3.1 celeb_anchors.json

```json
{
  "version": "1.0.0",
  "updated": "2026-04-06",
  "dimension": 768,
  "anchors": {
    "jang_wonyoung": {
      "name_kr": "장원영",
      "name_en": "Jang Wonyoung",
      "group": "IVE",
      "gender": "female",
      "aliases": ["원영", "원영이", "장원", "wonyoung"],
      "axis_roles": {
        "structure": "negative",
        "impression": "positive",
        "maturity": "negative",
        "intensity": "positive"
      },
      "reference_coords": {
        "structure": -0.7,
        "impression": 0.8,
        "maturity": -0.9,
        "intensity": 0.7
      },
      "community_score": null,
      "image_count": 0,
      "embedding_path": null
    }
  }
}
```

**필드 설명:**

| 필드 | 용도 | 소비자 |
|------|------|--------|
| `aliases` | NER 정규화 — 유저 입력 매칭 | `llm.py` 인터뷰 해석 |
| `axis_roles` | 축 극성 배정 — 프로젝터 fit() | `coordinate.py` |
| `reference_coords` | LLM 프롬프트 레퍼런스 | `llm.py` 프롬프트 |
| `community_score` | 커뮤 인기 지수 (0~100) | 리포트 컨텍스트, 클러스터 가중치 |
| `image_count` | 수집된 사진 수 (팀메이트가 채움) | `embed_anchors.py` 검증 |
| `embedding_path` | 생성된 임베딩 경로 | `similarity.py` 로더 |

### 3.2 축 역할 배정 규칙

`axis_roles`에서 각 셀럽이 어느 극에 기여하는지 정의:

```
structure.negative (sharp): 한소희, 카리나, 윈터, 장원영, 제니, 해린
structure.positive (soft):  설윤, 수지, 김유정, 안유진, 아이유, 김태리

impression.negative (warm): 아이유, 수지, 김유정, 화사, 김태리, 안유진, 지수
impression.positive (cool): 카리나, 윈터, 장원영, 한소희, 제니, 해린, 설윤

maturity.negative (fresh):  장원영, 해린, 김유정, 안유진, 민지, 윈터, 설윤
maturity.positive (mature): 한소희, 김태리, 제니, 화사, 지수, 카리나

intensity.negative (natural): 아이유, 수지, 김유정, 김태리, 해린, 안유진, 지수
intensity.positive (bold):    화사, 제니, 카리나, 장원영, 한소희, 윈터, 설윤
```

한 셀럽이 여러 축에 참여 가능. 민지는 `maturity.negative`에만 참여하고
나머지 축에서는 중립이므로 프로젝터 fit에 포함하지 않음 → 기준점 역할.

---

## 4. 파이프라인 변경 상세

### 4.1 similarity.py (신규)

```
역할: 앵커 임베딩 로딩 + 코사인 유사도 기반 top-K 셀럽 매칭

입력: 유저 CLIP 임베딩 (768d), 성별
출력: [
  {key: "jang_wonyoung", name_kr: "장원영", similarity: 0.78,
   axis_delta: {structure: +0.12, impression: -0.05, ...},
   community_score: 92},
  ...
]

의존: celeb_anchors.json + data/embeddings/{gender}/*.npy
폴백: 임베딩 없으면 reference_coords 기반 유클리드 거리
```

### 4.2 coordinate.py 수정

| 항목 | AS-IS | TO-BE |
|------|-------|-------|
| mock 차원 | 512d | 768d (clip.py와 통일) |
| 앵커 로딩 | 하드코딩 mock | JSON axis_roles 기반 자동 로딩 |
| 프로젝터 생성 | `mock_anchor_projector()` | `load_anchor_projector(gender, anchors_json)` |
| 폴백 | 랜덤 시드 | mock도 768d로 수정 |

### 4.3 llm.py 수정

| 항목 | AS-IS | TO-BE |
|------|-------|-------|
| 셀럽 레퍼런스 | 8명 문자열 하드코딩 | JSON에서 동적 로드 |
| 좌표값 | 수동 입력 | reference_coords 필드 사용 |
| 별명 처리 | LLM 추론 의존 | aliases 목록을 프롬프트에 포함 |
| similar_celebs | LLM이 추측 | CLIP 유사도 결과를 프롬프트에 주입 |

### 4.4 main.py 수정

`run_analysis()` 파이프라인에 유사도 단계 추가:

```
Step 1: face features (기존)
Step 2: CLIP embedding (기존, mock→real 전환 준비)
Step 3: compute_coordinates (기존, 768d로 수정)
Step 4: ★ compute_similarity(embedding, gender) ← 신규
Step 5: interpret_interview (기존, 동적 프롬프트)
Step 6: generate_report (기존, similar_celebs 주입)
```

### 4.5 프론트엔드 확장 (향후)

현재 `celeb-reference.tsx`는 단일 셀럽만 지원.
확장 시 타입 변경:

```typescript
// AS-IS
content: { celeb: string, similarity: number, reasons: string[], styling_tips: string[] }

// TO-BE
content: {
  celebs: {
    key: string,
    name: string,
    similarity: number,
    axis_delta: Record<string, number>,
    community_rank?: number
  }[],
  primary_insight: string,
  styling_tips: string[]
}
```

이 변경은 백엔드가 완성된 후 진행. 현재는 top-1만 기존 포맷으로 내려보내도 됨.

---

## 5. 커뮤니티 인기 지수 활용 설계

### 5.1 데이터 소스 (향후)

```
수동 입력 (현재)
    → celeb_anchors.json의 community_score 필드에 직접 입력
    → 0~100 스케일, null이면 미측정

크롤러 (향후)
    → 더쿠/팬/인스티즈 "예쁜 여돌" 글 주기적 수집
    → 긍정 문맥 가중치 + 부정 문맥 페널티
    → 월별 업데이트 → community_score 자동 갱신
```

### 5.2 활용 포인트

1. **리포트 컨텍스트**: "당신과 가장 유사한 장원영은 현재 커뮤니티 미모 인기도 1위"
2. **클러스터 라벨링**: 임베딩 공간의 클러스터에 인기도 가중 라벨 부여
3. **티저 최적화**: 유사 셀럽 중 community_score가 가장 높은 셀럽을 티저에 노출
   → "수지와 71% 유사"보다 "장원영과 78% 유사"가 전환율 높을 가능성

### 5.3 티저 셀럽 선택 로직

```python
def select_teaser_celeb(similar_celebs: list[dict]) -> dict:
    """
    티저에 노출할 셀럽 선택.
    유사도와 인기도의 가중 평균으로 결정.

    전략: similarity 70% + community_score 30%
    → 유사도가 높으면서 유명한 셀럽이 티저에 나옴
    """
    for celeb in similar_celebs:
        score = celeb["similarity"] * 0.7
        if celeb.get("community_score"):
            score += (celeb["community_score"] / 100) * 0.3
        celeb["teaser_score"] = score
    return max(similar_celebs, key=lambda c: c["teaser_score"])
```

---

## 6. 구현 우선순위

| 순서 | 작업 | 사진 필요 | 비고 |
|------|------|----------|------|
| 1 | `celeb_anchors.json` 생성 | X | 모든 코드가 의존 |
| 2 | `similarity.py` 구현 | X | 폴백 모드로 동작 가능 |
| 3 | `llm.py` 프롬프트 업데이트 | X | JSON 동적 로드 |
| 4 | `coordinate.py` 768d 통일 | X | 차원 불일치 수정 |
| 5 | `main.py` 파이프라인 통합 | X | 1~4 연결 |
| 6 | 사진 수집 + embed_anchors.py 실행 | **O** | 팀메이트 작업 후 |
| 7 | 실제 유사도 검증 + UMAP | **O** | 6 이후 |
| 8 | 프론트엔드 celeb-reference 확장 | X | 백엔드 완성 후 |
| 9 | 커뮤 크롤러 + community_score 자동화 | X | 향후 |

**1~5는 사진 없이 지금 바로 가능.**

---

## 7. 구조적 비교 엔진 (comparison.py)

### 7.1 개요

유저 사진에서 뽑은 MediaPipe 구조적 특징(jaw_angle, eye_ratio 등)을
앵커 셀럽의 동일한 특징과 비교하여 **핀포인트 차이**를 산출한다.

"수지와 82% 유사" → "수지보다 턱선이 15% 더 각지고, 눈이 12% 더 큼"

### 7.2 특징 → 축 매핑

| 특징 | 축 | 값 높을 때 | 값 낮을 때 |
|------|---|-----------|-----------|
| jaw_angle (턱선 각도) | structure | soft (둥근) | sharp (각진) |
| cheekbone_prominence (광대) | structure | sharp (뚜렷) | soft (부드러운) |
| lip_fullness (입술) | structure | soft (풍성) | sharp (얇은) |
| eye_spacing_ratio (눈 간격) | impression | warm (넓은) | cool (좁은) |
| symmetry_score (대칭도) | impression | cool (정돈) | warm (자연) |
| eye_width_ratio (눈 크기) | maturity | fresh (큰) | mature (작은) |
| forehead_ratio (이마) | maturity | mature (넓은) | fresh (좁은) |
| nose_length_ratio (코 길이) | maturity | mature (긴) | fresh (짧은) |
| golden_ratio_score (황금비) | intensity | bold (또렷) | natural (편안) |

### 7.3 데이터 흐름

```
embed_anchors.py 실행 시:
  앵커 이미지 → face.py analyze_face() → 구조적 특징 추출
                                        → data/anchor_features/{key}.json 저장

유저 분석 시:
  유저 사진 → face.py → features
  features + similar_celebs → comparison.py compare_with_top_celebs()
                            → [{celeb_key, comparisons: [{feature, diff_pct, axis, pole}]}]
                            → LLM 프롬프트에 주입
                            → 리포트에 구체적 비교 피드백
```

### 7.4 LLM 프롬프트 주입 예시

```
[유저↔앵커 구조적 비교 (MediaPipe 기반)]

  vs 수지 (유사도 82%):
    - 턱선 각도이(가) 수지보다 15.2% 더 낮습니다 → structure 축 sharp 방향
    - 눈 크기이(가) 수지보다 12.1% 더 큽니다 → maturity 축 fresh 방향
    - 광대 돌출도이(가) 수지보다 8.5% 더 큽니다 → structure 축 sharp 방향
    요약: 턱선 각도 sharp (structure→sharp), 눈 크기 fresh (maturity→fresh)

  → 위 구조적 차이를 리포트의 face_structure 섹션과 similar_celebs 비교에 반영
```

---

## 8. 클러스터 라벨링 시스템 (cluster.py)

### 8.1 개요

CLIP 임베딩 공간에서 앵커 셀럽들이 형성하는 클러스터를 정의하고,
유저를 가장 가까운 클러스터에 배정하여 "당신은 Cool Goddess 타입" 같은
직관적 라벨을 제공한다.

### 8.2 사전 정의 클러스터 (사진 전)

| ID | 라벨 | 한국어 | 시드 멤버 | 지배 축 |
|---|---|---|---|---|
| cool_goddess | Cool Goddess | 쿨한 여신 | 카리나, 한소희, 제니, 윈터 | sharp + cool + bold |
| warm_natural | Warm Natural | 따뜻한 내추럴 | 수지, 아이유, 김유정, 김태리 | soft + warm + natural |
| fresh_doll | Fresh Doll | 프레시 돌 | 장원영, 안유진, 민지, 해린 | fresh + soft |
| bold_icon | Bold Icon | 볼드 아이콘 | 화사, 제니 | bold + mature |
| soft_elegance | Soft Elegance | 소프트 엘레강스 | 수지, 김태리, 지수 | soft + mature + natural |

### 8.3 데이터 기반 클러스터 (사진 후)

사진 임베딩이 준비되면 `discover_clusters()`가 HDBSCAN으로 실제 클러스터를 발견:

```
embed_anchors.py 실행
  → CLIP 임베딩 생성
  → UMAP 시각화에서 클러스터 확인
  → discover_clusters() 호출
  → 자동 라벨링 (축 중심값 → 키워드 조합)
  → data/clusters.json 저장
```

### 8.4 자동 라벨링 규칙

중심 좌표의 절댓값 ≥ 0.3인 축에서 극성을 추출하고 키워드를 조합:

```
(sharp, cool) → "Sculpted Goddess"   / "조각같은 여신"
(soft, warm)  → "Soft Angel"         / "부드러운 엔젤"
(sharp, warm) → "Sculpted Fox"       / "조각같은 여우상"
(soft, cool)  → "Soft Fairy"         / "부드러운 요정"
(fresh)       → "Fresh Doll"         / "프레시 돌"
(mature)      → "Elegant Icon"       / "우아한 아이콘"
(bold)        → "Bold Statement"     / "볼드 스테이트먼트"
(natural)     → "Natural Muse"       / "내추럴 뮤즈"
```

### 8.5 community_score 가중치

클러스터 배정 시 community_score로 가중치 적용 가능:

```python
assign_cluster(user_coords, community_weight=0.3)
# → 인기도 높은 클러스터 방향으로 약간 끌림
# → 유저가 "트렌디한 타입"으로 분류될 확률 상승
# → 0.0이면 순수 거리 기반 (기본값)
```

### 8.6 리포트에서 활용

```
"당신은 '쿨한 여신(Cool Goddess)' 클러스터에 속합니다.
 카리나, 한소희, 제니와 같은 날카로운 이목구비와 쿨한 인상이 특징입니다.
 현재 이 클러스터 멤버들의 평균 커뮤니티 인기도는 89점으로,
 가장 주목받는 미감 유형입니다."
```

---

## 9. 전체 파이프라인 (최종)

```
Step 1: face.py        → 구조적 특징 추출
Step 2: clip.py        → 768d CLIP 임베딩
Step 3: coordinate.py  → 4축 좌표 계산
Step 4: similarity.py  → top-3 유사 셀럽 (CLIP cosine / 좌표 폴백)
Step 5: comparison.py  → 유저↔셀럽 구조적 차이 분석
Step 6: cluster.py     → 미감 클러스터 배정
Step 7: llm.py         → 인터뷰 해석 → 추구미 좌표
Step 8: coordinate.py  → 갭 계산
Step 9: llm.py         → 리포트 생성 (모든 데이터 주입)
```
