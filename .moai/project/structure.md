# SIGAK — 프로젝트 구조

## 디렉토리 트리

```
Sigak/
├── landing.jsx                    # 고객용 랜딩 페이지 (예약 플로우)
├── sigak_dashboard.jsx            # 내부 인터뷰어 대시보드
├── sigak-backend.tar.gz           # 백엔드 아카이브
│
├── [Backend: sigak/]
│   ├── main.py                    # FastAPI 앱 + 전체 API 엔드포인트 정의
│   ├── config.py                  # 환경 설정 (Pydantic Settings)
│   ├── db.py                      # SQLAlchemy ORM 모델 (5개 테이블)
│   ├── requirements.txt           # Python 의존성
│   └── pipeline/
│       ├── __init__.py
│       ├── face.py                # MediaPipe + OpenCV 얼굴 분석
│       ├── coordinate.py          # 4축 미감 좌표계 엔진
│       └── llm.py                 # Claude API 연동 (해석 + 리포트 생성)
│
├── .moai/                         # MoAI-ADK 프로젝트 설정
│   ├── config/sections/
│   │   ├── language.yaml          # 언어 설정
│   │   └── user.yaml              # 사용자 설정
│   └── project/
│       ├── product.md             # 제품 개요
│       ├── structure.md           # 프로젝트 구조 (현재 문서)
│       └── tech.md                # 기술 스택
│
├── .claude/                       # Claude Code 설정
├── .mcp.json                      # MCP 서버 설정
├── .gitignore
└── CLAUDE.md                      # Claude Code 지침서
```

---

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
│                                                                 │
│  ┌──────────────────────┐    ┌───────────────────────────────┐  │
│  │   landing.jsx        │    │   sigak_dashboard.jsx         │  │
│  │   (고객 예약 UI)      │    │   (인터뷰어 대시보드)          │  │
│  │                      │    │                               │  │
│  │  - 예약 캘린더        │    │  - 대기열 관리                 │  │
│  │  - 티어 선택          │    │  - 인터뷰 데이터 입력          │  │
│  │  - 결제 플로우        │    │  - 사진 업로드                 │  │
│  │  - 좌석 현황          │    │  - 가설 검증 지표              │  │
│  └──────────────────────┘    └───────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API
┌───────────────────────────────▼─────────────────────────────────┐
│                      API Layer (FastAPI)                        │
│                        main.py                                  │
│                                                                 │
│  /api/v1/booking          POST  예약 생성                       │
│  /api/v1/interview/{id}   POST  인터뷰 데이터 제출              │
│  /api/v1/photos/{id}      POST  사진 업로드 + 즉시 분석         │
│  /api/v1/analyze/{id}     POST  전체 파이프라인 실행             │
│  /api/v1/report/{id}      GET   리포트 조회                     │
│  /api/v1/feedback/{id}    POST  피드백 제출                     │
│  /api/v1/dashboard/queue  GET   대기열 조회                     │
│  /api/v1/dashboard/stats  GET   가설 검증 지표                  │
│  /api/v1/axes             GET   좌표축 정의 조회                │
│  /health                  GET   헬스체크                        │
└──────────┬──────────────────────────┬───────────────────────────┘
           │                          │
┌──────────▼──────────┐   ┌───────────▼──────────────────────────┐
│  Data Layer         │   │  Pipeline Layer                      │
│                     │   │                                      │
│  In-Memory Store    │   │  face.py        MediaPipe 468점      │
│  (WoZ Phase)        │   │                 얼굴 랜드마크 추출    │
│                     │   │                 + OpenCV 피부톤 분석  │
│  → PostgreSQL 16    │   │                                      │
│    + pgvector       │   │  coordinate.py  4축 좌표 산출        │
│    + asyncpg        │   │                 구조 점수 + CLIP     │
│                     │   │                 앵커 프로젝션         │
│  → S3 (이미지)      │   │                                      │
│                     │   │  llm.py         Claude API           │
│  5 Tables:          │   │                 인터뷰 해석           │
│  - users            │   │                 + 리포트 생성        │
│  - interviews       │   │                                      │
│  - face_analyses    │   │  → WeasyPrint   PDF 렌더링           │
│  - reports          │   │  → Jinja2       HTML 템플릿           │
│  - celeb_anchors    │   │                                      │
└─────────────────────┘   └──────────────────────────────────────┘
```

---

## 핵심 파일 상세

### 프론트엔드

#### `landing.jsx` — 고객 예약 페이지
- **컴포넌트:** `App` (메인), `Overlay` (예약 패널), `R` (스크롤 reveal), `Inp` (입력 필드)
- **데이터:** 하드코딩된 예약 현황 (`BOOKINGS` 객체), 티어 정의 (`TIERS` 배열)
- **레이아웃:** NAV → HERO → TIERS(x3) → EXPERTS(x2) → SEATS → CTA → FOOTER
- **스타일:** 인라인 CSS 문자열 (`const CSS`), CSS Variables 활용
- **반응형:** 768px 브레이크포인트, 모바일에서 단일 컬럼 전환

#### `sigak_dashboard.jsx` — 인터뷰어 대시보드
- **뷰:** Queue(대기열), Entry(인터뷰 입력), Stats(가설 지표)
- **컴포넌트:** `QueueView`, `EntryView`, `StatsView`, `StatCard`
- **데이터:** Mock 데이터 (`MOCK_QUEUE`, `MOCK_STATS`) — 백엔드 연동 예정
- **질문 구조:** 코어 6개 + Wedding 2개 + Creator 3개 (티어별 동적 구성)
- **스타일:** 인라인 스타일 객체 (`const S`) + CSS 문자열

### 백엔드

#### `main.py` — FastAPI 애플리케이션
- 10개 API 엔드포인트 정의
- 인메모리 딕셔너리 기반 데이터 저장 (WoZ)
- Pydantic 스키마: `BookingCreate`, `InterviewSubmit`, `FeedbackSubmit`
- CORS 미들웨어 (현재 `allow_origins=["*"]`)

#### `db.py` — 데이터베이스 모델
- SQLAlchemy ORM + asyncpg
- 5개 테이블: `users`, `interviews`, `face_analyses`, `reports`, `celeb_anchors`
- pgvector: CLIP 임베딩 저장용 `Vector(512)` 컬럼

#### `config.py` — 환경 설정
- Pydantic Settings 기반 `.env` 파일 로딩
- DB, S3, LLM, CV Pipeline, 좌표계, 리포트 설정

#### `pipeline/face.py` — 얼굴 분석
- MediaPipe Face Mesh 468포인트 랜드마크 추출
- 11개 구조적 메트릭 산출
- 얼굴형 분류 (oval/round/square/heart/oblong)
- OpenCV LAB 색공간 피부톤 분석

#### `pipeline/coordinate.py` — 좌표계 엔진
- 구조적 특징 → 축별 점수 변환
- CLIP 앵커 프로젝션 (셀럽 임베딩 기반 방향 벡터)
- 가중 결합: 축별 structural_weight + clip_weight
- 갭 분석: 현재↔추구미 벡터 차이 + 주/보조 이동 방향

#### `pipeline/llm.py` — LLM 파이프라인
- Claude API 기반 인터뷰 해석 → 추구미 좌표
- 셀럽 레퍼런스 그라운딩 (8명 사전 좌표)
- 6섹션 구조화 리포트 생성
- JSON 출력 강제 + 파싱 실패 폴백

---

## 데이터 플로우

```
고객 예약 (landing.jsx)
    │
    ▼
POST /booking → USERS 저장
    │
    ▼
인터뷰어 대기열 확인 (dashboard)
    │
    ▼
인터뷰 진행 → POST /interview/{id}
    │
    ▼
사진 촬영 → POST /photos/{id}
    │              │
    │              ▼
    │        face.py: MediaPipe 랜드마크 추출
    │              │
    │              ▼
    │        구조적 메트릭 + 피부톤 분석
    │
    ▼
POST /analyze/{id}
    │
    ├─→ coordinate.py: 현재 좌표 산출
    │
    ├─→ llm.py (interpret): 인터뷰 → 추구미 좌표
    │
    ├─→ coordinate.py (gap): 현재↔추구미 갭 계산
    │
    └─→ llm.py (report): 전체 리포트 생성
              │
              ▼
        REPORTS 저장 → GET /report/{id}
              │
              ▼
        PDF 렌더링 (WeasyPrint + Jinja2)
              │
              ▼
        POST /feedback/{id} → 가설 검증 지표 업데이트
```

---

## 디자인 시스템 구조

### 공통 디자인 토큰

두 프론트엔드 애플리케이션이 공유하는 디자인 요소:

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--bg` | `#F3F0EB` | 전체 배경 (웜 아이보리) |
| `--black` | `#000000` | 포그라운드, 텍스트, 액티브 상태 |
| `--serif` | `Noto Serif KR` | 헤드라인, 숫자, 감성 텍스트 |
| `--sans` | `Pretendard Variable` | 본문, UI, 레이블, 버튼 |
| 디바이더 | `1px solid rgba(0,0,0,0.1~0.15)` | 섹션 구분선 |
| 패딩 | `60px` (데스크탑) / `24px` (모바일) | 수평 여백 |
| 레터스페이싱 | `1~2.5px` | 라벨, 네비게이션, 섹션 타이틀 |

### 컴포넌트 패턴

- **네비게이션 바:** 검정 배경 고정(sticky), 로고 중앙, 링크 양사이드
- **섹션 구조:** 컨텐츠 블록 + 1px 디바이더 반복
- **카드/통계:** 테두리 그리드, 세리프 대형 숫자 + 산세리프 라벨
- **버튼/CTA:** 검정 배경 + 아이보리 텍스트 (활성), opacity 비활성
- **오버레이:** 우측 슬라이드 패널, 반투명 배경 딤
- **상태 뱃지:** 라운드 4px, opacity 기반 계층 구분
