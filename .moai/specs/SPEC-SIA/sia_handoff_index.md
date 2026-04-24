# Sia 프로젝트 핸드오프 인덱스 (v2)

> 작성: 2026-04-22
> 버전: v2 — 세션 #5, #6 완결편화. 모든 결정 사항 pending 해소
> 대상: Sia 프로젝트 문서 세트 수신자 (CTO 포함)

---

## 문서 세트 (v2)

| 파일 | 역할 | 상태 |
|---|---|---|
| **`sia_session4_output_v2.md`** | **메인 spec. 구현 시 이 문서 기준.** | ✅ 완결 |
| `sia_session5_output_v2.md` | 협조 유저 기준 드라이런 완결 | ✅ 완결 |
| `sia_session6_output_v2.md` | 대화 실패 모드 대응 (단답/이탈/과몰입) + 14 타입 체계 확정 | ✅ 완결 |
| `sia_handoff_index.md` (본 문서) | 네비게이션 | - |

**과거 버전 (보관/히스토리용):**
- `sia_session4_output.md` (v1)
- `sia_session5_output.md` (v1)
- `sia_session6_output.md` (v1)

---

## 읽기 순서

### CTO (프론트엔드 구현자) 기준

1. **`sia_session4_output_v2.md`** 만 읽으면 됨. self-contained
2. 구현 중 "단답 연타 / 이탈 / 과몰입" 대응 로직이 필요하면 → **`sia_session6_output_v2.md`** 추가 참조
3. 드라이런 방법론/가설 검증 내용이 궁금하면 → `sia_session5_output_v2.md`

### 맥락 파악 기준

1. 본 인덱스
2. 세션 #4 v2 섹션 0 (변경 이력) + 섹션 1 (스코프)
3. 세션 #5 v2 (드라이런 + 가설 검증)
4. 세션 #6 v2 (실패 모드 대응)

---

## 현재 상태 요약

### ✅ 확정 (v2 완결편에 전부 반영됨)

**구조:**
- 페르소나 B-친밀형
- 비율 30 : 50 : 20 + sub-rule
- **14 타입 체계** (기존 11 + 신규 3: CHECK_IN, RE_ENTRY, RANGE_DISCLOSURE)
- 버킷: 수집 / 이해 / 여백 / **관리 (신규, 트리거 기반)**
- M1 결합 출력 (OPENING_DECLARATION + OBSERVATION 한 메시지)

**룰:**
- A-1 ~ A-8: 어휘, 비율, 트리거, 공감, 인식, B-친밀형, 추상화, 질문 종결
- A-9: 단답 연타 에스컬레이션 (B → D → 이양)
- A-10: 이탈 신호 대응
- A-11: 과몰입 대응 (경미/심각 분리)

**구현 자산:**
- 하드코딩 39 문구 (4 타입 20 + 신규 3 타입 18 + 이탈 종결 V5 1)
- Haiku Jinja 7 타입 + base.jinja (+ `is_first_turn` 분기)
- Validator FP 0, FN 0 기준선 (패치 코드 제공)
- 드라이런 3건 완주 (만재 / 지은 / 준호)

**본인 결정:**
- 세션 #5 섹션 7: (a) / (a) 확정
- 세션 #6 섹션 10: (a) / (a) / (a) 확정
- EMPATHY_MIRROR sub-rule: 보수적 가이드 (hard cap 아님)
- RECOGNITION sub-rule: 2회 하한 우선 (% 는 가이드)
- "잘 모르겠어요" 단답 카운트 포함
- 이탈 시 M9 RE_ENTRY 종결 버전 송출

### 🟡 Pending (구현 블로커 아님, 세션 #7 에서 처리)

**실측 검증 이슈 (세션 #4 v2 섹션 10.2):**
- EMPATHY_MIRROR 질문 종결 처리 (실측에서 유저 기대 감지, 현 spec 은 서술 종결)
- Haiku 어휘 자연스러움 (적나라/어색 표현 방지)
- 일반화 회피 방어 블록 신규 필요 ("뭐 다들 그런 거 아닌가요" 대응)

**미설계 영역:**
- 진단 이후 결과물 레이어 (₩49,000 full report 와 대화 관계)
- 오프닝 전 화면 흐름 (피드 링크 입력 → 분석 로딩)
- 추가 실패 모드 (So-what, 부정적 해석, 조언 요구)

---

## 로드맵

### 단기 (세션 #7)

- 실측 검증 이슈 3건 spec 정리
- 추가 실패 모드 spec
- 진단 이후 결과물 레이어 초안

### 중기 (Phase H = Claude Code 구현)

현 v2 기준으로 착수 가능. 생성될 파일:

```
sia/
├── state.py                        # 14 타입 enum + ConversationState
├── decide.py                       # decide_next_message (A-9/10/11 반영)
├── validator.py                    # 전체 패치 통합
├── hardcoded.py                    # pick_variant + 39 문구
├── templates/
│   └── hardcoded.yaml
├── prompts/
│   └── haiku/
│       ├── base.jinja
│       ├── observation.jinja       (is_first_turn 분기)
│       ├── probe.jinja
│       ├── extraction.jinja
│       ├── empathy_mirror.jinja
│       ├── recognition.jinja
│       ├── confrontation.jinja
│       └── diagnosis.jinja
├── haiku_client.py                 # API wrapper, fallback 3회 실패
└── tests/
    ├── test_validator.py
    ├── test_hardcoded.py
    └── fixtures/
        ├── sample_2_manjae.yaml
        ├── sample_3_jieun.yaml
        └── sample_4_junho.yaml
```

### 장기 (Phase H 이후)

**500회 실사용자 페르소나 실험 (창업자 로드맵):**
- Phase H 완료 후 실시스템 대상 대규모 검증
- 페르소나 구성 권장: 협조 40% / 단답/이탈 30% / 적대 10% / 과몰입 5% / 엣지 15%
- 발견되는 실패 모드는 세션 #8+ 에서 spec 반영

---

## CTO 에게

- 프론트엔드 작업은 v2 3종 (세션 #4/5/6) 기준
- 세션 #4 v2 가 메인 spec, 세션 #6 v2 가 실패 모드 대응 확장
- 구현 중 엣지 케이스 마주치면 창업자 바로 문의. 추측 구현 금지
- Phase H (백엔드 구현) 는 창업자 주도. 프론트는 API 계약만 확정되면 먼저 진행 가능

---

## 창업자에게 (본인)

세션 #7 진입 시 다룰 것:
- 실측 이슈 3건 (EMPATHY 질문 종결 / 어휘 자연스러움 / 일반화 회피 블록)
- 추가 실패 모드 발굴 2-3건
- 진단 이후 결과물 레이어 or 오프닝 전 화면 중 택 1

Phase H 직진 vs 세션 #7 경유 판단은 CTO 와 협의. 보통 세션 #7 1회로 실측 이슈 정리하고 Phase H 착수 권장.
