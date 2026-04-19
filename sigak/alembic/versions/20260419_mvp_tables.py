"""MVP v1.1: token balances, transactions, payment_orders, verdicts, reports.blur_released

Revision ID: 20260419_mvp_tables
Revises:
Create Date: 2026-04-19

First Alembic migration. Run `alembic stamp head` on the existing production
DB before upgrading so this migration is NOT applied to an already-populated
schema — the baseline tables (users, orders, reports, notifications) were
created by ``db.py::Base.metadata.create_all()`` and must not be re-created.
See alembic/README.md.

Schema note: the MVP brief (section 5) shows ``user_id BIGINT`` in DDL, but
``users.id`` is a String/VARCHAR UUID in db.py. Foreign keys below use the
existing String type — db.py is authoritative over the brief SQL template.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260419_mvp_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_balances",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("balance >= 0", name="ck_token_balances_nonneg"),
    )

    op.create_table(
        "token_transactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(), nullable=False),
        # kind: purchase | consume_reasoning | consume_blur_release |
        #       consume_monthly_report | consume_other | refund | admin_grant
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),          # +credit, -debit
        sa.Column("balance_after", sa.Integer(), nullable=False),   # audit snapshot
        sa.Column("reference_id", sa.String(), nullable=True),
        # reference_type: order | verdict | report | null
        sa.Column("reference_type", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # Raw SQL for the DESC index — Alembic's column-list API handles ASC fine
    # but DESC requires dialect-specific syntax we'd rather spell out.
    op.execute(
        "CREATE INDEX idx_token_tx_user "
        "ON token_transactions (user_id, created_at DESC)"
    )

    op.create_table(
        "payment_orders",
        sa.Column("id", sa.String(), primary_key=True),  # 'pay_xxx'
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("pack_code", sa.String(), nullable=False),
        sa.Column("amount_krw", sa.Integer(), nullable=False),
        sa.Column("tokens_granted", sa.Integer(), nullable=False),
        # status: pending | paid | failed | cancelled | refunded
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("pg_provider", sa.String(), nullable=False, server_default="toss"),
        sa.Column("pg_payment_key", sa.String(), nullable=True),
        sa.Column("pg_order_id", sa.String(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.execute(
        "CREATE INDEX idx_payment_orders_user "
        "ON payment_orders (user_id, created_at DESC)"
    )

    op.create_table(
        "verdicts",
        sa.Column("id", sa.String(), primary_key=True),  # 'vrd_xxx'
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("winner_photo_id", sa.String(), nullable=False),
        sa.Column("ranked_photo_ids", JSONB(), nullable=False),
        sa.Column("coordinates_snapshot", JSONB(), nullable=True),
        sa.Column(
            "reasoning_unlocked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column("reasoning_unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reasoning_data", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.execute(
        "CREATE INDEX idx_verdicts_user "
        "ON verdicts (user_id, created_at DESC)"
    )

    # reports.blur_released — default TRUE so existing old-BM reports stay
    # unlocked. New onboarding service MUST explicitly insert FALSE for new
    # rows (brief section 5.5).
    op.add_column(
        "reports",
        sa.Column(
            "blur_released",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
    )


def downgrade() -> None:
    # IF EXISTS everywhere so a half-applied upgrade can still be rolled back.
    # (Learned from stamp-before-upgrade recovery: downgrade was failing
    # mid-way when blur_released column didn't exist yet.)
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS blur_released")
    op.execute("DROP INDEX IF EXISTS idx_verdicts_user")
    op.execute("DROP TABLE IF EXISTS verdicts")
    op.execute("DROP INDEX IF EXISTS idx_payment_orders_user")
    op.execute("DROP TABLE IF EXISTS payment_orders")
    op.execute("DROP INDEX IF EXISTS idx_token_tx_user")
    op.execute("DROP TABLE IF EXISTS token_transactions")
    op.execute("DROP TABLE IF EXISTS token_balances")
