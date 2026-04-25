"""SIGAK v2.0 Phase I PI-D — pi_v3 baseline + 추가 컬럼

Revision ID: 20260503_piv3
Revises: 20260502_userhistory
Create Date: 2026-04-25

CLAUDE.md §5.1 PI v1 spec (본인 결정 2026-04-25):
  - 가입 30 + PI 50 = 부족 20 결제
  - baseline 정면 사진 R2 영구 저장
  - pi_engine STEP 추가: face_metrics / coord_3axis / matched_types / matched_celebs
    / vault_snapshot / r2_sonnet_raw_key / r2_haiku_raw_key / r2_clip_embedding_key

Scope:
  users 테이블:
    pi_baseline_r2_key       VARCHAR — 정면 사진 R2 키 (영구 보관)
    pi_baseline_uploaded_at  TIMESTAMPTZ — 업로드 시각
    pi_pending               BOOLEAN  — baseline 업로드 후 unlock 미완료 표시

  pi_reports 테이블 (PI-A/PI-B/PI-C 가 채울 컬럼들):
    face_metrics             JSONB — MediaPipe 468 메트릭
    coord_3axis              JSONB — Shape/Volume/Age 좌표
    matched_types            JSONB — type top-3 + cosine similarity
    matched_celebs           JSONB — 셀럽 top-3 + similarity
    vault_snapshot           JSONB — 생성 시점 vault 스냅샷
    r2_sonnet_raw_key        VARCHAR — Sonnet Vision raw 응답 R2 키
    r2_haiku_raw_key         VARCHAR — Haiku narrative raw R2 키
    r2_clip_embedding_key    VARCHAR — CLIP 768d embedding R2 키

기존 pi_reports.report_data JSONB 는 유지 — 9 컴포넌트 응답 캐시 용도. PI-A/PI-C 가
analytic 컬럼을 분리 채워서 디버깅 / Monthly 시계열 비교 / re-render 용이.

전수 nullable=True — 신규 컬럼 모두 기존 row 영향 없음. 운영 실행 안전.

Rollback:
  downgrade() 두 테이블의 추가 컬럼 drop. 데이터 손실은 컬럼 자체에 있던 값만.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260503_piv3"
down_revision = "20260502_userhistory"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────
#  upgrade
# ─────────────────────────────────────────────

def upgrade() -> None:
    # 1. users 테이블 — baseline 메타데이터
    op.add_column(
        "users",
        sa.Column("pi_baseline_r2_key", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "pi_baseline_uploaded_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "pi_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
    )

    # 2. pi_reports 테이블 — PI-A/PI-B/PI-C 분석 컬럼
    op.add_column(
        "pi_reports",
        sa.Column("face_metrics", JSONB(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("coord_3axis", JSONB(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("matched_types", JSONB(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("matched_celebs", JSONB(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("vault_snapshot", JSONB(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("r2_sonnet_raw_key", sa.String(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("r2_haiku_raw_key", sa.String(), nullable=True),
    )
    op.add_column(
        "pi_reports",
        sa.Column("r2_clip_embedding_key", sa.String(), nullable=True),
    )


def downgrade() -> None:
    # pi_reports 컬럼 drop
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS r2_clip_embedding_key")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS r2_haiku_raw_key")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS r2_sonnet_raw_key")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS vault_snapshot")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS matched_celebs")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS matched_types")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS coord_3axis")
    op.execute("ALTER TABLE pi_reports DROP COLUMN IF EXISTS face_metrics")

    # users 컬럼 drop
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS pi_pending")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS pi_baseline_uploaded_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS pi_baseline_r2_key")
