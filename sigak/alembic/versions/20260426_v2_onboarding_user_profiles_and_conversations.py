"""v2 Onboarding: user_profiles + conversations tables

Revision ID: 20260426_v2_onboarding_user_profiles_and_conversations
Revises: 20260425_verdicts_gold_reading
Create Date: 2026-04-26

Priority 1 D1 — SIGAK v2 Onboarding + Verdict redesign (SPEC-ONBOARDING-V2).

Adds:
  - users.birth_date DATE (nullable for existing v1 users)
  - users.ig_handle VARCHAR(50) (nullable, optional onboarding input)
  - conversations table (Sia 대화 이력 영속, onboarding snapshot)
  - user_profiles table (gender-aware profile + IG cache + extracted fields)

Relationship to v1:
  - users.onboarding_data (JSONB) / users.onboarding_completed (BOOL) 는 유지.
    v2 릴리스 후 2주 동안 dual-read 가능. v3 에서 drop 예정.
  - 기존 v1 유저는 user_profiles row 없이 존재 가능 (optional 재온보딩 유도).

Rollback policy:
  - downgrade() 는 신규 2 테이블 drop + users 신규 2 컬럼 drop.
  - 기존 v1 데이터는 온전히 유지됨.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260426_v2_onboarding_user_profiles_and_conversations"
down_revision = "20260425_verdicts_gold_reading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─────────────────────────────────────────────
    # 1. users 컬럼 확장 (v2 structured input)
    # ─────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("birth_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("ig_handle", sa.String(50), nullable=True),
    )

    # ─────────────────────────────────────────────
    # 2. conversations: Sia 대화 이력
    # ─────────────────────────────────────────────
    # 영속 보존 (Redis 는 active session 동안만 TTL 5분 sliding).
    # extraction 은 종료 후 Sonnet 4.6 가 messages → extraction_result JSONB 로 변환.
    op.create_table(
        "conversations",
        sa.Column(
            "conversation_id",
            sa.String(36),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "messages",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "turn_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "ended_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "extraction_result",
            JSONB(),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_conversations_user_status",
        "conversations",
        ["user_id", "status"],
    )

    # ─────────────────────────────────────────────
    # 3. user_profiles: 유저 프로파일 (v2 onboarding 산출물)
    # ─────────────────────────────────────────────
    # 구성:
    #   - Structured (Step 0): gender, birth_date, ig_handle (users 와 중복 OK)
    #   - IG 자동 추출 (Step 1): ig_feed_cache JSONB
    #   - 대화 추출 (Step 2): structured_fields JSONB
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # Structured fields (Step 0)
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("ig_handle", sa.String(50), nullable=True),

        # IG auto-extracted (Step 1)
        sa.Column("ig_feed_cache", JSONB(), nullable=True),
        sa.Column("ig_fetch_status", sa.String(20), nullable=True),  # success/failed/skipped/private
        sa.Column(
            "ig_fetched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        # Conversation extracted (Step 2)
        sa.Column(
            "structured_fields",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),

        # Meta
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
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
    )

    # IG refresh 쿼리 지원 (ig_fetched_at 기반 stale 탐지)
    op.create_index(
        "idx_user_profiles_ig_fetched_at",
        "user_profiles",
        ["ig_fetched_at"],
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_profiles_ig_fetched_at")
    op.execute("DROP TABLE IF EXISTS user_profiles")

    op.execute("DROP INDEX IF EXISTS idx_conversations_user_status")
    op.execute("DROP TABLE IF EXISTS conversations")

    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS ig_handle")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS birth_date")
