"""v2 BM: verdicts.diagnosis_unlocked + pi_reports 신규

Revision ID: 20260424_v2_bm_diagnosis_and_pi
Revises: 20260423_v1_2_users_sigak_report
Create Date: 2026-04-24

BM 재설계:
  - 피드 진단 해제 (verdict 단위): 10 토큰 — 신규 diagnosis_unlocked 컬럼
  - PI 해제 (유저 1회 영속): 50 토큰 — 신규 pi_reports 테이블
  - 변화 탭: 무료
  - 기존 verdicts.blur_released (50토큰 통합 블러 해제): deprecated 유지
  - 기존 users.sigak_report_released (30토큰): 신규 pi_reports로 이관

Migration 포인트:
  - verdicts.diagnosis_unlocked 신규 컬럼, 기본 FALSE.
  - pi_reports 신규 테이블 (user_id PK, unlocked_at nullable, report_data JSONB).
  - sigak_report_released=TRUE 유저는 pi_reports로 이관 (grandfathered — 기지불자
    50토큰 재지불 면제). unlocked_at = NOW() 스탬프.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260424_v2_bm_diagnosis_and_pi"
down_revision = "20260423_v1_2_users_sigak_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. verdicts.diagnosis_unlocked
    op.add_column(
        "verdicts",
        sa.Column(
            "diagnosis_unlocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    # 2. pi_reports 테이블
    op.create_table(
        "pi_reports",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_data", JSONB(), nullable=True),
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

    # 3. 기존 sigak_report_released=TRUE 유저 → pi_reports 이관 (grandfathered)
    op.execute(
        """
        INSERT INTO pi_reports (user_id, unlocked_at, report_data, created_at, updated_at)
        SELECT
          id,
          NOW(),
          jsonb_build_object('status', 'migrated_from_sigak_report'),
          NOW(),
          NOW()
        FROM users
        WHERE sigak_report_released = TRUE
        ON CONFLICT (user_id) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pi_reports")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS diagnosis_unlocked")
