"""verdicts.raw_sonnet_r2_key — Verdict v2 LLM raw 영구 저장

Revision ID: 20260505_verdict_raw
Revises: 20260504_r2_uploadfail
Create Date: 2026-04-27

데이터 기업 원칙: LLM 산출물도 raw 로 영원히. 기존 verdicts 테이블은
preview_content / full_content (파싱된 결과 JSONB) 만 보존하고 Sonnet 의
원시 응답 텍스트는 휘발됐음. 재현 불가능한 LLM 출력 → R2 영구 저장.

신규 컬럼 (verdicts):
  raw_sonnet_r2_key       VARCHAR — Sonnet response raw text R2 키
  sonnet_attempt_count    INT     — 몇 번째 시도에 성공했는지 (디버깅)

R2 저장 위치:
  users/{user_id}/verdicts/{verdict_id}/sonnet_raw.txt

raw 본문은 BYTEA 가 아닌 R2 에 보관 — 응답 본문 (수 KB) 다수 누적 시
DB 부담 회피. R2 put 실패 시 dead-letter 가 받아서 보존.

기존 row 영향 없음 (모두 nullable).
"""
from alembic import op
import sqlalchemy as sa


revision = "20260505_verdict_raw"
down_revision = "20260504_r2_uploadfail"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "verdicts",
        sa.Column("raw_sonnet_r2_key", sa.String(255), nullable=True),
    )
    op.add_column(
        "verdicts",
        sa.Column("sonnet_attempt_count", sa.Integer, nullable=True),
    )


def downgrade():
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS sonnet_attempt_count")
    op.execute("ALTER TABLE verdicts DROP COLUMN IF EXISTS raw_sonnet_r2_key")
