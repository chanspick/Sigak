"""Verdict 2.0: preview/full split + user_profile_snapshot + version

Revision ID: 20260427_verdict_v2
Revises: 20260426_v2_onboarding
Create Date: 2026-04-27

Priority 1 D5 Phase 1 — SIGAK v2 Verdict 재설계 (SPEC-ONBOARDING-V2).

Adds 6 columns to existing `verdicts` table:
  - preview_shown        BOOLEAN DEFAULT FALSE NOT NULL
  - full_unlocked        BOOLEAN DEFAULT FALSE NOT NULL
  - preview_content      JSONB NULL
  - full_content         JSONB NULL
  - user_profile_snapshot JSONB NULL
      (생성 시점의 user_profile 복사본. 이후 profile refresh 돼도 verdict 는
       당시 기준 유지 — immutable 보장)
  - version              VARCHAR(10) DEFAULT 'v1' NOT NULL
      (기존 row 는 'v1' 유지, 신규 v2 flow 는 'v2' 저장)

v1 verdict 와의 공존:
  - 기존 services/verdicts.py 는 변경 없음 (D6 이전까지 유지).
  - 신규 services/verdict_v2.py 가 병행 동작.
  - v1 API path 유지, v2 는 /api/v2/verdict/* 신규 path.
  - 프론트 마이그레이션 완료 후 v3 에서 v1 drop 예정.

Rollback:
  - downgrade() 는 신규 6 컬럼 전량 drop. 기존 v1 row 데이터 손상 없음.

Alembic revision ID 규칙:
  - `version_num VARCHAR(32)` 제한으로 revision_id 는 32자 이내.
  - 본 파일: "20260427_verdict_v2" = 19자, OK.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260427_verdict_v2"
down_revision = "20260426_v2_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────
    # verdicts 테이블 확장 (v2 preview/full split)
    # ─────────────────────────────────────────────
    op.add_column(
        "verdicts",
        sa.Column(
            "preview_shown",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "verdicts",
        sa.Column(
            "full_unlocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )
    op.add_column(
        "verdicts",
        sa.Column("preview_content", JSONB(), nullable=True),
    )
    op.add_column(
        "verdicts",
        sa.Column("full_content", JSONB(), nullable=True),
    )
    op.add_column(
        "verdicts",
        sa.Column("user_profile_snapshot", JSONB(), nullable=True),
    )
    op.add_column(
        "verdicts",
        sa.Column(
            "version",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'v1'"),
        ),
    )

    # v2 전용 조회 가속 — unlock 상태 + version 조합 인덱스
    op.create_index(
        "idx_verdicts_version_unlock",
        "verdicts",
        ["version", "full_unlocked"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_verdicts_version_unlock")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS version")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS user_profile_snapshot")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS full_content")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS preview_content")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS full_unlocked")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS preview_shown")
