# Sia 프로젝트 핸드오프 인덱스 (v3)

> 작성: 2026-04-23
> 버전: v3 — 세션 #7 완결편 등록. 본 세션 결정 사항 (B2B talent pool 영구 삭제, 신규 룰 5건, CONFRONTATION 블록 2개) 반영
> 대상: Sia 프로젝트 문서 세트 수신자 (CTO 포함)

---

## 문서 세트 (v3)

| 파일 | 역할 | 상태 |
|---|---|---|
| **`sia_session4_output_v2.md`** | **메인 spec. 구현 시 이 문서 기준 + 세션 #7 patch 적용** | ✅ 완결 (세션 #7 patch 대상) |
| `sia_session5_output_v2.md` | 협조 유저 기준 드라이런 완결 | ✅ 완결 |
| `sia_session6_output_v2.md` | 대화 실패 모드 대응 (단답/이탈/과몰입) + 14 타입 체계 확정 | ✅ 완결 (세션 #7 patch 대상) |
| **`sia_session7_output.md`** | **본 세션 작업 결과 — A-1 / A-2 / C6 / C7 / A-12-16 신규 룰 + B2B talent pool 영구 삭제** | ✅ 신규 (본 판) |
| `sia_handoff_index.md` (본 문서) | 네비게이션 | v3 갱신 |

**과거 버전 (보관/히스토리용):**
- `sia_session4_output.md` (v1)
- `sia_session5_output.md` (v1)
- `sia_session6_output.md` (v1)
- `sia_handoff_index.md` (v2)

---

## 읽기 순서

### CTO (프론트엔드 구현자) 기준

1. **`sia_session4_output_v2.md`** + 세션 #7 패치 매니페스트 (`sia_session7_output.md` §10.1) 같이 읽기
2. 실패 모드 / 신규 14 타입 / 관리 버킷 → **`sia_session6_output_v2.md`** + 세션 #7 패치 매니페스트 (`sia_session7_output.md` §10.2)
3. **세션 #7 신규 룰 (A-1 / A-12-16 / C6 / C7 / RANGE_REAFFIRM) → `sia_session7_output.md`** 직접 참조
4. 드라이런 방법론/가설 검증 내용이 궁금하면 → `sia_session5_output_v2.md`

### 맥락 파악 기준

1. 본 인덱스
2. 세션 #4 v2 섹션 0 (변경 이력) + 섹션 1 (스코프)
3. 세션 #5 v2 (드라이런 + 가설 검증)
4. 세션 #6 v2 (실패 모드 대응 + 14 타입)
5. 세션 #7 (본 세션 신규 룰 + 로플레이 fixture 2건)

---

## 현재 상태 요약

### ✅ 확정 (v3 기준)

**구조:**
- 페르소나 B-친밀형
- 비율 30 : 50 : 20 + sub-rule
- 14 타입 체계 (변경 없음 — 세션 #7 신규 타입 0)
- 버킷: 수집 / 이해 / 여백 / 관리
- M1 결합 출력 (OPENING_DECLARATION + OBSERVATION 한 메시지)
- **결합 출력 패턴 일반화 (세션 #7) — EMPATHY 결합 출력 + 향후 다른 타입 확장 가능**
- **RANGE_DISCLOSURE 모드 분기 (세션 #7) — limit / reaffirm**

**룰:**
- A-1 ~ A-8: 어휘, 비율, 트리거, 공감, 인식, B-친밀형, 추상화, 질문 종결
- A-9: 단답 연타 에스컬레이션 (B → D → 이양)
- A-10: 이탈 신호 대응
- A-11: 과몰입 대응 (경미/심각 분리)
- **A-12 (세션 #7 신규): 질문 종결 신규 정보 원칙**
- **A-13 (세션 #7 신규): 자기 충만형 라포 prefix**
- **A-14 (세션 #7 신규): 사족 금지 — A-2 base.jinja negative example 흡수**
- **A-15 (세션 #7 신규): 산출물 가치사슬 정합 원칙. B2B talent pool 영구 삭제 반영**
- **A-16 (세션 #7 신규): 유저 명시 자기인지 존중 원칙**

**CONFRONTATION 블록:**
- C1: 외부 권위 회귀 돌파
- C2: 자기 축소/체념 돌파
- C3: 반문 공격 돌파
- C4: 주제 이탈 돌파
- C5 = META_REBUTTAL (섹션 5 기준)
- **C6 (세션 #7 신규): 평가 의존 돌파**
- **C7 (세션 #7 신규): 일반화 회피 돌파 (= 원 A-3 이슈 해소)**

**구현 자산:**
- 하드코딩 44 문구 (4 타입 20 + 신규 3 타입 18 + 이탈 종결 V5 1 + **RANGE_REAFFIRM 5**)
- Haiku Jinja 7 타입 + base.jinja (+ `is_first_turn` 분기 + **세션 #7: A-2 어휘 보강 + A-14 사족 금지 + 친구 톤 positive example + 적나라 변환 표**)
- Validator FP 0, FN 0 기준선 (패치 코드 제공) + **세션 #7: check_haiku_naturalness, C6 / C7 검증 추가**
- 드라이런 fixture 누적 5건 (만재 / 지은 / 준호 / **서연 (세션 #7)** / **도윤 (세션 #7)**)

**사업 정체성:**
- **B2B 캐스팅 talent pool 영구 삭제 (세션 #7, 본인 결정 2026-04-23)** — A-15 산출물 가치사슬에서 제거. 향후 어떤 작업에서도 talent pool 호명 금지

**본인 결정 누적:**
- 세션 #5 섹션 7: (a) / (a) 확정
- 세션 #6 섹션 10: (a) / (a) / (a) 확정
- EMPATHY_MIRROR sub-rule: 보수적 가이드
- RECOGNITION sub-rule: 2회 하한 우선
- "잘 모르겠어요" 단답 카운트 포함
- 이탈 시 M9 RE_ENTRY 종결 버전 송출
- **세션 #7 본인 결정 로그 14건 (`sia_session7_output.md` §13 참조)**

### 🟡 보류 (CTO / 사업 결정 필요)

- **A-17: 가격/결제 응대 원칙** — 세션 #7 발견. CTO 결정 후 spec 화. 잠정 spec 초안은 `sia_session7_output.md` §11.1 참조

### 🟡 Pending (구현 블로커 아님)

- **A-4: RECOGNITION 결합 출력화** — 도윤 fixture 에서 RECOGNITION 단독 자연스러움 확인. 필수 아닐 가능성. 별도 페르소나 로플레이 검증 후 결정
- **B 항목 잔여:** So-what 위기 / 부정적 해석 / 조언 요구
- **C 항목:** 진단 이후 결과물 레이어 (₩49,000 full report 와 대화 관계) / 오프닝 전 화면 흐름 (피드 링크 입력 → 분석 로딩)

### 🔴 후속 작업 (별도)

- **세션 #4 v2 / 세션 #6 v2 / 세션 #5 v2 의 B2B talent pool 관련 언급 전수 점검 + 정리** — 본 세션 결정 (talent pool 영구 삭제) 후속

---

## 로드맵

### 단기 (세션 #8)

후보 (택 1-2):
- talent pool 삭제 후속 정리 (세션 #4/5/6 v2 전수 점검)
- A-17 가격 응대 (CTO 결정 후)
- 페르소나 다양화 검증 (준호 / 지은 / 만재 archetype 으로 본 세션 신규 룰 재검증)
- B 항목 잔여
- C 항목 (진단 이후 결과물 레이어 or 오프닝 전 화면 흐름)

### 중기 (Phase H = Claude Code 구현)

현 v3 + 세션 #7 patch 기준으로 착수 가능. 생성될 파일 (세션 #7 반영):

```
sia/
├── state.py                        # 14 타입 enum + ConversationState
├── decide.py                       # decide_next_message 
│                                   #   (세션 #7: detect_eval_request, detect_generalization,
│                                   #    detect_self_pr, detect_user_disclaimer 신설,
│                                   #    C6 vs RANGE_REAFFIRM 분기)
├── validator.py                    # 전체 패치 통합 + 세션 #7 (check_haiku_naturalness, C6 / C7 검증)
├── hardcoded.py                    # pick_variant + 44 문구 (세션 #7: RANGE_REAFFIRM 5변형 추가)
├── templates/
│   └── hardcoded.yaml              # RANGE_REAFFIRM 포함
├── prompts/
│   └── haiku/
│       ├── base.jinja              # 세션 #7: A-2 + A-14 보강
│       ├── observation.jinja       # is_first_turn 분기 + 세션 #7: A-12 + A-15 + A-16 self-check + A-13 prefix
│       ├── probe.jinja             # 세션 #7: A-12 + A-15 + A-16 self-check
│       ├── extraction.jinja        # 세션 #7: A-12 + A-15 + A-16 self-check
│       ├── empathy_mirror.jinja    # 세션 #7: is_combined 플래그 + next_combined_type 분기
│       ├── recognition.jinja       # 세션 #7: A-12 + A-15 + A-16 self-check
│       ├── confrontation.jinja     # 세션 #7: C6 / C7 블록 추가, A-13 prefix 가이드
│       └── diagnosis.jinja
├── haiku_client.py                 # API wrapper, fallback 3회 실패
└── tests/
    ├── test_validator.py
    ├── test_hardcoded.py
    └── fixtures/
        ├── sample_2_manjae.yaml
        ├── sample_3_jieun.yaml
        ├── sample_4_junho.yaml
        ├── sample_5_seoyeon.yaml   # 세션 #7 신규
        └── sample_6_doyun.yaml     # 세션 #7 신규
```

### 장기 (Phase H 이후)

**500회 실사용자 페르소나 실험 (창업자 로드맵):**
- Phase H 완료 후 실시스템 대상 대규모 검증
- 페르소나 구성 권장: 협조 40% / 단답/이탈 30% / 적대 10% / 과몰입 5% / 엣지 15%
- **세션 #7 추가: 자기평가 변동형 + 자기 PR 과잉형 페르소나 추가 검증**
- 발견되는 실패 모드는 세션 #8+ 에서 spec 반영

---

## CTO 에게

- 프론트엔드 작업은 v3 4종 (세션 #4/5/6 v2 + 세션 #7) 기준
- **세션 #4 v2 메인 spec + 세션 #7 패치 매니페스트 (`sia_session7_output.md` §10) 같이 읽어야 완전체**
- 세션 #6 v2 도 마찬가지로 세션 #7 패치 적용 필요 (RANGE_DISCLOSURE 모드 분기, decide_next_message 보강 등)
- **사업 모델 변경 사항 1건: B2B talent pool 영구 삭제.** 데이터 모델 / API 설계 영향. 본인과 사업 방향 재검토 필요
- 보류 항목 1건 (A-17 가격 응대) — 결정해야 spec 화 가능. 결정 전까지 임시 fallback = RANGE_REAFFIRM
- 구현 중 엣지 케이스 마주치면 창업자 바로 문의. 추측 구현 금지
- Phase H (백엔드 구현) 는 창업자 주도. 프론트는 API 계약만 확정되면 먼저 진행 가능

---

## 창업자에게 (본인)

세션 #8 진입 시 다룰 후보 (`sia_session7_output.md` §14, §18 참조):
- talent pool 삭제 후속 정리 (긴급, 정합성 이슈)
- A-17 가격 응대 (CTO 결정 후)
- A-4 RECOGNITION 결합화 (선택)
- 페르소나 다양화 검증 (단답형 / 자기 축소형 / 외부 권위 회귀형 archetype)
- B 항목 잔여 / C 항목

**Phase H 직진 vs 세션 #8 경유 판단:**
- 세션 #7 까지 완료된 spec 으로 Phase H 충분히 착수 가능
- 단 talent pool 삭제 후속 정리는 Phase H 진입 전 권장 (코드 일관성)
- A-17 은 운영 데이터 쌓이면서 결정해도 무방 (임시 fallback 가능)

**본 세션의 본질적 발견 (세션 #7 §18 인용):**
> spec 룰은 "사변적 안전장치" 가 아니라 "실측 위반 → 본인 지적 → 정의 확정" 의 사후적 산물.
> Phase H 운영 단계도 같은 패턴으로 spec 보강하는 게 권장.

500회 실험을 기다리지 말고, Phase H 운영 시 매 위반 케이스마다 spec 보강 패턴을 가져갈 것.
