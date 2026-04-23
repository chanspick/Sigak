"""SIGAK v2.0: best_shot_sessions

Revision ID: 20260430_bestshot
Revises: 20260429_monthly
Create Date: 2026-04-30

Phase K1 (CLAUDE.md §3.4 / §5.3 + 본인 확정 50-500 / target 1/15 / max 1/10).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260430_bestshot"
down_revision = "20260429_monthly"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "best_shot_sessions",
        sa.Column("session_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'uploading'"),
        ),
        sa.Column("uploaded_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("strength_score_snapshot", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "strength_warning_acknowledged",
            sa.Boolean(), nullable=False, server_default=sa.text("FALSE"),
        ),
        sa.Column("result_data", JSONB(), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_best_shot_sessions_user_status",
        "best_shot_sessions",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_best_shot_sessions_created",
        "best_shot_sessions",
        [sa.text("created_at DESC")],
    )


def downgrade():
    op.drop_index("ix_best_shot_sessions_created", table_name="best_shot_sessions")
    op.drop_index("ix_best_shot_sessions_user_status", table_name="best_shot_sessions")
    op.drop_table("best_shot_sessions")
