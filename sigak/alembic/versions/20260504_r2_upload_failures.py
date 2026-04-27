"""r2_upload_failures table — dead-letter for failed R2 uploads (raw 손실 0 정책).

Revision ID: 20260504_r2_uploadfail
Revises: 20260503_piv3
Create Date: 2026-04-27

데이터 기업 원칙: raw 손실 절대 금지. R2 일시 장애로 사진/Vision raw 가
24-48h 후 IG CDN 만료와 함께 영구 손실되는 상황 차단.

Flow:
  services.r2_persistence.put_bytes_durable(...)
    1. r2_client.put_bytes_with_retry (3회 exponential backoff)
    2. 그래도 실패 → r2_upload_failures INSERT (raw bytes 자체 보관)
    3. 운영자가 admin 라우트 또는 별도 cron 으로 재시도

컬럼:
  id              UUID PK (hex string)
  user_id         FK users.id CASCADE
  purpose         'ig_snapshot' / 'ig_vision_raw' / 'aspiration_photo' / ...
  r2_key          업로드 시도했던 키 (재시도 시 동일 키 사용)
  payload         BYTEA — 실패한 raw 데이터 그 자체 (영구 보존)
  content_type    image/jpeg 등
  src_url         원본 IG CDN URL (재수집 fallback 용, 24-48h 만료 가능)
  error_kind      예외 클래스명
  attempts        시도 횟수 (재시도마다 증가)
  status          'pending' / 'completed' / 'fatal'
  created_at      최초 INSERT 시각
  last_attempted_at 마지막 시도 시각
  completed_at    최종 R2 업로드 성공 시각 (성공 시에만)

Rollback:
  downgrade() 테이블 drop. 이 테이블이 destination 이므로 손실되면
  진짜 raw 영구 손실. 운영 환경에서 downgrade 금지.
"""
from alembic import op
import sqlalchemy as sa


revision = "20260504_r2_uploadfail"
down_revision = "20260503_piv3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "r2_upload_failures",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "purpose",
            sa.String(40),
            nullable=False,
            comment="ig_snapshot | ig_vision_raw | aspiration_photo | ...",
        ),
        sa.Column("r2_key", sa.Text, nullable=False),
        sa.Column(
            "payload",
            sa.LargeBinary,
            nullable=False,
            comment="실패한 raw bytes — 영구 보존. 재시도 시 그대로 R2 put.",
        ),
        sa.Column("content_type", sa.String(80), nullable=True),
        sa.Column(
            "src_url",
            sa.Text,
            nullable=True,
            comment="원본 fetch URL (IG CDN 등). 재수집 fallback 용.",
        ),
        sa.Column("error_kind", sa.String(80), nullable=True),
        sa.Column(
            "attempts",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="pending | completed | fatal",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "last_attempted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    # 운영 모니터링용 — 펜딩 row 빠르게 식별 + 유저별 집계
    op.create_index(
        "ix_r2_upload_failures_status_created",
        "r2_upload_failures",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_r2_upload_failures_user",
        "r2_upload_failures",
        ["user_id"],
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_r2_upload_failures_user")
    op.execute("DROP INDEX IF EXISTS ix_r2_upload_failures_status_created")
    op.execute("DROP TABLE IF EXISTS r2_upload_failures")
