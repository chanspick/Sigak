"""이달의 시각 엔드포인트 (Phase M3, MVP 스켈레톤).

CLAUDE.md §3.7 / §5.6.

엔드포인트:
  GET /api/v2/monthly/status        다음 15일 예정 + 현재 월 상태
  GET /api/v2/monthly/{report_id}   특정 리포트 조회 (ready/delivered 만 content)

토큰 차감:
  MVP 범위 안에선 실 리포트 생성 없음 → 토큰 차감 0.
  v1.1+ 에서 실 엔진 붙을 때 COST_MONTHLY_REPORT(30) 활성화.

스케줄러:
  run_monthly_scheduler_tick 은 외부 cron 에서 호출. API 라우트로 노출하지 않음
  (어드민 엔드포인트는 v1.1+ 별도 추가 가능).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from deps import db_session, get_current_user
from schemas.monthly_report import (
    MonthlyReport,
    MonthlyStatusResponse,
)
from services.monthly_engine import (
    MVP_PLACEHOLDER_MESSAGE,
    count_past_reports,
    days_between,
    get_current_month_report,
    next_delivery_kst_fifteenth,
    year_month_for_delivery,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/monthly", tags=["monthly"])


# ─────────────────────────────────────────────
#  GET /status
# ─────────────────────────────────────────────

@router.get("/status", response_model=MonthlyStatusResponse)
def get_status(
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> MonthlyStatusResponse:
    """다음 15일 예정 + 유저의 현재 월 상태 요약.

    프론트 홈 카드 "이달의 시각" 에 표시될 내용.
    - 다음 리포트 날짜
    - 남은 일수
    - 현재 월 리포트 id + status (있으면)
    - 과거 리포트 수
    - MVP 한정 placeholder_message (실 엔진 붙을 때 None 으로 전환)
    """
    now = datetime.now(timezone.utc)
    next_delivery = next_delivery_kst_fifteenth(now)
    next_ym = year_month_for_delivery(next_delivery)

    # 이번 달 (현 날짜 기준) 리포트 조회
    this_ym = now.astimezone(
        next_delivery.tzinfo if next_delivery.tzinfo else timezone.utc
    ).strftime("%Y-%m")
    # KST 기준 이번 달. 15일 넘었으면 다음 달이 next 이므로, 이번 월 데이터는
    # year_month = this_ym (KST 기준 이번 달) 로 조회.
    from services.monthly_engine import KST
    current_ym = now.astimezone(KST).strftime("%Y-%m")
    current_report = get_current_month_report(db, user["id"], year_month=current_ym)

    past_count = count_past_reports(db, user["id"])

    return MonthlyStatusResponse(
        next_delivery=next_delivery,
        next_delivery_year_month=next_ym,
        days_remaining=days_between(now, next_delivery),
        current_month_report_id=(
            current_report.report_id if current_report else None
        ),
        current_month_status=(
            current_report.status if current_report else None
        ),
        past_reports_count=past_count,
        placeholder_message=(
            # 실 엔진 구현 전까지는 항상 placeholder 안내 표시
            MVP_PLACEHOLDER_MESSAGE
        ),
    )


# ─────────────────────────────────────────────
#  GET /{report_id}
# ─────────────────────────────────────────────

@router.get("/{report_id}", response_model=MonthlyReport)
def get_report(
    report_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(db_session),
) -> MonthlyReport:
    """특정 리포트 조회. 소유자만 접근 (403 otherwise)."""
    if db is None:
        raise HTTPException(500, "DB unavailable")

    row = db.execute(
        text(
            "SELECT report_id, user_id, year_month, status, "
            "       scheduled_for, generated_at, result_data, created_at "
            "FROM monthly_reports WHERE report_id = :rid"
        ),
        {"rid": report_id},
    ).first()

    if row is None:
        raise HTTPException(404, "이달의 시각 리포트를 찾을 수 없습니다.")
    if row.user_id != user["id"]:
        raise HTTPException(403, "본인 리포트가 아닙니다.")

    return MonthlyReport(
        report_id=row.report_id,
        user_id=row.user_id,
        year_month=row.year_month,
        status=row.status,
        scheduled_for=row.scheduled_for,
        generated_at=row.generated_at,
        result_data=row.result_data,
        created_at=row.created_at,
    )
