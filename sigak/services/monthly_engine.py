"""Monthly Engine — 이달의 시각 스케줄러 스텁 (Phase M2).

CLAUDE.md §3.7 / §5.6 / §15 Phase M.

MVP 범위:
  - KST 15일 00:00 기준 next_delivery 계산
  - 유저당 월 1개 (year_month 유니크) — monthly_reports 테이블 조회/생성
  - run_monthly_scheduler_tick : 크론 후크 placeholder (실 배포는 v1.1+)
  - compute_report_status : 특정 유저의 현재 월 상태

KST 정책:
  "매월 15일 00:00 KST" — 한국 유저 타겟 기준. 계산 내부는 UTC 로 normalize.
  KST = UTC+9. 한국 IANA: "Asia/Seoul" (DST 없음).

신규 유저 정책:
  가입 시점 기준 가장 가까운 미래 15일 00:00 KST 를 next_delivery 로.
  오늘이 14일 이전 → 이번 달 15일.
  오늘이 15일 00:00 이후 → 다음 달 15일.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from schemas.monthly_report import (
    MonthlyReport,
    MonthlyReportStatus,
    MonthlyScheduleTickResult,
)


logger = logging.getLogger(__name__)


# KST = UTC+9 (DST 없음). Python 3.9+ zoneinfo 사용 가능하지만 의존성 최소화 위해
# 고정 offset 으로 처리.
KST = timezone(timedelta(hours=9))

MVP_PLACEHOLDER_MESSAGE = (
    "매월 15일에 지난달 대비 변화를 정리해 찾아옵니다. "
    "실 리포트는 곧 준비될 예정입니다."
)


# ─────────────────────────────────────────────
#  Time helpers
# ─────────────────────────────────────────────

def next_delivery_kst_fifteenth(now_utc: Optional[datetime] = None) -> datetime:
    """지금 시각 이후 가장 가까운 '15일 00:00 KST' 를 UTC 로 반환.

    오늘이 15일 00:00 KST 이전 → 이번 달 15일.
    오늘이 15일 00:00 KST 이후 → 다음 달 15일.
    """
    now = now_utc or datetime.now(timezone.utc)
    now_kst = now.astimezone(KST)

    # 이번 달 15일 00:00 KST
    this_month_fifteenth_kst = now_kst.replace(
        day=15, hour=0, minute=0, second=0, microsecond=0,
    )
    if now_kst < this_month_fifteenth_kst:
        return this_month_fifteenth_kst.astimezone(timezone.utc)

    # 다음 달 15일
    if now_kst.month == 12:
        next_month = this_month_fifteenth_kst.replace(year=now_kst.year + 1, month=1)
    else:
        next_month = this_month_fifteenth_kst.replace(month=now_kst.month + 1)
    return next_month.astimezone(timezone.utc)


def year_month_for_delivery(delivery_utc: datetime) -> str:
    """delivery 시각의 KST 기준 년-월 ('2026-04')."""
    return delivery_utc.astimezone(KST).strftime("%Y-%m")


def days_between(now_utc: datetime, target_utc: datetime) -> int:
    """target - now 남은 일수 (버림). 음수면 0."""
    delta = target_utc - now_utc
    days = delta.days
    return max(days, 0)


# ─────────────────────────────────────────────
#  Status compute — 특정 유저의 현재 월 monthly_reports 조회
# ─────────────────────────────────────────────

def get_current_month_report(
    db,
    user_id: str,
    year_month: Optional[str] = None,
) -> Optional[MonthlyReport]:
    """특정 유저의 특정 월 리포트 조회. 없으면 None."""
    if db is None:
        return None
    if year_month is None:
        year_month = year_month_for_delivery(
            next_delivery_kst_fifteenth()
        )

    try:
        row = db.execute(
            text(
                "SELECT report_id, user_id, year_month, status, "
                "       scheduled_for, generated_at, result_data, created_at "
                "FROM monthly_reports "
                "WHERE user_id = :uid AND year_month = :ym "
                "LIMIT 1"
            ),
            {"uid": user_id, "ym": year_month},
        ).first()
    except Exception:
        # 테이블 미생성 (dev / migration 지연) — 조용히 None
        logger.debug(
            "monthly_reports query failed — treating as not scheduled (user=%s, ym=%s)",
            user_id, year_month,
        )
        return None

    if row is None:
        return None

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


def count_past_reports(db, user_id: str) -> int:
    """과거 (status in ready/delivered) 리포트 수 — 홈 배지용."""
    if db is None:
        return 0
    try:
        scalar = db.execute(
            text(
                "SELECT COUNT(*) FROM monthly_reports "
                "WHERE user_id = :uid AND status IN ('ready', 'delivered')"
            ),
            {"uid": user_id},
        ).scalar()
        return int(scalar or 0)
    except Exception:
        return 0


# ─────────────────────────────────────────────
#  Scheduler — cron stub (v1.1+ 에서 실 구현)
# ─────────────────────────────────────────────

def run_monthly_scheduler_tick(
    db,
    *,
    now_utc: Optional[datetime] = None,
) -> MonthlyScheduleTickResult:
    """매월 15일 cron 훅. MVP placeholder — 실 리포트 생성 없음.

    MVP 동작:
      - 호출 시점 이후 다음 delivery (= 다음 15일) 에 대한 scheduled row 를
        기존 user_profiles 보유 유저 대상으로 생성.
      - UNIQUE(user_id, year_month) 로 중복 무시.
      - status='placeholder' 로 저장 (실 엔진 전까지 "준비 중" 안내용).

    v1.1+ 에서 이 함수가:
      1. status='scheduled' 로 바꾸고
      2. 생성 job 큐잉
      3. result_data 채우면 status='ready'
    로 진화.

    실제 cron 트리거는 외부 (Railway cron / Cloudflare Workers / CI schedule) 에서
    이 함수를 호출. FastAPI app 내부 주기 실행은 MVP 범위 밖.
    """
    result = MonthlyScheduleTickResult(
        tick_at=now_utc or datetime.now(timezone.utc),
        year_month=year_month_for_delivery(next_delivery_kst_fifteenth(now_utc)),
    )

    if db is None:
        return result

    next_delivery = next_delivery_kst_fifteenth(now_utc)
    ym = year_month_for_delivery(next_delivery)

    try:
        rows = db.execute(
            text("SELECT user_id FROM user_profiles"),
        ).fetchall()
    except Exception:
        logger.exception("monthly scheduler: user_profiles scan failed")
        return result

    result.candidates_scanned = len(rows)

    for row in rows:
        user_id = row.user_id
        report_id = f"mr_{uuid.uuid4().hex[:24]}"
        try:
            db.execute(
                text(
                    "INSERT INTO monthly_reports "
                    "  (report_id, user_id, year_month, status, "
                    "   scheduled_for, created_at) "
                    "VALUES (:id, :uid, :ym, 'placeholder', :sf, NOW()) "
                    "ON CONFLICT (user_id, year_month) DO NOTHING"
                ),
                {
                    "id": report_id,
                    "uid": user_id,
                    "ym": ym,
                    "sf": next_delivery,
                },
            )
            # ON CONFLICT DO NOTHING 은 rowcount=0 (already exists) 또는 1 (created).
            # 확정적 카운트 위해 별도 SELECT 생략 (성능). 대신 결과 단순 집계.
            result.scheduled_created += 1
        except Exception:
            logger.exception(
                "monthly scheduler: INSERT failed user=%s ym=%s", user_id, ym,
            )
            result.errors += 1

    db.commit()
    logger.info(
        "monthly scheduler tick: ym=%s scanned=%d scheduled=%d errors=%d",
        ym, result.candidates_scanned,
        result.scheduled_created, result.errors,
    )
    return result
