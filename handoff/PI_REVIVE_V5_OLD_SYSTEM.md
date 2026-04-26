# SIGAK 옛 PI 시스템 풀 부활 — 명령서 v5 (FINAL)

**버전:** v5 FINAL (옛 system production 활성 확인 + 본인 BETA 결정 반영)
**작성:** 2026-04-26
**예상 분량:** 6-11h
**전제:** 신 PI v3 폐기 (본인 자기 전 잠금 결정 정합) + 옛 SIGAK_V3 시스템 풀 사용 + BETA 5/15 까지 무료 공개

---

## 0. 배경

본인 자기 전 commit `653c5f5` = "PI v3 잠금 — product 본질 검증 미완 (5천원 가치 미달)". 본 인스턴스가 이전 turn 에서 잘못 판단해서 503 gate 풀어 신 PI v3 활성. 본인 의도 X.

본인 본 깡통 = PIv3Screen 의 inline JSON dump (metrics·0개 / face_type·달걀형 / ...).

**진짜 의도** = 옛 SIGAK_V3 시스템 (production 풀 활성, main.py + pipeline/* + /report/[id]/full + 옛 frontend 컴포넌트) **그대로 사용** + **신 PI v3 폐기**.

옛 system 검증 완료:
- main.py 2,435 lines + pipeline/ 13,186 lines = 풀 활성
- `/api/v1/submit`, `/api/v1/photos/{uid}`, `/api/v1/analyze/{uid}`, `/api/v1/report/{id}` = production endpoints
- frontend `lib/api/client.ts` = 위 API client 풀 활성 (submitPhotos, uploadPhotos, analyze, getReport, getReportServerSide, getMyReports)
- `app/report/[id]/page.tsx` (overview) + `app/report/[id]/full/page.tsx` (풀 viewer) = production
- `pipeline/report_formatter.py:format_report_for_frontend` = backend → frontend ReportData 변환 풀 작동

---

## 1. 결정사항 (본인 답)

| 영역 | 결정 |
|---|---|
| 옛 system 부활 방식 | 풀 사용 (frontend 만 wiring 변경 / backend BETA 우회) |
| 결제 path | BETA 5/15 까지 무료 공개. 5/15 이후 본인 재결정. |
| 신 PI v3 처리 | 폐기 또는 503 maintenance 영구. /pi/* route 비활성. |
| 신 token 시스템 | Sia / Verdict / Best Shot / Aspiration = 보존 (토큰 유지). PI 만 BETA 무료. |

---

## 2. 작업 단위 분해 (7개)

### 작업 A — backend BETA 우회 분기 (main.py)

**파일:** `sigak/main.py:1085 get_report` (`/api/v1/report/{id}` 핸들러)
**분량:** 0.5h

**핵심:** access_level 강제 "full" 처리 + paywall 응답 미포함.

**Before (line 1136-1162):**
```python
access = report.get("access_level", "standard")
response["access_level"] = access
...
if access != "full":
    response["paywall"] = {...}
    response["payment_account"] = PAYMENT_INFO
```

**After:**
```python
from config import get_settings
from datetime import date
def _is_pi_beta_free() -> bool:
    try:
        return date.today() < date.fromisoformat(get_settings().beta_free_until)
    except Exception:
        return False

# get_report 내:
if _is_pi_beta_free():
    access = "full"  # BETA 무료 = paywall 우회
else:
    access = report.get("access_level", "standard")
response["access_level"] = access
...
if access != "full":  # BETA 후 = 정상 paywall
    response["paywall"] = {...}
```

**의존성:** `config.beta_free_until` (PI-REVIVE 1차 commit `bebf996` 에 추가됨)

---

### 작업 B — frontend `/vision` PIBlock link 변경

**파일:** `sigak-web/components/sigak/vision-view.tsx`
**분량:** 1-2h

**핵심 변경:**

**1. PIUnlockedBlock 의 `<Link href={\`/pi/${reportId}\`}>` → `<Link href={\`/report/${reportId}/full\`}>`**

**2. "사진 다시 올려서 새로 받기" link → 옛 system 사진 업로드 entry**
- 옛 system entry = `/sia` (본인 자기 전 결정) 또는 별도 page
- 단순 path: 본인 결정 시 `/sia` 처음부터 또는 `/onboarding/photo`

**3. PIPendingBlock 의 "먼저 미리보기 (무료)" Link `/pi/preview` → `/sia` 종료 진입 흐름**
- has_baseline 의미 변경 = 옛 system 의 `user.status == "pending_payment"` 여부

**4. `getPIv3Status()` 호출 폐기 → `getMyReports(userId)` 호출**
- 신 v3 status (has_baseline / has_current_report) → 옛 my reports list (있으면 PIUnlockedBlock 노출)

**고려:**
- 옛 system 의 user_id 기반 흐름 vs 신 system 의 vault user_id 호환성
- frontend `lib/api/client.ts` 의 `getMyReports(userId)` 함수 활용

---

### 작업 C — `/sia` 종료 → 옛 system entry wiring

**파일:** `sigak-web/app/sia/...` (Sia 대화 종료 page) + `lib/api/client.ts` 호환성
**분량:** 1-2h

**핵심:** Sia 대화 완료 → 사진 업로드 → `/api/v1/submit` 호출 → /report/{id} redirect

**옵션 A — Sia 종료 후 사진 업로드 page 별도:**
- `/sia` 종료 → `/photo-upload` 새 page → `/api/v1/submit` → `/report/{report_id}` redirect

**옵션 B — Sia 대화 안에 사진 업로드 통합:**
- 본인이 자기 전 작업한 vault baseline 사진 활용 + Sia 대화 완료 시 `/api/v1/submit` 호출 + report 생성 + `/report/{id}` redirect

**의존성:** routes/sia.py 의 Sia session 종료 hook + 옛 main.py:_run_analysis_pipeline 호출

**본인 결정 영역:** 옵션 A vs B. 본 명령서 작성 후 결정.

---

### 작업 D — `/pi/*` 라우트 폐기 또는 redirect

**파일들:**
- `sigak-web/app/pi/upload/page.tsx`
- `sigak-web/app/pi/preview/page.tsx`
- `sigak-web/app/pi/[id]/page.tsx`
- `sigak-web/components/pi-v3/PIv3Screen.tsx` (폐기)
- `sigak-web/components/pi-v3/PiMaintenance.tsx` (보존, 재잠금 시)

**분량:** 0.5-1h

**옵션 A:** 폐기 (파일 삭제)
**옵션 B:** redirect (각 page = `redirect("/sia")` 또는 `/report/{id}`)

**권장:** B (안전, 옛 link 들어와도 정상 redirect).

---

### 작업 E — backend `routes/pi.py` v3 영역 비활성

**파일:** `sigak/routes/pi.py:73-77` `router_v3`
**분량:** 0.5h

**핵심:** v3 503 gate 다시 활성 (PI-REVIVE 1차 commit 에서 풀었던 것 되돌림).

**Before (현재):**
```python
router_v3 = APIRouter(
    prefix="/api/v3/pi",
    tags=["pi-v3"],
)
```

**After:**
```python
router_v3 = APIRouter(
    prefix="/api/v3/pi",
    tags=["pi-v3"],
    dependencies=[Depends(_pi_v3_maintenance_gate)],
)
```

**근데 메시지 변경:** 5천원 가치 미달 → "PI 시스템 갱신 중. 옛 SIGAK_V3 system 사용 중."

**또는 라우트 자체 등록 X:** `main.py` 또는 `app.py` 에서 `app.include_router(router_v3)` 호출 자체 제거. 깔끔.

---

### 작업 F — frontend 신 PI 관련 dead code 정리

**파일들:**
- `sigak-web/lib/api/pi.ts` = 신 v3 API client (deletePIv3 / unlockPIv3 / etc) 폐기
- `sigak-web/components/sigak/vision-view.tsx` = `getPIv3Status` import / state 등 폐기

**분량:** 0.5h

**대안:** 그대로 두되 호출 0건 보장 (작업 D + E 완료 시 자동).

---

### 작업 G — LIVE smoke test (옛 path 풀 진행)

**분량:** 2-3h

**체크리스트:**
- [ ] 새 user 가입 / Sia 대화 진입
- [ ] Sia 종료 → 사진 업로드 → `/api/v1/submit` 호출 → user/order 생성
- [ ] `/api/v1/analyze/{uid}` 호출 → `_run_analysis_pipeline` 실행 → DB pi_reports 저장
- [ ] `/report/{report_id}` overview 진입 → ReportNav + OverviewContent
- [ ] BETA 기간 = `access_level="full"` 응답 + paywall 미노출
- [ ] `/report/{report_id}/full` 진입 → ReportViewer + 9 sections 풀 (face-structure / skin-analysis / hair-recommendation / overlay-compare / etc)
- [ ] hair catalog 34장 이미지 정상 매칭
- [ ] overlay before/after slider 작동
- [ ] 모바일 viewport 100dvh
- [ ] 본인이 본 PIv3Screen 깡통 화면 = **0건** (신 v3 진입 X 검증)

---

## 3. Dependency 그래프

```
A (backend BETA, 0.5h) ──┐
                          │
E (v3 503 gate, 0.5h) ────┤
                          │
B (frontend vision, 1-2h)─┼──► G (smoke test, 2-3h) ──► LAUNCH
                          │
C (/sia → 옛 entry, 1-2h)─┤
                          │
D (/pi/* redirect, 0.5h) ─┤
                          │
F (dead code 정리, 0.5h) ──┘
```

A / E = 독립 병렬. B / C / D / F = 독립 병렬. G = 모두 후.

---

## 4. 보존 영역 (손대지 X)

- 신 token 시스템 (services/tokens.py / routes/tokens.py)
- Sia 대화 (routes/sia.py / services/sia_*.py)
- Verdict v2 (routes/verdict_v2.py / services/verdict_v2.py)
- Best Shot (routes/best_shot.py / services/best_shot_*.py)
- Aspiration (routes/aspiration.py / services/aspiration_*.py)
- 신 vault (services/user_data_vault.py / coordinate_system.py / user_taste_profile.py / knowledge_matcher.py / sia_writer.py)
- DB schema (pi_reports / users.user_history JSONB / aspiration_analyses / verdict_sessions / etc)
- 옛 main.py / pipeline/ 코드 (변경 0)

---

## 5. 파괴 영역 (정리)

- routes/pi.py 의 v3 영역 (503 gate 영구 또는 라우트 등록 X)
- /pi/* page.tsx (폐기 또는 redirect)
- components/pi-v3/PIv3Screen.tsx (폐기)
- 신 v3 schema (schemas/pi_report.py 의 PIv3* / PiContent / PiPreview / FaceStructureContent / etc) — 옛 backend 와 무관, dead code 잔존 가능

---

## 6. 본인 결정 (확정)

1. **`/sia` 종료 후 옛 system 진입 흐름** (작업 C):
   ✅ **별도 사진 업로드 page** (`/photo-upload`)
   - `/sia` 종료 → `/photo-upload` 새 page → `/api/v1/submit` (사진 + interview JSON) → `/report/{report_id}` redirect
   - 단계 명확. 옛 SIGAK_V3 흐름 정합.
   - sigak-web/app/photo-upload/page.tsx 신규 생성 필요 (사진 multipart picker + submitPhotos 호출)

2. **5/15 이후 결제 path**:
   ✅ **5/15 이후 다시 결정** (BETA 데이터 보고 판단)
   - 본 명령서 = BETA 분기만 명시
   - 5/15 후 = 옛 ₩29K vs 신 token 50 vs 절충 = 본인이 BETA user 데이터 + 마케터 의견 보고 판단

---

## 7. 새 인스턴스 분기 절차

본인 영역:
1. 위 결정 1, 2 답
2. 본 명령서 검수
3. 새 cmd → claude → /effort max → 본 명령서 복붙

새 인스턴스 첫 액션:
1. handoff/PI_REVIVE_V5_OLD_SYSTEM.md read
2. 작업 A → E (병렬 가능, ~1h)
3. 작업 B / C / D / F (병렬, ~3-5h)
4. 작업 G smoke test (~2-3h)
5. commit + push + Railway 배포

---

## 8. Risk 요약

🟢 낮음:
- 옛 main.py + pipeline/* = production 검증
- 옛 frontend route + ReportViewer = production 검증
- BETA 우회 분기 = 단순 logic
- 본인이 옛 system 작동 확인됨

🟡 중간:
- `/sia` 종료 → 옛 entry wiring (본인 결정 영역)
- 신 vault 의 user_id vs 옛 main.py 의 user_id 호환 검증
- 신 BETA env (`config.beta_free_until`) main.py 에서 import 가능 여부 검증

🔴 높음:
- 없음 (옛 system 풀 살아있음 = critical blocker 0)

---

## DONE

본 명령서 = Phase 5 (옛 system 풀 부활) wiring 인스턴스 분기용 입력.
**6-11h 안에 풀 launch 가능.** 본인 결정 1, 2 답 + 검수 통과 시 새 cmd 분기.
