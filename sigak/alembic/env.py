"""Alembic migration environment for SIGAK.

Loads SQLAlchemy metadata from db.py and normalizes DATABASE_URL to sync
psycopg2 form (same rule as db.py) so Alembic uses the sync engine even when
app code reads the URL as postgresql+asyncpg://.

See alembic/README.md for the baseline-then-migrate deployment strategy.
"""
import os
import re
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from db import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _get_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    url = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", url)
    return url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    ini_section = config.get_section(config.config_ini_section) or {}
    ini_section["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
