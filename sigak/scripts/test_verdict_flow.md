# Verdict 플로우 테스트 (MVP v1.2 Phase C)

## 전제

- `20260421_v1_2_verdicts_llm_cache` 마이그레이션 적용됨
- 테스트 유저 `abcc2bea-e784-4d92-93ba-ce590c8f1b56` (또는 본인 USER_ID)
- 유저의 `onboarding_completed=TRUE` + `onboarding_data`에 9개 필수 필드
- `ANTHROPIC_API_KEY` Railway에 설정됨 (LLM #2 호출용)

## Step 0 — 마이그레이션 + JWT

```cmd
cd C:\Users\PC\Desktop\Sigak\sigak
set DATABASE_URL=postgresql://postgres:...@nozomi.proxy.rlwy.net:58732/railway
alembic upgrade head
```

환경변수 + JWT:
```cmd
set API=https://sigak-production.up.railway.app
set USER_ID=abcc2bea-e784-4d92-93ba-ce590c8f1b56
set ADMIN_KEY=<Railway ADMIN_KEY 값>

curl -X POST "%API%/api/v1/auth/dev-issue-jwt" -H "X-Admin-Key: %ADMIN_KEY%" -H "Content-Type: application/json" -d "{\"user_id\": \"%USER_ID%\"}"
REM 응답의 jwt 값 복사
set JWT=eyJ...
```

## Step 0.5 — 온보딩 완료 상태 확보

위 유저의 `onboarding_completed`가 false면 시나리오 4(거부)부터 시작. true로 만들려면 test_onboarding_flow.md 시나리오 1(Happy Path) 먼저 실행.

```cmd
curl "%API%/api/v1/onboarding/state" -H "Authorization: Bearer %JWT%"
REM onboarding_completed: true 확인
```

## Step 0.6 — 테스트용 사진 확보

얼굴이 찍힌 jpg/png 2장 이상. Windows cmd에서 multipart:
```cmd
curl -X POST "%API%/api/v1/verdicts" ^
  -H "Authorization: Bearer %JWT%" ^
  -F "files=@C:\Users\PC\Desktop\photo1.jpg" ^
  -F "files=@C:\Users\PC\Desktop\photo2.jpg" ^
  -F "files=@C:\Users\PC\Desktop\photo3.jpg"
```

(`^`는 cmd의 줄 이음 문자. PowerShell에서는 백틱 `` ` ``.)

---

## 시나리오 1 — Verdict 생성 (무료 티어)

### 1-A. 5장 사진으로 verdict 생성

5장 이상 사진 준비. 이름은 자유 (서버가 재명명).

```cmd
curl -X POST "%API%/api/v1/verdicts" ^
  -H "Authorization: Bearer %JWT%" ^
  -F "files=@C:\path\to\photo1.jpg" ^
  -F "files=@C:\path\to\photo2.jpg" ^
  -F "files=@C:\path\to\photo3.jpg" ^
  -F "files=@C:\path\to\photo4.jpg" ^
  -F "files=@C:\path\to\photo5.jpg"
```

기대 응답 구조:
```json
{
  "verdict_id": "vrd_xxx",
  "candidate_count": 5,
  "tiers": {
    "gold":   [{"photo_id":"p_aaa","score":0.84,"url":"/api/v1/uploads/<uid>/vrd_xxx_0.jpg"}],
    "silver": [
      {"photo_id":"p_bbb","score":0.73,"url":null},
      {"photo_id":"p_ccc","score":0.67,"url":null},
      {"photo_id":"p_ddd","score":0.61,"url":null}
    ],
    "bronze": [
      {"photo_id":"p_eee","score":0.55,"url":null}
    ]
  },
  "gold_reading": "구도와 표정의 균형이 좋아요. 내추럴에 잘 맞고요.",
  "blur_released": false,
  "pro_data": null
}
```

**핵심 확인**:
- `tiers.gold`는 1장, `url` 채워져 있음
- `tiers.silver`는 1~3장, 전부 `url: null`
- `tiers.bronze`는 나머지, 전부 `url: null`
- `gold_reading`은 placeholder 3종 중 하나 (한국어 2문장)
- `blur_released: false`, `pro_data: null`
- `verdict_id` 기록: `set VERDICT_ID=vrd_xxx`

### 1-B. GET으로 동일 verdict 재조회
```cmd
curl "%API%/api/v1/verdicts/%VERDICT_ID%" -H "Authorization: Bearer %JWT%"
```
기대: 위와 동일한 구조. 단 `gold_reading: ""`(GET은 ephemeral placeholder 재생성 안 함 — TODO 있음)

---

## 시나리오 2 — LLM #2 캐시 히트

### 2-A. 백엔드 로그 테일링 준비 (Railway dashboard)
Railway → Deployments → 최신 빌드 → View logs 열어두기

### 2-B. 첫 verdict (캐시 MISS 예상)
시나리오 1과 동일하게 POST.

로그에서 확인:
```
[LLM#2 cache MISS] user=abcc2bea-...
[LLM#1 cache MISS] user=abcc2bea-...
```

### 2-C. 두 번째 verdict (캐시 HIT 예상)
같은 유저로 다시 POST (새 verdict_id 생성되지만 LLM 캐시는 공유).

로그에서 확인:
```
[LLM#2 cache HIT] user=abcc2bea-...
[LLM#1 cache HIT] user=abcc2bea-...   ← winner가 같은 사람이면 HIT
```

또는 DB 직접 확인:
```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); r=e.connect().execute(sa.text('SELECT interview_interpretation_hash, updated_at FROM users WHERE id=:u LEFT JOIN face_interpretations f ON f.user_id=users.id'.replace('LEFT','INNER')), {'u': os.environ['USER_ID']}).first(); print(r)"
```

### 2-D. 캐시 무효화 확인 (onboarding 변경)
```cmd
curl -X POST "%API%/api/v1/onboarding/save-step" -H "Authorization: Bearer %JWT%" -H "Content-Type: application/json" -d "{\"step\":3,\"fields\":{\"desired_image\":\"새로운 이미지\"}}"

REM verdict 다시 생성
curl -X POST "%API%/api/v1/verdicts" -H "Authorization: Bearer %JWT%" -F "files=@photo1.jpg" -F "files=@photo2.jpg"
```
기대 로그: `[LLM#2 cache MISS]` (hash 바뀜)

---

## 시나리오 3 — Blur release

### 3-A. 사전 조건: 잔액 50 토큰 이상
테스트 환경이라 실제 Toss 결제 대신 DB로 직접 credit:
```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); c=e.connect(); c.execute(sa.text(\"INSERT INTO token_balances (user_id, balance) VALUES (:u, 100) ON CONFLICT (user_id) DO UPDATE SET balance = 100\"), {'u': os.environ['USER_ID']}); c.commit(); print('balance set to 100')"
```

### 3-B. 시나리오 1에서 받은 VERDICT_ID로 release-blur

```cmd
curl -X POST "%API%/api/v1/verdicts/%VERDICT_ID%/release-blur" ^
  -H "Authorization: Bearer %JWT%" ^
  -H "Content-Type: application/json" ^
  -d "{}"
```

기대:
```json
{
  "verdict_id": "vrd_xxx",
  "blur_released": true,
  "pro_data": {
    "silver_readings": [
      {"photo_id":"p_bbb","axis_delta":{"shape":0.12,"volume":-0.05,"age":0.2},"reason":"추구미 좌표와의 거리가 있어 후순위로 분류되었어요"},
      ...
    ],
    "bronze_readings": [...],
    "full_analysis": {
      "interpretation": "따뜻한 첫사랑 기반에 성숙도를 높인 방향",
      "reference_base": "따뜻한 첫사랑",
      "chugumi_target": {"shape":0.1,"volume":0.3,"age":-0.3},
      "action_spec": null,
      "trajectory_signal": null
    }
  },
  "balance_after": 50
}
```

### 3-C. 멱등성 확인
같은 curl 다시 실행 → 토큰 **차감 없음**, 동일 pro_data 반환, `balance_after: 50` 유지.

### 3-D. GET으로 해제 후 상태 확인
```cmd
curl "%API%/api/v1/verdicts/%VERDICT_ID%" -H "Authorization: Bearer %JWT%"
```
기대: `silver`/`bronze` 배열의 모든 `url` 필드가 **채워짐**. `blur_released:true`, `pro_data` 포함.

### 3-E. 잔액 재확인
```cmd
curl "%API%/api/v1/tokens/balance" -H "Authorization: Bearer %JWT%"
```
기대: `{"balance":50,...}`

### 3-F. 잔액 부족 케이스 (별도 verdict)
먼저 새 verdict 생성 (`VERDICT_ID_2`). 그리고 balance를 10으로:
```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); c=e.connect(); c.execute(sa.text('UPDATE token_balances SET balance = 10 WHERE user_id = :u'), {'u': os.environ['USER_ID']}); c.commit()"

curl -X POST "%API%/api/v1/verdicts/%VERDICT_ID_2%/release-blur" -H "Authorization: Bearer %JWT%" -H "Content-Type: application/json" -d "{}"
```
기대: `402 {"detail":"토큰이 부족합니다. 50토큰 필요, 현재 10"}`

---

## 시나리오 4 — Onboarding 미완료 verdict 거부

### 4-A. Reset + onboarding 클리어
```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); c=e.connect(); c.execute(sa.text('UPDATE users SET onboarding_data=NULL, onboarding_completed=FALSE WHERE id=:u'), {'u': os.environ['USER_ID']}); c.commit()"
```

### 4-B. verdict 시도
```cmd
curl -i -X POST "%API%/api/v1/verdicts" -H "Authorization: Bearer %JWT%" -F "files=@photo1.jpg" -F "files=@photo2.jpg"
```
기대: `409 {"detail":"onboarding을 먼저 완료해주세요"}`

### 4-C. onboarding_data는 있는데 completed=false
```cmd
curl -X POST "%API%/api/v1/onboarding/save-step" -H "Authorization: Bearer %JWT%" -H "Content-Type: application/json" -d "{\"step\":1,\"fields\":{\"height\":\"160_165\"}}"

curl -i -X POST "%API%/api/v1/verdicts" -H "Authorization: Bearer %JWT%" -F "files=@photo1.jpg" -F "files=@photo2.jpg"
```
기대: `409 {"detail":"onboarding을 먼저 완료해주세요"}` — `onboarding_data`는 있어도 `completed=false`면 거부

---

## DB 검증 쿼리

```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); rows=list(e.connect().execute(sa.text('SELECT id, candidate_count, blur_released, reasoning_unlocked FROM verdicts WHERE user_id=:u ORDER BY created_at DESC LIMIT 5'), {'u': os.environ['USER_ID']})); [print(r) for r in rows]"
```

```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); r=e.connect().execute(sa.text('SELECT features_hash, updated_at FROM face_interpretations WHERE user_id=:u'), {'u': os.environ['USER_ID']}).first(); print(r)"
```

```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); r=e.connect().execute(sa.text('SELECT interview_interpretation_hash, (interview_interpretation IS NOT NULL) as has_interp FROM users WHERE id=:u'), {'u': os.environ['USER_ID']}).first(); print(r)"
```

```cmd
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); rows=list(e.connect().execute(sa.text('SELECT kind, amount, balance_after, idempotency_key FROM token_transactions WHERE user_id=:u ORDER BY created_at DESC LIMIT 5'), {'u': os.environ['USER_ID']})); [print(r) for r in rows]"
```

---

## 알려진 제약 (MVP 범위 밖)

- `gold_reading`은 placeholder 3종 로테이션. 실제 LLM 호출 아님 (founder 소유)
- `pro_data.full_analysis.action_spec` / `trajectory_signal`은 null. 위와 동일 (founder 소유)
- `pro_data.silver_readings[*].reason`도 placeholder. 위와 동일
- GET /verdicts/{id}는 `gold_reading` 재생성 안 함 (빈 문자열 반환). persistence는 후속 작업
- URL이 "signed URL 1h expiry"가 아니라 일반 uploads 경로 — S3 migration은 refactor backlog
- `analyze_face`가 sync여서 async route의 이벤트 루프 블로킹. 동시성 낮은 MVP에서 문제 없음. refactor backlog #N으로 올림
