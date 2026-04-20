"""v1.2: users.sigak_report_released

Revision ID: 20260423_v1_2_users_sigak_report
Revises: 20260422_v1_2_users_consent
Create Date: 2026-04-23

시각 리포트(온보딩 기반 분석 요약) 해제 플래그.
- TRUE: 유저가 30토큰 소비해서 해제한 상태. GET /sigak-report가 onboarding_data 반환.
- FALSE: 잠김 (기본). 프론트가 블러 처리 + 해제 CTA 노출.

시각 재설정 시 reset 엔드포인트가 FALSE로 되돌림(잠김 상태 복귀).
하지만 release 엔드포인트의 idempotency_key는 재사용되므로 재해제 시 추가 차감 없음.
"""
from alembic import op
import sqlalchemy as sa


revision: str = "20260423_v1_2_users_sigak_report"
down_revision = "20260422_v1_2_users_consent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "sigak_report_released",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS sigak_report_released")
