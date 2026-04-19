# 결제 플로우 테스트 스크립트

## 전제

- 백엔드가 Railway에 떠 있고 env 설정: `TOSS_SECRET_KEY`, `JWT_SECRET`, `ADMIN_KEY`
- 테스트할 유저가 DB에 존재 (카카오 로그인으로 생성된 UUID)
- 모든 보호 라우트는 `Authorization: Bearer <JWT>` 필수

## Step 0 — 환경변수 + JWT 발급

```bash
export API=https://sigak-production.up.railway.app
export USER_ID=<기존 DB의 유저 UUID>
export ADMIN_KEY=<Railway의 ADMIN_KEY 값>
```

**개발용 JWT 발급** (카카오 OAuth 건너뛰고 바로 JWT 받기):

```bash
JWT=$(curl -s -X POST "$API/api/v1/auth/dev-issue-jwt" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\"}" | python -c "import sys, json; print(json.load(sys.stdin)['jwt'])")
echo $JWT
```

Windows cmd:
```cmd
curl -X POST "%API%/api/v1/auth/dev-issue-jwt" -H "X-Admin-Key: %ADMIN_KEY%" -H "Content-Type: application/json" -d "{\"user_id\": \"%USER_ID%\"}"
REM 응답의 jwt 값 복사해서:
set JWT=eyJ...
```

**운영 경로**: 실제 카카오 로그인 후 `/auth/kakao/token` 응답의 `jwt` 필드 사용.

## 시나리오 1 — 정상 플로우 (purchase-intent → Toss SDK → confirm → 토큰 적립)

### 1-A. 본인 확인 + 잔액

```bash
curl -s "$API/api/v1/auth/me" -H "Authorization: Bearer $JWT"
# → {id, kakao_id, email, name, tier}

curl -s "$API/api/v1/tokens/balance" -H "Authorization: Bearer $JWT"
# → {"balance": 0, "updated_at": null}
```

### 1-B. 구매 의도 생성

```bash
curl -s -X POST "$API/api/v1/tokens/purchase-intent" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"pack_code": "starter"}'
```

예상:
```json
{
  "order_id": "pay_a1b2c3d4e5f6",
  "amount_krw": 10000,
  "tokens_granted": 100,
  "pg_order_id": "pay_a1b2c3d4e5f6",
  "pg_amount": 10000,
  "pg_order_name": "SIGAK Token Pack — Starter"
}
```

`order_id` / `pg_order_id` 기록.

### 1-C. Toss SDK 결제 (수동)

프론트 Toss SDK 또는 Toss [샌드박스](https://developers.tosspayments.com/sandbox)에서 `pg_order_id` + amount 사용해 결제. 성공 시 리다이렉트 URL에 `paymentKey` 포함됨.

### 1-D. 결제 승인 (백엔드)

```bash
export ORDER_ID=pay_a1b2c3d4e5f6
export PAYMENT_KEY=<Toss success에서 받은 paymentKey>

curl -s -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{\"payment_key\": \"$PAYMENT_KEY\", \"amount\": 10000}"
```

예상 성공:
```json
{"order_id": "pay_a1b2c3d4e5f6", "status": "paid", "balance_after": 100}
```

### 1-E. 잔액 재확인

```bash
curl -s "$API/api/v1/tokens/balance" -H "Authorization: Bearer $JWT"
# → {"balance": 100, "updated_at": "..."}
```

### 1-F. 멱등성 확인

1-D를 다시 실행 → `balance_after: 100` 유지. 주문이 이미 `paid`라 short-circuit.

---

## 시나리오 2 — 웹훅만 도착 (confirm 건너뛰기)

유저가 결제 성공 페이지 도달 전에 앱을 닫은 상황.

### 2-A. 구매 의도 생성

```bash
curl -s -X POST "$API/api/v1/tokens/purchase-intent" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"pack_code": "regular"}'
```

### 2-B. Toss 결제 (수동)

`paymentKey` 확보.

### 2-C. 웹훅 시뮬레이션

```bash
curl -s -X POST "$API/payments/webhook" \
  -H "Content-Type: application/json" \
  -d "{\"eventType\": \"PAYMENT_STATUS_CHANGED\", \"data\": {\"paymentKey\": \"$PAYMENT_KEY\"}}"
```

(웹훅은 JWT 불필요 — Toss 재조회가 인증 역할)

내부 동작:
1. `paymentKey` 추출
2. `get_payment($PAYMENT_KEY)` — 우리 secret key로 Toss 재조회
3. Toss 응답의 `orderId`로 `payment_orders` lookup
4. `status=DONE` → 주문 paid + `credit:{order_id}` 키로 토큰 적립

### 2-D. 잔액 확인

```bash
curl -s "$API/api/v1/tokens/balance" -H "Authorization: Bearer $JWT"
# → {"balance": 280}  (시나리오 1 돌렸으면 380)
```

### 2-E. 뒤늦은 confirm (경쟁 상태 검증)

```bash
curl -s -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{\"payment_key\": \"$PAYMENT_KEY\", \"amount\": 25000}"
```

주문이 이미 paid → idempotency 단축 → `balance_after: 280` 그대로. **중복 없음**.

---

## 보안 검증 케이스

### JWT 없이 호출
```bash
curl -i "$API/api/v1/tokens/balance"
```
예상: `401 {"detail":"인증이 필요합니다"}`

### 유효하지 않은 JWT
```bash
curl -i "$API/api/v1/tokens/balance" -H "Authorization: Bearer invalid.jwt.here"
```
예상: `401 {"detail":"유효하지 않은 토큰입니다"}`

### 타 유저 주문 접근
user_A의 JWT로 user_B의 order_id에 confirm:
```bash
curl -i -X POST "$API/api/v1/payments/confirm/$USER_B_ORDER_ID" \
  -H "Authorization: Bearer $USER_A_JWT" \
  -H "Content-Type: application/json" \
  -d "{\"payment_key\": \"...\", \"amount\": 10000}"
```
예상: `403 {"detail":"본인 주문이 아닙니다"}`

### 금액 변조 방어
```bash
curl -i -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"payment_key": "fake", "amount": 5000}'
```
예상: `400 {"detail":"결제 금액이 일치하지 않습니다"}` — Toss 호출 전 차단.

### fake 웹훅 (시그니처 없는 웹훅 방어 증명)
```bash
curl -i -X POST "$API/payments/webhook" \
  -H "Content-Type: application/json" \
  -d '{"data": {"paymentKey": "fake_key_xxx"}}'
```
예상: `200 {"ok": true}` — DB 변화 **없음**. get_payment가 Toss에서 NOT_FOUND로 막음.

### ADMIN_KEY 없이 dev-issue-jwt
```bash
curl -i -X POST "$API/api/v1/auth/dev-issue-jwt" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\"}"
```
예상: `403 {"detail":"invalid admin key"}`

---

## DB 정합성 검증

```bash
python -c "
import os, sqlalchemy as sa
e = sa.create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    for row in c.execute(sa.text('''
        SELECT po.id, po.status, po.tokens_granted, po.pg_payment_key,
               tb.balance, tt.kind, tt.amount, tt.idempotency_key
        FROM payment_orders po
        LEFT JOIN token_balances tb ON tb.user_id = po.user_id
        LEFT JOIN token_transactions tt ON tt.reference_id = po.id
        WHERE po.user_id = :uid
        ORDER BY po.created_at DESC
    '''), {'uid': os.environ['USER_ID']}):
        print(row)
"
```

**정합성 규칙**:
- `payment_orders.status='paid'` 각 row마다 정확히 1개의 `token_transactions` (`kind='purchase'`, `idempotency_key='credit:{order_id}'`)
- `token_balances.balance` = 유저의 모든 `token_transactions.amount` 합
- `pending`/`failed` 주문은 `token_transactions` row 없음
