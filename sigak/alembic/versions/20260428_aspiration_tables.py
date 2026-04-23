"""SIGAK v2.0: aspiration_analyses + aspiration_target_blocklist

Revision ID: 20260428_aspiration
Revises: 20260427_verdict_v2
Create Date: 2026-04-28

Phase J1 (CLAUDE.md §3.5/§3.6/§5.4/§5.5).

Tables:
  1. aspiration_analyses
     - id (PK)
     - user_id (FK users.id, CASCADE)
     - target_type ('ig' | 'pinterest')
     - target_identifier (핸들 or 보드 URL)
     - result_data JSONB (AspirationAnalysis dump)
     - created_at

  2. aspiration_target_blocklist
     - PK (target_type, target_identifier)
     - blocked_at
     - reason

사용 흐름:
  라우트 요청 → blocklist 체크 → Apify 수집 → Vision → 결과 저장.
  대상자 삭제 요청 수신 → aspiration_target_blocklist INSERT + 관련 analyses 삭제.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260428_aspiration"
down_revision = "20260427_verdict_v2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "aspiration_analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "target_type",
            sa.String(20),
            nullable=False,
            comment="ig | pinterest",
        ),
        sa.Column("target_identifier", sa.String(512), nullable=False),
        sa.Column("result_data", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_aspiration_analyses_user_id_created",
        "aspiration_analyses",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_aspiration_analyses_target",
        "aspiration_analyses",
        ["target_type", "target_identifier"],
    )

    op.create_table(
        "aspiration_target_blocklist",
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_identifier", sa.String(512), nullable=False),
        sa.Column(
            "blocked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("reason", sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint(
            "target_type", "target_identifier",
            name="pk_aspiration_target_blocklist",
        ),
    )


def downgrade():
    op.drop_table("aspiration_target_blocklist")
    op.drop_index(
        "ix_aspiration_analyses_target",
        table_name="aspiration_analyses",
    )
    op.drop_index(
        "ix_aspiration_analyses_user_id_created",
        table_name="aspiration_analyses",
    )
    op.drop_table("aspiration_analyses")
