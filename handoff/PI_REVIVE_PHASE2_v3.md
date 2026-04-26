# SIGAK 옛 PI 무료 부활 — Phase 2 명령서 v4 (FINAL, 실 분량 반영)

**버전:** v4 FINAL (routes/pi.py 풀 read + 본인 직감 반영)
**작성:** 2026-04-26
**예상 분량:** **1.5-2h** (정찰 추정 8-12h → 실측 반영으로 -85% 단축)
**전제:** 외부 데드라인 협상 결과 무관 = 24h 안 풀 마진

---

## 0. 핵심 진단 (정찰 추정 vs 실 코드 read)

| 항목 | 정찰 추정 | 실 코드 (routes/pi.py 풀 read) |
|---|---|---|
| v1 엔진 위치 | main.py:880-1043 (잘못) | services/pi_engine.py::generate_pi_report_v1 |
| v1 라우트 작동 | stub 만 | v3 라우트가 이미 v1 호출 (line 624) |
| 9 컴포넌트 변환 | 신규 50-80줄 필요 | **이미 작성** (`_compose_v3_sections_from_v1_components`) |
| v3 차단 | router 입구 503 dependency 1줄 | 동일 |
| 진짜 차단 | v1 stub | **v3 503 gate 1줄만** |
| 분량 추정 | 8-12h | **1.5-2h** |

**핵심:** 옛 PI = v3 라우트 안에 살아있음. v3 503 gate 1줄만 풀면 그대로 작동.

---

## 1. 작업 단위 (총 4개, ~20-30줄)

### 작업 1 — v3 503 gate 해제

**파일:** `sigak/routes/pi.py`
**라인:** 73-77
**분량:** 1줄 변경

**Before:**
```python
router_v3 = APIRouter(
    prefix="/api/v3/pi",
    tags=["pi-v3"],
    dependencies=[Depends(_pi_v3_maintenance_gate)],
)
```

**After:**
```python
router_v3 = APIRouter(
    prefix="/api/v3/pi",
    tags=["pi-v3"],
)
```

**확인:** `_pi_v3_maintenance_gate` 함수는 그대로 둠 (재잠금 시 dependency 다시 추가 가능).

---

### 작업 2 — celeb_reference 폐기

**파일 1:** `sigak/schemas/pi_report.py` (PI_V3_SECTION_ORDER, PI_V3_PREVIEW_VISIBILITY)
**파일 2:** `sigak-web/components/report/section-renderer.tsx` (case "celeb_reference")
**파일 3:** `sigak/routes/pi.py:_compose_v3_sections_from_v1_components` (loop 영향 자동)
**분량:** 5-10줄

**핵심:**
1. `PI_V3_SECTION_ORDER` 에서 `"celeb_reference"` 제거 → 9 sections → 8 sections
2. `PI_V3_PREVIEW_VISIBILITY` 에서 `celeb_reference` 키 제거
3. section-renderer.tsx 의 `case "celeb_reference":` 제거 (또는 condition false)
4. 변환 layer (`_compose_v3_sections_from_v1_components`) = `PI_V3_SECTION_ORDER` 순회 = 자동 영향
5. 백엔드 PI-A `_assemble_9_components` = celeb_reference 제거 또는 그대로 두되 frontend 미노출

**선택 정리:**
- `components/report/sections/celeb-reference.tsx` = 파일 삭제 (75줄 shell 제거)
- `services/pi_engine.py` 의 PI-A v1 celeb_reference component 생성 = 그대로 두되 sections 노출 차단

---

### 작업 3 — BETA_FREE_UNTIL 분기

**파일:** `sigak/config.py` (env) + `sigak/routes/pi.py::_debit_v3_unlock` (line 838)
**분량:** 10-15줄

**config.py 추가:**
```python
BETA_FREE_UNTIL = os.getenv("BETA_FREE_UNTIL", "2026-05-15")
```

**routes/pi.py::_debit_v3_unlock 분기:**
```python
def _debit_v3_unlock(db, user_id: str) -> int:
    # BETA 무료 기간 — 토큰 차감 X
    from datetime import date
    beta_until = date.fromisoformat(config.BETA_FREE_UNTIL)
    if date.today() < beta_until:
        logger.info("[pi v3 unlock] BETA free user=%s (no charge)", user_id)
        return tokens_service.get_balance(db, user_id)

    # 기존 50 토큰 차감 로직 (line 840 이하)
    cost = PI_V3_UNLOCK_COST_TOKENS
    ...
```

**환불 path:** BETA 기간 = 차감 X = 환불 path 도 자동 무영향.

**measurement:** 본인 자기 전 메모 = "posthog 기존 인프라" 활용. 별도 작업 X.

---

### 작업 4 — 진단 깊이 부족 카피 정합

**파일:** 프론트 PI 진입 카피 (어디든 "5천원 가치 미달" 표현 노출 시)
**분량:** 5-10줄

**핵심:** v3 잠금 카피 ("시각이 본 당신은 더 정교한 형태로 곧 돌아옵니다") = 풀고 무료 BETA 카피로 교체. 또는 "베타 기간 무료 / 정식 출시 후 5,000원" 안내.

**선택:** PI 진입 화면 / 결제 페이지 / 토큰 차감 응답 메시지 정합.

---

## 2. Dependency 그래프

```
작업 1 (gate 해제, 1줄) ──┐
작업 2 (celeb 폐기, 5-10줄) ─┤
작업 3 (BETA env, 10-15줄) ──┼──► smoke test (1-1.5h) ──► LAUNCH
작업 4 (카피, 5-10줄) ──────┘
```

**모든 작업 = 독립. 병렬 가능. 순서 무관.**

---

## 3. 진행 룰

### 보존 영역 (손대지 X)

- 신 PI 5 인스턴스 산출물 (services/coordinate_system.py / user_taste_profile.py / user_data_vault.py / knowledge_matcher.py / sia_writer.py)
- v1 라우트 (`router` line 49) — stub 그대로 둠
- v2 라우트 (`router_v2` line 50) — 신 PI 영역
- `_pi_v3_maintenance_gate` 함수 자체 (재잠금 시 사용)
- generate_pi_report_v1 / PI-B / PI-C 본문
- 9 컴포넌트 변환 layer (`_compose_v3_sections_from_v1_components`)
- vault history_context 풀 build (`_build_history_context`)

### 작업 영역 (활성)

- routes/pi.py:73-77 (v3 router dependency 제거)
- schemas/pi_report.py (PI_V3_SECTION_ORDER / PI_V3_PREVIEW_VISIBILITY)
- routes/pi.py::_debit_v3_unlock (BETA 분기)
- config.py (BETA_FREE_UNTIL env)
- components/report/section-renderer.tsx (celeb_reference case 제거)
- 프론트 PI 진입 카피

### 폐기 영역

- components/report/sections/celeb-reference.tsx (파일 삭제)
- 503 maintenance UI 카피 (5천원 가치 미달 → BETA 무료)

### env / config 룰

- `BETA_FREE_UNTIL=2026-05-15` (Railway env 등록)
- `r2_public_base_url` 운영 검증
- `ANTHROPIC_API_KEY` 활성 확인
- 신규 deps 0건 (모두 기존)

---

## 4. LIVE smoke test 체크리스트

### 백엔드

- [ ] `/api/v3/pi/status` 200 응답 (503 X)
- [ ] `/api/v3/pi/upload` baseline 사진 업로드 → R2 영구
- [ ] `/api/v3/pi/preview` 토큰 차감 0 + 8 sections 응답
- [ ] `/api/v3/pi/unlock` BETA 기간 = 토큰 차감 0 + 8 sections full
- [ ] generate_pi_report_v1 8 컴포넌트 정상 반환 (celeb_reference 제외)
- [ ] PI-B / PI-C pipeline import / fallback 정상

### 프론트

- [ ] PI 진입 화면 = 503 maintenance UI 제거
- [ ] BETA 무료 카피 노출
- [ ] 8 sections 풀 render (cover / face_structure / skin_analysis / gap_analysis / coordinate_map / hair_recommendation / action_plan / type_reference)
- [ ] celeb_reference 노출 0건 (build 성공 + import 0건 검증)
- [ ] hair 34 catalog 이미지 정확 매칭
- [ ] overlay before/after slider 정상 (overlay_compare 컴포넌트)

### 모바일

- [ ] viewport 100dvh 정합
- [ ] overlay slider touchmove 작동
- [ ] hair-recommendation 4열 → 모바일 1-2열 적응

### 차단 검증

- [ ] v1 라우트 (`/api/v1/pi`) = 그대로 stub 작동 (touch X)
- [ ] v2 라우트 (`/api/v2/pi`) = 신 PI 영역 그대로 (touch X)
- [ ] VisionView PI 호출 차단 (commit ef42745) — 유지 또는 해제 본인 결정

---

## 5. 작업 순서 권장 (1.5-2h)

**0-30분: 코드 변경 (작업 1-4)**
1. routes/pi.py:73-77 `dependencies=[]` 제거 (작업 1, 1분)
2. schemas/pi_report.py PI_V3_SECTION_ORDER 에서 celeb_reference 제거 (작업 2-1, 5분)
3. section-renderer.tsx case 제거 + components/report/sections/celeb-reference.tsx 파일 삭제 (작업 2-2, 5분)
4. config.py BETA_FREE_UNTIL env + routes/pi.py::_debit_v3_unlock 분기 (작업 3, 15분)
5. 프론트 PI 진입 카피 정합 (작업 4, 5분)

**30분-1.5h: smoke test**
6. 본인 picomputer 사진 1장 + IG handle 풀 chain
7. /api/v3/pi/upload → preview → unlock 풀 통과
8. 8 sections frontend render
9. celeb_reference 노출 0건 검증
10. 모바일 viewport

**1.5-2h: Railway 배포 + 본인 검수**
11. Railway env (BETA_FREE_UNTIL) 등록
12. 배포 + LIVE 1회 검증
13. 본인 검수 + finalize

---

## 6. 새 인스턴스 분기 절차

본인 영역:
1. ~~외부 협상~~ — 1.5-2h 시나리오 = 24h 안에 풀 마진. 협상 미수신 시 그대로 진행
2. ~~celeb asset 큐레이션~~ — 폐기 결정 (반영)
3. 본 명령서 검수 (handoff/PI_REVIVE_PHASE2_v3.md)
4. 새 cmd → claude → /effort max → 본 명령서 복붙 → 작업 1-4 + smoke test 실행

새 인스턴스 첫 액션:
1. handoff/PI_REVIVE_PHASE2_v3.md read
2. 작업 1 → 2 → 3 → 4 (병렬 가능, 30분)
3. smoke test (1h)
4. Railway 배포 (30분)
5. 본인 검수 + PR

---

## 7. Risk 요약

🟢 낮음:
- v1 엔진 풀 작동 (commit 7b14e76, 3461줄, 36 tests)
- 9 컴포넌트 변환 layer 이미 작성
- v3 503 gate = 단 1줄 dependency 차단
- celeb 폐기 = critical blocker 제거
- 신규 deps 0건

🟡 중간:
- BETA_FREE_UNTIL date.today() vs datetime.now(timezone) 시간대 검증 (UTC / KST)
- celeb_reference 제거 시 _assemble_9_components 의 PI_V3_SECTION_ORDER 동기화 검증
- v3 unlock 환불 path 가 BETA 기간엔 호출 안 됨 (의도 정합 검증)

🔴 높음:
- 없음

---

## DONE

본 명령서 = Phase 2 wiring 인스턴스 분기용 입력 (FINAL, 실 분량 반영).
**1.5-2h 안에 풀 launch 가능.** 본인 검수 통과 시 새 cmd 분기.
