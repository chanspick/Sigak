# Alembic Migration Strategy (SIGAK MVP v1.1)

Scaffolded 2026-04-19. No migration files yet — those arrive once blockers
Q1/Q3/Q4/Q7 from the MVP brief are resolved and the new token/verdict tables
are finalized.

## Current DB management

The existing DB is still created by `db.py::Base.metadata.create_all()` plus
the ad-hoc `_migrate_columns()` ALTER statements. Alembic co-exists but is
inert until the first migration file is added.

## First migration (baseline)

When the first real migration is created:

### On existing deploys (production, staging with real data)

```
alembic stamp head
```

Marks the current schema as "already at latest" without running any DDL.
This is safe because the schema was produced by `create_all()` and must
match `Base.metadata` exactly.

### On fresh environments

```
alembic upgrade head
```

Creates all tables from migrations instead of `create_all()`.

### Cleanup (after first migration is confirmed deployed)

Remove `_migrate_columns()` call from `db.py::init_db()`. Until then both
mechanisms run at startup and are idempotent.

## Creating migrations

Prefer hand-written migrations for MVP — autogenerate is convenient but
produces noisy diffs against the existing schema. Example:

```
alembic revision -m "add token_balances and token_transactions"
```

Then fill in `upgrade()` / `downgrade()` in the generated file under
`versions/`.

## URL handling

`env.py::_get_url()` reads `DATABASE_URL` from env and normalizes
`postgres://`, `postgresql+asyncpg://`, etc. to sync `postgresql://` form
matching `db.py`. Do not hardcode the URL in `alembic.ini`.
