"""v1.2 Phase C: verdicts.blur_released + LLM caching tables

Revision ID: 20260421_v1_2_verdicts_llm_cache
Revises: 20260420_v1_2_users_onboarding
Create Date: 2026-04-21

Three additive changes:
  1. ``verdicts.blur_released BOOL DEFAULT FALSE`` — the new MVP gate. The
     older ``reports.blur_released`` stays untouched for legacy compat.
  2. ``face_interpretations`` — LLM #1 cache keyed by user_id with
     ``features_hash`` for invalidation on feature-shape changes.
  3. ``users.interview_interpretation`` JSONB + hash — LLM #2 cache inline on
     the users row (1:1 with user, no separate table).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260421_v1_2_verdicts_llm_cache"
down_revision = "20260420_v1_2_users_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. verdicts.blur_released
    op.add_column(
        "verdicts",
        sa.Column(
            "blur_released",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    # 2. face_interpretations cache table (LLM #1)
    op.create_table(
        "face_interpretations",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("features_hash", sa.Text(), nullable=False),
        sa.Column("interpretation", JSONB(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # 3. users.interview_interpretation + hash (LLM #2 cache)
    op.add_column(
        "users",
        sa.Column("interview_interpretation", JSONB(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("interview_interpretation_hash", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS interview_interpretation_hash")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS interview_interpretation")
    op.execute("DROP TABLE IF EXISTS face_interpretations")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS blur_released")
