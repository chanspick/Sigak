"""verdicts.gold_reading 영속화

Revision ID: 20260425_verdicts_gold_reading
Revises: 20260424_v2_bm_diagnosis_and_pi
Create Date: 2026-04-25

공유 링크로 타유저가 verdict을 열람할 때 gold_reading을 보여줘야 하므로
create 시점 일회성이던 값을 DB에 저장.

기존 row는 NULL → 빈 문자열로 직렬화. 신규 row는 create 시 LLM #3 short 결과 저장.
"""
from alembic import op
import sqlalchemy as sa


revision: str = "20260425_verdicts_gold_reading"
down_revision = "20260424_v2_bm_diagnosis_and_pi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "verdicts",
        sa.Column("gold_reading", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS gold_reading")
