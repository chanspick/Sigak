"""SIGAK v2.0: monthly_reports (이달의 시각 스켈레톤)

Revision ID: 20260429_monthly
Revises: 20260428_aspiration
Create Date: 2026-04-29

Phase M1 (CLAUDE.md §3.7/§5.6).

MVP 스코프:
  - 테이블만 생성. 실 생성 엔진은 v1.1+ 이관.
  - UNIQUE(user_id, year_month) — 유저당 월 1개 보장.
  - status 기본 'scheduled'. placeholder 는 MVP 한정.

year_month 포맷: 'YYYY-MM' (예: '2026-04'). CHAR(7) 로 고정.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260429_monthly"
down_revision = "20260428_aspiration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monthly_reports",
        sa.Column("report_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("year_month", sa.CHAR(7), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'scheduled'"),
            comment="scheduled | generating | ready | delivered | failed | placeholder",
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_data", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "user_id", "year_month",
            name="uq_monthly_reports_user_year_month",
        ),
    )
    op.create_index(
        "ix_monthly_reports_user_status",
        "monthly_reports",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_monthly_reports_scheduled_for",
        "monthly_reports",
        ["scheduled_for"],
    )


def downgrade():
    op.drop_index("ix_monthly_reports_scheduled_for", table_name="monthly_reports")
    op.drop_index("ix_monthly_reports_user_status", table_name="monthly_reports")
    op.drop_table("monthly_reports")
