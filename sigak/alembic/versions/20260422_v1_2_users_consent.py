"""v1.2: users.consent_completed + consent_data

Revision ID: 20260422_v1_2_users_consent
Revises: 20260421_v1_2_verdicts_llm_cache
Create Date: 2026-04-22

약관 v2.0(2026-04-20 시행) 대응. 온보딩 welcome 화면에서 수집하는 필수 5개
+ 선택 1개 동의 결과를 ``consent_data`` JSONB에 timestamp·ip·version과 함께
저장. 필수 5개 전부 true여야 ``consent_completed`` 플립.

기존 ``onboarding_completed`` 와는 별개 게이트. 순서: consent → onboarding.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260422_v1_2_users_consent"
down_revision = "20260421_v1_2_verdicts_llm_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "consent_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("consent_data", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS consent_data")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS consent_completed")
