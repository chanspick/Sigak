"""user_history JSONB + ig_last_snapshot_at — 전수 raw 누적 + 24h IG 캐시

Revision ID: 20260502_userhistory
Revises: 20260501_piv2
Create Date: 2026-04-24

Scope:
  users.user_history JSONB DEFAULT '{}' — 4 기능 raw 누적 (conversations /
    best_shot_sessions / aspiration_analyses / verdict_sessions, 각 최대 10개)
  users.ig_last_snapshot_at TIMESTAMPTZ — Sia 재진입 24h 캐시 판정용

CLAUDE.md:
  §4.2 UserDataVault 의 "history 리스트 보유" 명세 이행.
  v1 연료 확보 (LLM 주입 + 유저 데이터 누적 락인).

기존 테이블 (conversations / aspiration_analyses / best_shot_sessions /
  verdict_sessions) 은 유지 — 이중 저장. user_history 는 LLM 주입용 요약본,
  원본 테이블은 조회/감사/backfill 용.

Rollback:
  downgrade() 는 두 컬럼 drop. 기존 row 영향 없음 (다른 컬럼 손대지 않음).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260502_userhistory"
down_revision = "20260501_piv2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "user_history",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "ig_last_snapshot_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ig_last_snapshot_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS user_history")
