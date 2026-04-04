# SIGAK — 기술 스택

## 기술 스택 개요

| 레이어 | 기술 | 버전 | 역할 |
|--------|------|------|------|
| **프론트엔드** | React | 18 | 컴포넌트 기반 UI |
| **백엔드** | FastAPI | 0.115.0 | 비동기 REST API |
| **서버** | Uvicorn | 0.30.0 | ASGI 서버 |
| **ORM** | SQLAlchemy | 2.0.35 | 데이터베이스 모델링 |
| **DB** | PostgreSQL | 16+ | 관계형 데이터 저장 |
| **벡터DB** | pgvector | 0.3.5 | CLIP 임베딩 저장 + 유사도 검색 |
| **DB 마이그레이션** | Alembic | 1.13.0 | 스키마 버전 관리 |
| **CV** | MediaPipe | 0.10.18 | 얼굴 랜드마크 추출 (468포인트) |
| **이미지 처리** | OpenCV | 4.10.0 | 피부톤 분석 (headless) |
| **이미지 유틸** | Pillow | 10.4.0 | 이미지 변환 |
| **수치 연산** | NumPy | 1.26.4 | 좌표 계산, 벡터 연산 |
| **LLM** | Anthropic Claude | 0.39.0 | 인터뷰 해석 + 리포트 생성 |
| **PDF** | WeasyPrint | 62.3 | HTML→PDF 렌더링 |
| **템플릿** | Jinja2 | 3.1.4 | 리포트 HTML 템플릿 |
| **스토리지** | AWS S3 (boto3) | 1.35.0 | 사진 업로드 저장 |
| **HTTP 클라이언트** | httpx | 0.27.0 | 외부 API 호출 |
| **검증** | Pydantic | 2.9.0 | 데이터 검증 + 설정 |

---

## 프론트엔드 기술 상세

### React 18
- **함수형 컴포넌트** + Hooks (`useState`, `useEffect`, `useRef`, `useCallback`)
- **빌드 시스템 없음** — 현재 단독 JSX 파일로 작성 (빌드 도구 미구성)
- **의존성 관리 없음** — `package.json` 미존재, CDN 또는 외부 번들러 의존 추정

### 스타일링 방식
- `landing.jsx`: **CSS-in-JS 문자열** — `const CSS` 템플릿 리터럴 + `<style>{CSS}</style>` 주입
- `sigak_dashboard.jsx`: **인라인 스타일 객체** — `const S = { ... }` + `style={S.navTab}` 방식
- CSS Variables 활용 (`--bg`, `--black`, `--serif`, `--sans`)
- 반응형: `@media (max-width: 768px)` 단일 브레이크포인트

### 외부 폰트
- `Pretendard Variable` — jsdelivr CDN (가변 폰트, 한글 서브셋)
- `Noto Serif KR` — Google Fonts (wght 200~900)

### UI 패턴
- **IntersectionObserver 기반 스크롤 reveal** — threshold 0.05, translateY 20px 애니메이션
- **오버레이 패널** — `position: fixed`, 우측 슬라이드(`translateX`), cubic-bezier 이징
- **상태 머신** — 예약 플로우 (티어→날짜→시간→폼→결제→완료)

---

## 백엔드 기술 상세

### FastAPI 0.115.0
- 비동기 엔드포인트 (`async def`)
- Pydantic v2 스키마 검증 (`BaseModel`, `model_dump()`)
- CORS 미들웨어 (현재 `allow_origins=["*"]` — 프로덕션 전 제한 필요)
- 파일 업로드: `UploadFile` + `python-multipart`

### 데이터베이스

#### PostgreSQL 16 + asyncpg
- 비동기 드라이버: `asyncpg==0.29.0`
- 연결 문자열: `postgresql+asyncpg://sigak:sigak@localhost:5432/sigak`

#### pgvector
- CLIP 임베딩 저장: `Vector(512)` 컬럼 (`face_analyses.clip_embedding`, `celeb_anchors.clip_embedding`)
- 셀럽 유사도 검색에 활용 예정

#### ORM 모델 (5 테이블)

| 테이블 | 주요 컬럼 | 관계 |
|--------|-----------|------|
| `users` | name, phone, tier, booking_date/time, status | → interview, analysis, report |
| `interviews` | 코어 6개 + 티어별 질문, raw_notes | ← user |
| `face_analyses` | 11개 구조 메트릭, clip_embedding(512d), 4축 좌표, 피부톤 | ← user |
| `reports` | current/aspiration coords, gap, sections JSON, 피드백, B2B 옵트인 | ← user |
| `celeb_anchors` | name, category, clip_embedding, 4축 좌표, anchor_roles | 독립 |

#### 현재 상태
- **인메모리 딕셔너리** 사용 중 (WoZ 단계)
- Alembic 마이그레이션 구성됨, 미실행

---

## CV 파이프라인 상세

### MediaPipe Face Mesh
- **468포인트 랜드마크** 추출 (정적 이미지 모드)
- `refine_landmarks=True` (눈 주변 정밀도 향상)
- 최소 검출 신뢰도: 0.5

### 구조적 메트릭 산출

| 메트릭 | 산출 방식 | 범위 |
|--------|-----------|------|
| `face_shape` | height/width 비율 + 턱 각도 + 광대 조합 분류 | oval/round/square/heart/oblong |
| `jaw_angle` | 좌턱-턱끝-우턱 3점 각도 | 110~150도 |
| `cheekbone_prominence` | (얼굴폭 - 턱폭) / 얼굴폭 * 3 | 0~1 |
| `eye_width_ratio` | 평균 눈 너비 / 얼굴 너비 | 0~1 |
| `eye_spacing_ratio` | 내안각 거리 / 얼굴 너비 | 0~1 |
| `nose_length_ratio` | 코 길이 / 얼굴 높이 | 0~1 |
| `lip_fullness` | 입술 높이 / 얼굴 높이 | 0~1 |
| `forehead_ratio` | 이마 높이 / 얼굴 높이 | 0~1 |
| `symmetry_score` | 좌우 5쌍 랜드마크 거리 비교 평균 | 0~1 |
| `golden_ratio_score` | 주요 비율의 phi(1.618) 근접도 | 0~1 |

### 피부톤 분석
- OpenCV BGR→LAB 색공간 변환
- 양쪽 볼 영역 샘플링 (얼굴 폭의 3% 반경)
- a*(적-녹) + b*(청-황) 채널 기반 warm/cool/neutral 분류
- L* 채널 기반 밝기(brightness) 0~1

### CLIP 임베딩 (미구현 — WoZ mock)
- 목표: `open-clip-torch` ViT-B-32 모델
- 현재: SHA256 해시 기반 결정론적 512차원 의사 임베딩
- 앵커 프로젝터: 랜덤 시드(42) 기반 방향 벡터

---

## 좌표계 엔진 상세

### 4축 정의 + 가중치

| 축 | 한국어 | -1 극 | +1 극 | 구조 가중치 | CLIP 가중치 |
|----|--------|-------|-------|------------|------------|
| structure | 구조 | 날카로운 | 부드러운 | 0.6 | 0.4 |
| impression | 인상 | 따뜻한 | 쿨한 | 0.2 | 0.8 |
| maturity | 성숙도 | 프레시 | 성숙한 | 0.4 | 0.6 |
| intensity | 강도 | 자연스러운 | 볼드 | 0.1 | 0.9 |

### 앵커 프로젝션 알고리즘
1. 각 축의 양극에 ~10명의 셀럽 CLIP 임베딩 평균을 앵커로 설정
2. 양극 평균 사이의 방향 벡터를 단위 정규화
3. 입력 임베딩을 방향 벡터에 투영 (내적)
4. 스케일링 (x5) 후 [-1, 1] 클리핑

### 구조 점수 → 축 점수 변환
- `structure`: 턱 각도(50%) + 광대 역수(30%) + 입술 풍성도(20%)
- `impression`: 눈 간격(50%) + 비대칭도(50%)
- `maturity`: 이마 비율(50%) + 눈 크기 역수(50%)
- `intensity`: 황금비 근접도

### 갭 분석
- 벡터 차이: `aspiration[axis] - current[axis]`
- 크기: 유클리드 노름
- 주/보조 이동 방향: 절대값 기준 정렬

---

## LLM 파이프라인 상세

### Claude API
- **모델:** `claude-sonnet-4-20250514`
- **용도 1:** 인터뷰 해석 — 자연어 추구미 → 4축 좌표 (max_tokens: 512)
- **용도 2:** 리포트 생성 — 전체 데이터 기반 6섹션 리포트 (max_tokens: 4096)

### 셀럽 레퍼런스 앵커 (시스템 프롬프트 내장)
8명의 사전 좌표: 수지, 제니, 아이유, 한소희, 카리나, 원빈, 차은우, 뉴진스(그룹)

### 리포트 구조
6개 섹션: `face_structure` → `skin_analysis` → `current_position` → `aspiration` → `gap_analysis` → `action_plan`
+ `action_items` (메이크업/헤어/스타일링/컬러) + `similar_celebs` + `trend_context`

### 에러 핸들링
- JSON 파싱 실패 시 폴백 (빈 리포트 + "수동 보정 필요" 메시지)
- 마크다운 코드 펜스 자동 제거

---

## 인프라 및 배포

### 현재 구성 (개발/WoZ)
- 로컬 개발 환경
- 인메모리 데이터 저장
- CORS `allow_origins=["*"]`
- `.env` 파일 기반 설정

### 프로덕션 계획
- **DB:** PostgreSQL 16 + pgvector (asyncpg 드라이버)
- **스토리지:** AWS S3 또는 MinIO (사진 업로드)
- **서버:** Uvicorn ASGI
- **도메인:** `sigak.kr`

---

## 개발 환경 요구사항

### Python 3.11+
```bash
pip install -r requirements.txt
```

### 주요 시스템 의존성
- **WeasyPrint:** GTK/Pango 라이브러리 필요 (OS별 설치 방법 상이)
- **MediaPipe:** Python 3.8~3.12 지원
- **PostgreSQL 16:** pgvector 확장 설치 필요

### 환경 변수 (`.env`)
```
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://sigak:sigak@localhost:5432/sigak
S3_BUCKET=sigak-uploads
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
```

---

## 기술적 결정 및 근거

| 결정 | 선택 | 근거 |
|------|------|------|
| 백엔드 프레임워크 | FastAPI | 비동기 지원, 자동 API 문서, Pydantic 네이티브 통합 |
| 얼굴 분석 | MediaPipe | 경량, 브라우저/서버 모두 가능, 468포인트 고밀도 |
| 임베딩 저장 | pgvector | PostgreSQL 네이티브, 별도 벡터DB 불필요 |
| LLM | Claude API | 한국어 이해도 높음, 구조화 JSON 출력 안정적 |
| PDF 생성 | WeasyPrint | CSS 기반 레이아웃, 디자인 시스템 일관성 유지 |
| 좌표계 가중치 | 축별 차등 | 인상/강도는 미묘한 분위기이므로 CLIP 의존, 구조는 측정 가능하므로 구조 의존 |
| WoZ mock | 결정론적 해시 | 같은 이미지이면 같은 결과 보장, A/B 비교 가능 |
| 인메모리 저장 | 딕셔너리 | WoZ 단계 빠른 반복, DB 마이그레이션 이후 전환 |
