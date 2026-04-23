"""이달의 시각 (Monthly Report) 스키마 — Phase M (MVP 스켈레톤).

CLAUDE.md §3.7 / §5.6 정의.

MVP 범위:
  - 스키마 + DB 테이블 정의
  - 유저 당 월 1개 (UNIQUE user_id, year_month)
  - 실 리포트 엔진은 v1.1+ 이관
  - 현재는 status="placeholder" 로 "준비 중" 안내만

Status 머신:
  scheduled   — 다음 15일 대기 상태 (기본)
  generating  — 엔진 실행 중 (v1.1+)
  ready       — 생성 완료, 유저 열람 가능
  delivered   — 유저가 열람/결제 완료
  failed      — 생성 실패
  placeholder — MVP 한정. "v1.1+ 에서 제공 예정" 안내용

Idempotency key 패턴: f"monthly:{user_id}:{year_month}"  (year_month = "2026-04")
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


MonthlyReportStatus = Literal[
    "scheduled", "generating", "ready", "delivered", "failed", "placeholder",
]


class MonthlyReport(BaseModel):
    """monthly_reports.result_data JSONB + DB row 공통 도메인 표현."""
    model_config = ConfigDict(extra="ignore")

    report_id: str
    user_id: str
    year_month: str                      # "2026-04" — 월 단위 고유
    status: MonthlyReportStatus

    scheduled_for: datetime              # KST 15일 00:00 UTC 변환값
    generated_at: Optional[datetime] = None

    # v1.1+ 엔진이 채움. MVP 에선 None 또는 placeholder 메시지.
    result_data: Optional[dict] = None

    created_at: datetime


class MonthlyStatusResponse(BaseModel):
    """라우트 GET /api/v2/monthly/status 응답."""
    model_config = ConfigDict(extra="ignore")

    next_delivery: datetime              # 다음 리포트 예정 시각 (UTC)
    next_delivery_year_month: str        # "2026-05"
    days_remaining: int                  # 오늘 대비 next_delivery 까지 남은 일수

    current_month_report_id: Optional[str] = None
    current_month_status: Optional[MonthlyReportStatus] = None

    # 과거 리포트 수 (유저가 몇 번 받았는지) — 홈 카드 배지 용
    past_reports_count: int = 0

    # MVP 안내 — "아직 생성 엔진 준비 중" 고정 문구 (프론트 카드 copy)
    placeholder_message: Optional[str] = None


class MonthlyScheduleTickResult(BaseModel):
    """scheduler tick 반환 — 운영 모니터링용."""
    model_config = ConfigDict(extra="ignore")

    tick_at: datetime
    year_month: str
    candidates_scanned: int = 0
    scheduled_created: int = 0
    skipped_existing: int = 0
    errors: int = 0
