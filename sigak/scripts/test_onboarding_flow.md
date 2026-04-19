# 온보딩 플로우 테스트 (MVP v1.2)

## 전제

- Railway 배포 완료 후 실행
- 기존 user 1명 DB에 존재 (카카오 로그인으로 생성된 UUID)
- `JWT_SECRET`, `ADMIN_KEY`가 Railway에 설정되어 있음

## Step 0 — 환경변수 + JWT 발급

```bash
export API=https://sigak-production.up.railway.app
export USER_ID=<기존 DB의 유저 UUID>
export ADMIN_KEY=<Railway의 ADMIN_KEY 값>
export DATABASE_URL=<Railway의 DATABASE_URL 값 — 직접 DB 검증용>

JWT=$(curl -s -X POST "$API/api/v1/auth/dev-issue-jwt" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\"}" | python -c "import sys, json; print(json.load(sys.stdin)['jwt'])")
echo "JWT issued: ${JWT:0:30}..."
```

Windows cmd:
```cmd
set API=https://sigak-production.up.railway.app
set USER_ID=<기존 DB의 유저 UUID>
set ADMIN_KEY=<Railway의 ADMIN_KEY 값>
curl -X POST "%API%/api/v1/auth/dev-issue-jwt" -H "X-Admin-Key: %ADMIN_KEY%" -H "Content-Type: application/json" -d "{\"user_id\": \"%USER_ID%\"}"
REM 응답에서 jwt 값 복사
set JWT=eyJ...
```

## 공통 Reset 헬퍼

각 시나리오 시작 전에 DB 상태 초기화 (엔드포인트 `/reset`은 `onboarding_data`를 남겨서, 테스트 격리 위해 SQL로 NULL 처리):

```bash
python -c "
import os, sqlalchemy as sa
e = sa.create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    c.execute(sa.text('UPDATE users SET onboarding_data=NULL, onboarding_completed=FALSE WHERE id=:uid'), {'uid': os.environ['USER_ID']})
    c.commit()
print('reset OK')
"
```

## 시나리오 1 — Happy Path (step 1→2→3→4 → completed=true)

### Setup
```bash
# 위 Reset 헬퍼 실행
```

### 1-A. Step 1 저장 (체형)
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":1,"fields":{"height":"160_165","weight":"50_55","shoulder_width":"medium","neck_length":"medium"}}'
```
기대:
```json
{"onboarding_data":{"height":"160_165","weight":"50_55","shoulder_width":"medium","neck_length":"medium"},"completed":false}
```

### 1-B. Step 2 저장 (얼굴)
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":2,"fields":{"face_concerns":"wide_face,square_jaw"}}'
```
기대: `onboarding_data`에 step 1+2 필드 병합됨, `completed:false`

### 1-C. Step 3 저장 (추구미)
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":3,"fields":{"style_image_keywords":"chic,modern,elegant","desired_image":"뉴진스 같은데 좀 더 성숙","makeup_level":"basic"}}'
```
기대: `onboarding_data`에 step 1+2+3 필드 병합, `completed:false`

### 1-D. Step 4 저장 (자기인식) → **자동 완료**
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":4,"fields":{"self_perception":"차분하다는 말을 자주 들어요"}}'
```
기대:
```json
{"onboarding_data":{...9개 필수 필드 모두...},"completed":true}
```

### 1-E. state 재확인
```bash
curl -s "$API/api/v1/onboarding/state" -H "Authorization: Bearer $JWT"
```
기대:
```json
{"onboarding_completed":true,"onboarding_data":{...},"next_step":null}
```

---

## 시나리오 2 — Resume (step 2까지 → next_step=3)

### Setup: Reset 헬퍼 실행

### 2-A. Step 1 저장
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":1,"fields":{"height":"160_165","weight":"50_55","shoulder_width":"medium","neck_length":"medium"}}'
```

### 2-B. Step 2 저장
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":2,"fields":{"face_concerns":"wide_face"}}'
```

### 2-C. GET /state → next_step 확인
```bash
curl -s "$API/api/v1/onboarding/state" -H "Authorization: Bearer $JWT"
```
기대:
```json
{
  "onboarding_completed": false,
  "onboarding_data": {
    "height":"160_165","weight":"50_55","shoulder_width":"medium","neck_length":"medium",
    "face_concerns":"wide_face"
  },
  "next_step": 3
}
```

### 2-D. 엣지: step 4만 먼저 저장 (1~3 건너뛰기)
```bash
# Reset
python -c "import os, sqlalchemy as sa; e=sa.create_engine(os.environ['DATABASE_URL']); c=e.connect(); c.execute(sa.text('UPDATE users SET onboarding_data=NULL, onboarding_completed=FALSE WHERE id=:uid'), {'uid': os.environ['USER_ID']}); c.commit()"

# Step 4 만 저장 (필수 9개 중 self_perception만 있음)
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":4,"fields":{"self_perception":"차분해요"}}'
# 기대: completed=false (8개 필드 빠짐)

# next_step은 1 (첫 번째 빠진 필드 height가 step 1)
curl -s "$API/api/v1/onboarding/state" -H "Authorization: Bearer $JWT"
# 기대: next_step=1
```

---

## 시나리오 3 — Merge 검증 (같은 step 다른 필드 재저장)

### Setup: Reset 헬퍼 실행

### 3-A. Step 3의 일부 필드만 저장
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":3,"fields":{"desired_image":"첫번째 이미지","makeup_level":"basic"}}'
```
기대: `onboarding_data:{"desired_image":"첫번째 이미지","makeup_level":"basic"}`

### 3-B. 같은 Step 3의 다른 필드 저장
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":3,"fields":{"style_image_keywords":"chic,modern","reference_celebs":"카리나"}}'
```
기대:
```json
{"onboarding_data":{"desired_image":"첫번째 이미지","makeup_level":"basic","style_image_keywords":"chic,modern","reference_celebs":"카리나"},"completed":false}
```
**핵심 확인**: `desired_image`와 `makeup_level`이 **유지**되고 새 필드가 **추가**됨.

### 3-C. 기존 필드 덮어쓰기 (같은 key 다른 value)
```bash
curl -s -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":3,"fields":{"desired_image":"수정된 이미지"}}'
```
기대: `desired_image`는 `"수정된 이미지"`로 교체, 나머지는 유지.

---

## DB 직접 검증

```bash
python -c "
import os, sqlalchemy as sa
e = sa.create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    row = c.execute(sa.text(
        'SELECT onboarding_completed, onboarding_data FROM users WHERE id=:uid'
    ), {'uid': os.environ['USER_ID']}).first()
    print('completed:', row.onboarding_completed)
    print('data:', row.onboarding_data)
"
```

---

## 보안 검증

### JWT 없이 호출
```bash
curl -i "$API/api/v1/onboarding/state"
# 기대: 401 {"detail":"인증이 필요합니다"}
```

### 잘못된 step 값
```bash
curl -i -X POST "$API/api/v1/onboarding/save-step" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"step":5,"fields":{}}'
# 기대: 422 Unprocessable Entity (Pydantic Literal 검증 실패)
```

### reset → onboarding_data 유지 확인
시나리오 1 실행으로 `completed=true` 상태 만들고:
```bash
curl -s -X POST "$API/api/v1/onboarding/reset" -H "Authorization: Bearer $JWT"
# 기대: {"onboarding_completed":false}

curl -s "$API/api/v1/onboarding/state" -H "Authorization: Bearer $JWT"
# 기대: onboarding_data는 유지 (pre-fill용), onboarding_completed:false
```
