# 결제 플로우 테스트 스크립트

## 전제

- 백엔드가 Railway에 떠 있고, `TOSS_SECRET_KEY` 환경변수가 설정되어 있음
- 테스트할 유저가 DB에 존재 (카카오 로그인 완료 상태). 유저 ID 필요
- `X-User-Id` 헤더로 mock 인증 사용 (JWT 배선 전까지 임시)

**환경변수** (테스트 쉘에서):

```bash
export API=https://sigak-production.up.railway.app
export USER_ID=<기존 DB의 유저 UUID>
```

Windows cmd면:

```cmd
set API=https://sigak-production.up.railway.app
set USER_ID=<기존 DB의 유저 UUID>
```

## 시나리오 1 — 정상 플로우 (purchase-intent → Toss SDK → confirm → 토큰 적립)

### 1-A. 잔액 확인 (0이어야 정상)

```bash
curl -s "$API/api/v1/tokens/balance" \
  -H "X-User-Id: $USER_ID"
```

예상 응답:
```json
{"balance": 0, "updated_at": null}
```

### 1-B. 구매 의도 생성

```bash
curl -s -X POST "$API/api/v1/tokens/purchase-intent" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"pack_code": "starter"}'
```

예상 응답:
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

`order_id` / `pg_order_id`를 기록해둠.

### 1-C. Toss SDK 결제 (수동 단계)

프론트 Toss SDK에서:
```js
await tossPayments.requestPayment('카드', {
  amount: 10000,
  orderId: '<1-B에서 받은 pg_order_id>',
  orderName: 'SIGAK Token Pack — Starter',
  successUrl: '...',
  failUrl: '...',
});
```

테스트 카드: Toss 공식 문서의 [테스트 카드 번호](https://docs.tosspayments.com/resources/test) 사용.

성공 시 `successUrl`에 `paymentKey`, `orderId`, `amount` 쿼리파라미터로 리다이렉트됨.

**프론트 없이 테스트하려면**: Toss 공식 [테스트 위젯](https://developers.tosspayments.com/sandbox)에서 우리 `pg_order_id`를 입력해 `paymentKey`를 뽑아낼 수 있음. 또는 시나리오 3(웹훅만) 경로로 DB 측면 검증 우선.

### 1-D. 결제 승인 (백엔드)

`paymentKey`가 확보됐다고 가정:

```bash
export ORDER_ID=pay_a1b2c3d4e5f6
export PAYMENT_KEY=<Toss success redirect에서 받은 paymentKey>

curl -s -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"payment_key\": \"$PAYMENT_KEY\", \"amount\": 10000}"
```

예상 성공:
```json
{"order_id": "pay_a1b2c3d4e5f6", "status": "paid", "balance_after": 100}
```

예상 Toss 에러 (예: 잘못된 payment_key):
- HTTP 402
- `{"detail": "결제 승인 실패: UNAUTHORIZED_KEY"}` 형태

### 1-E. 잔액 재확인

```bash
curl -s "$API/api/v1/tokens/balance" -H "X-User-Id: $USER_ID"
```

예상:
```json
{"balance": 100, "updated_at": "2026-04-19T..."}
```

### 1-F. 멱등성 확인 (같은 confirm 재호출)

1-D를 다시 실행 → **토큰 중복 적립 없음**, `balance_after: 100` 유지. 주문 상태가 이미 `paid`라서 short-circuit 탐.

---

## 시나리오 2 — 웹훅만 도착한 경우 (confirm 건너뛰기)

사용자가 결제 성공 페이지에 도달하기 전에 닫아버렸거나 네트워크 끊긴 상황. Toss는 계속 웹훅 쏴서 우리 서버가 자체적으로 처리해야 함.

### 2-A. 구매 의도 생성 (시나리오 1과 동일)

```bash
curl -s -X POST "$API/api/v1/tokens/purchase-intent" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d '{"pack_code": "regular"}'
```

새 `order_id`, `pg_order_id` 기록.

### 2-B. Toss 결제 실행 (수동)

시나리오 1-C와 동일. `paymentKey` 확보.

### 2-C. confirm 호출 생략 — 웹훅 시뮬레이션

실제 운영에서는 Toss가 자동으로 웹훅 POST 보냄. 수동으로 시뮬레이션:

```bash
curl -s -X POST "$API/payments/webhook" \
  -H "Content-Type: application/json" \
  -d "{\"eventType\": \"PAYMENT_STATUS_CHANGED\", \"data\": {\"paymentKey\": \"$PAYMENT_KEY\"}}"
```

예상 응답: `{"ok": true}` (HTTP 200)

내부 동작:
1. `paymentKey` 추출
2. `services.payments.get_payment($PAYMENT_KEY)` 호출 (우리 secret key로 Toss 재조회)
3. Toss 응답의 `orderId`로 우리 `payment_orders` 레코드 lookup
4. Toss `status=DONE` 확인 → 주문 paid 처리 + `credit:{order_id}` 키로 토큰 적립

### 2-D. 잔액 확인

```bash
curl -s "$API/api/v1/tokens/balance" -H "X-User-Id: $USER_ID"
```

예상: 시나리오 1에서 받은 100 + 시나리오 2의 280 = `280` (시나리오 1 실행 안 했다면 280만).

### 2-E. confirm 후발 호출 (경쟁 상태 검증)

같은 주문에 대해 이미 웹훅이 처리했는데, 뒤늦게 유저가 success 페이지에 도달해서 confirm 호출:

```bash
curl -s -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"payment_key\": \"$PAYMENT_KEY\", \"amount\": 25000}"
```

예상: HTTP 200, `{"order_id": ..., "status": "paid", "balance_after": 280}` — 주문이 이미 paid라서 `credit_tokens`의 idempotency 체크가 기존 트랜잭션을 발견하고 기존 `balance_after` 그대로 반환. **중복 적립 없음**.

### 2-F. 역 순서 검증 (confirm 먼저, 웹훅 나중)

시나리오 1-D로 confirm 성공 후, 2-C처럼 웹훅 쏴도 동일 idempotency_key `credit:{order_id}`로 short-circuit. 상태 변화 없음.

---

## 데이터베이스 직접 검증

결제 없이도 테이블 구조가 맞는지, 락/제약이 걸리는지 확인할 수 있음.

```bash
python -c "
import os, sqlalchemy as sa
e = sa.create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    # 주문 + 트랜잭션 + 잔액 한번에
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

**예상되는 정합성 규칙**:
- `payment_orders.status = 'paid'` 인 row마다 정확히 1개의 `token_transactions` row (`kind='purchase'`, `idempotency_key='credit:{order_id}'`)
- `token_balances.balance` = 해당 유저의 모든 `token_transactions.amount` 합
- `pending` 주문은 `token_transactions` row 없음
- `failed` 주문도 `token_transactions` row 없음

---

## 실패 케이스 의도적 테스트

### 금액 변조 방어

1-B에서 `amount_krw: 10000` 받았는데, 1-D에서 `amount: 5000`으로 보냄:

```bash
curl -s -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "X-User-Id: $USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"payment_key\": \"fake\", \"amount\": 5000}"
```

예상: HTTP 400, `{"detail": "결제 금액이 일치하지 않습니다"}` — Toss 호출 전에 차단.

### 타 유저 주문 접근 방어

다른 user_id로 남의 order_id에 confirm 시도:

```bash
curl -s -X POST "$API/api/v1/payments/confirm/$ORDER_ID" \
  -H "X-User-Id: OTHER_USER" \
  ...
```

예상: HTTP 403, `{"detail": "본인 주문이 아닙니다"}`.

### fake 웹훅 방어

실제 Toss paymentKey 아닌 임의 문자열로 웹훅:

```bash
curl -s -X POST "$API/payments/webhook" \
  -H "Content-Type: application/json" \
  -d '{"data": {"paymentKey": "fake_key_xxx"}}'
```

예상:
- `get_payment` 호출 → Toss가 `NOT_FOUND_PAYMENT` 또는 `INVALID_REQUEST`로 거부
- 우리 서버: HTTP 200 `{"ok": true}` 리턴하되 DB는 변화 없음 (로그에만 WARNING)

이 동작이 **시그니처 없는 웹훅의 인증 메커니즘**을 증명함 — fake 이벤트는 Toss API 재조회 단계에서 필터링됨.
