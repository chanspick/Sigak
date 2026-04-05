# PAYMENT.md — SIGAK 결제 플로우 명세

> 이 문서는 UX.md의 페이월 결제 부분을 구체화한다.
> WoZ 파일럿 기간에는 카카오톡 송금 + 알바 수동 확인 방식으로 운영하고,
> 토스페이먼츠 PG 승인 후 자동 결제로 전환한다.

---

## 결제 구조 요약

```
FREE        ₩0         커버 + 한줄요약 + 얼굴구조분석
─────────── paywall 1 ──────────────────────────────
STANDARD    ₩5,000    + 피부톤분석 + 미감좌표계
─────────── paywall 2 ──────────────────────────────
FULL        +₩15,000   + 실행가이드 + 셀럽 + 트렌드 (총 ₩20,000)
```

## access_level 상태 + UI 매핑

| access_level     | free 섹션 | standard 섹션      | full 섹션          |
|------------------|-----------|--------------------|---------------------|
| free             | 완전 표시 | 블러 + 페이월 카드 | 블러 + 페이월 카드  |
| standard_pending | 완전 표시 | 블러 + 대기 UI     | 블러 + 페이월 카드  |
| standard         | 완전 표시 | 완전 표시           | 블러 + 페이월 카드  |
| full_pending     | 완전 표시 | 완전 표시           | 블러 + 대기 UI     |
| full             | 완전 표시 | 완전 표시           | 완전 표시           |

pending 상태 = 유저가 "송금 완료" 클릭했으나 알바 미확인.
프론트에서 30초 간격 폴링으로 상태 변화 감지.

---

## 백엔드 API

### 기존 API 수정

**GET /api/v1/report/{report_id}** 응답에 결제 상태 추가:

```json
{
  "id": "report_abc123",
  "access_level": "free",
  "pending_level": null,
  "sections": [ ... ],
  "paywall": {
    "standard": { "price": 5000, "label": "₩5,000 잠금 해제", "method": "manual" },
    "full": { "price": 15000, "label": "+₩15,000 잠금 해제", "total_note": "이전 결제 포함 총 ₩20,000", "method": "manual" }
  },
  "payment_account": {
    "bank": "카카오뱅크",
    "number": "3333-00-0000000",
    "holder": "홍한진(시각)",
    "kakao_link": "kakaotalk://send?..."
  }
}
```

- pending_level이 null이 아니면 해당 단계가 대기 중
- method가 "manual"이면 카카오톡 송금 UI, "auto"이면 토스페이먼츠 위젯

### 신규 API

**POST /api/v1/payment-request/{user_id}** — 유저가 "송금 완료했어요" 클릭 시
**POST /api/v1/confirm-payment/{user_id}** — 알바가 "입금 확인 완료" 클릭 시
**GET /api/v1/dashboard/payments** — 알바 대시보드 결제 확인 대기 목록

### DB 추가: payment_requests 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID PK | |
| user_id | UUID FK | |
| report_id | UUID FK | |
| requested_level | VARCHAR(10) | standard / full |
| amount | INTEGER | 5000 / 15000 |
| status | VARCHAR(10) | pending / confirmed / unconfirmed / cancelled |
| requested_at | TIMESTAMP | 유저 클릭 시각 |
| confirmed_at | TIMESTAMP | 알바 확인 시각 (nullable) |
| confirmed_by | VARCHAR(50) | 확인 알바 이름 (nullable) |

---

## 프론트엔드 컴포넌트 구조

```
ReportPage
├── CoverSection           (항상 표시)
├── SummarySection          (항상 표시)
├── FaceStructureSection    (항상 표시)
├── PaywallGate level="standard"
│   ├── state=locked   → BlurredTeaser + PaywallCard
│   ├── state=pending  → BlurredTeaser + PendingCard
│   └── state=unlocked → null (통과)
├── SkinToneSection         (standard 이상)
├── CoordinateSection       (standard 이상)
├── PaywallGate level="full"
│   ├── state=locked   → BlurredTeaser + PaywallCard
│   ├── state=pending  → BlurredTeaser + PendingCard
│   └── state=unlocked → null (통과)
├── ActionPlanSection       (full 이상)
├── CelebReferenceSection   (full 이상)
├── TrendSection            (full 이상)
├── FeedbackSection         (항상 표시)
└── ShareSection            (항상 표시)
```

PaywallCard는 method에 따라 분기:
- method === "manual" → ManualPaymentFlow (카카오톡 송금 안내)
- method === "auto" → TossPaymentFlow (토스페이먼츠 위젯)

---

## Phase 2: 토스페이먼츠 PG 연동 (승인 후)

### 전환 시점
- 토스페이먼츠 카드사 심사 완료 후 (영업일 5~7일)
- 테스트 키로 개발은 즉시 가능

### 전환 범위
변경되는 것은 **페이월 카드 컴포넌트 1개**뿐.
- config.py에서 paywall.method = "auto" 전환
- 수동 확인 플로우 비활성화 (삭제 아님, fallback 보존)

### 토스페이먼츠 흐름
1. 프론트: SDK requestPayment() → 바텀시트 결제창
2. 유저: 카카오페이/토스페이/카드 선택 → 인증
3. 결제 완료 → webhook으로 확인 → access_level 자동 업데이트
4. 프론트: 블러 fade-out (0.6s) + 스크롤 위치 유지

---

## 엣지 케이스

- 유저가 송금 안 하고 "송금 완료" 클릭 → 알바 미확인 처리 → 24시간 후 pending 자동 해제
- 금액 오류 → 알바 수동 판단, 부족시 차액 안내, 초과시 환불 안내
- 입금자명 불일치 → 카톡으로 본인 확인 후 수동 처리
- 알바 30분 미확인 → 리마인드 카톡 자동 발송
- 환불: 열람 전 전액 환불, 열람 후 불가 (사전 동의)
