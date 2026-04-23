"""SIGAK v2.0 Phase I: pi_reports versioning (user_id PK → report_id PK + version + is_current)

Revision ID: 20260501_piv2
Revises: 20260430_bestshot
Create Date: 2026-05-01

CLAUDE.md §5.1 DB 변경 명시.

기존 스키마 (20260424_v2_bm_diagnosis_and_pi):
  pi_reports (user_id PK, unlocked_at, report_data, created_at, updated_at)

신 스키마:
  pi_reports (report_id PK, user_id, version, is_current, unlocked_at,
              report_data, created_at, updated_at)
  + partial UNIQUE INDEX on (user_id) WHERE is_current = TRUE
  + UNIQUE (user_id, version)
  + index (user_id, is_current)
  + index (user_id, version DESC)

Legacy data 처리 (grandfathered via sigak_report_released → {status: "migrated_from_sigak_report"}):
  기존 user_id PK row 를 report_id='pi_legacy_{user_id}', version=1, is_current=TRUE 로 이관.
  데이터 손실 0 보장.

Downgrade:
  신 컬럼 drop + user_id 로 PK 복귀. 단, 동일 user_id 중복 row 있으면 실패 가능.
  MVP 운영 상 upgrade only 권장.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260501_piv2"
down_revision = "20260430_bestshot"
branch_labels = None
depends_on = None


def upgrade():
    # 1. PK 제약 DROP (기존 user_id PK)
    op.drop_constraint("pi_reports_pkey", "pi_reports", type_="primary")

    # 2. 신규 컬럼 추가 (nullable 로 시작)
    op.add_column(
        "pi_reports",
        sa.Column("report_id", sa.String(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column(
            "version", sa.Integer(),
            nullable=False, server_default="1",
        ),
    )
    op.add_column(
        "pi_reports",
        sa.Column(
            "is_current", sa.Boolean(),
            nullable=False, server_default=sa.text("TRUE"),
        ),
    )

    # 3. 기존 row 에 report_id 생성 — 'pi_legacy_{user_id}'
    op.execute(
        "UPDATE pi_reports "
        "SET report_id = 'pi_legacy_' || user_id "
        "WHERE report_id IS NULL"
    )

    # 4. report_id NOT NULL + 신규 PK
    op.alter_column("pi_reports", "report_id", nullable=False)
    op.create_primary_key(
        "pi_reports_pkey", "pi_reports", ["report_id"],
    )

    # 5. 유니크 제약 + 인덱스
    op.create_unique_constraint(
        "uq_pi_reports_user_version", "pi_reports", ["user_id", "version"],
    )
    op.create_index(
        "ix_pi_reports_user_current", "pi_reports", ["user_id", "is_current"],
    )
    op.create_index(
        "ix_pi_reports_user_version_desc",
        "pi_reports",
        ["user_id", sa.text("version DESC")],
    )

    # 6. Partial unique index — 유저당 is_current=TRUE 는 최대 1개
    op.execute(
        "CREATE UNIQUE INDEX ux_pi_reports_one_current_per_user "
        "ON pi_reports (user_id) WHERE is_current = TRUE"
    )


def downgrade():
    """복원 (운영 상 비권장). 동일 user_id 중복 row 있으면 PK 재생성 실패."""
    op.execute("DROP INDEX IF EXISTS ux_pi_reports_one_current_per_user")
    op.drop_index("ix_pi_reports_user_version_desc", table_name="pi_reports")
    op.drop_index("ix_pi_reports_user_current", table_name="pi_reports")
    op.drop_constraint("uq_pi_reports_user_version", "pi_reports", type_="unique")
    op.drop_constraint("pi_reports_pkey", "pi_reports", type_="primary")

    op.drop_column("pi_reports", "is_current")
    op.drop_column("pi_reports", "version")
    op.drop_column("pi_reports", "report_id")

    op.create_primary_key("pi_reports_pkey", "pi_reports", ["user_id"])
