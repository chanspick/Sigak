"""v1.2: users.onboarding_completed + onboarding_data

Revision ID: 20260420_v1_2_users_onboarding
Revises: 20260419_mvp_tables
Create Date: 2026-04-20

Adds 4-step onboarding persistence to users. ``onboarding_data`` is a flat
JSONB — same field names as Pydantic ``SubmitRequest`` so existing pipeline
code reads from it unchanged. ``onboarding_completed`` flips True when step 4
save_step call sees all 9 required fields present (see routes/onboarding.py).

NOTE: ``verdicts.blur_released`` (separate column, not ``reports.blur_released``)
is deferred to the next migration — tracked as Phase C work in
memory/project_v1_2_prep.md.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260420_v1_2_users_onboarding"
down_revision = "20260419_mvp_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("onboarding_data", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS onboarding_data")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS onboarding_completed")
