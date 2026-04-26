"""Manual token grant — admin one-off (testbed / pre-launch).

Bypasses init_db() side-effects (table create_all + ALTER migrations) by
constructing its own engine, so running this against prod only touches
``token_balances`` and ``token_transactions``. credit_tokens_safe handles
idempotency via the UNIQUE ``token_transactions.idempotency_key`` —
re-running on the same day with the same email is a no-op (returns
existing balance_after).

Usage:
    cd sigak/
    DATABASE_URL='postgresql://...' python -m scripts.grant_tokens_admin \\
        --email jochanhyeong28@gmail.com --amount 100

    # Dry-run: resolve user and print balance only
    DATABASE_URL='postgresql://...' python -m scripts.grant_tokens_admin \\
        --email jochanhyeong28@gmail.com --amount 100 --dry-run
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services import tokens


def _make_session():
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("[ERROR] DATABASE_URL not set", file=sys.stderr)
        return None
    url = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", url)
    safe = url.split("@")[-1] if "@" in url else "set"
    print(f"[INFO] Connecting to ...@{safe}")
    engine = create_engine(url, pool_pre_ping=True)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant tokens to a user (admin)")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--amount", type=int, required=True, help="Token amount (positive)")
    parser.add_argument(
        "--key-suffix",
        default=date.today().isoformat(),
        help="idempotency_key suffix (default: today's ISO date)",
    )
    parser.add_argument("--reference-id", default="testbed-pre-launch")
    parser.add_argument("--dry-run", action="store_true", help="Resolve user only, do not credit")
    args = parser.parse_args()

    if args.amount <= 0:
        print(f"[ERROR] amount must be positive, got {args.amount}", file=sys.stderr)
        return 2

    db = _make_session()
    if db is None:
        return 1

    try:
        row = db.execute(
            text("SELECT id, name, email FROM users WHERE email = :email"),
            {"email": args.email},
        ).first()
        if row is None:
            print(f"[ERROR] No user with email = {args.email}", file=sys.stderr)
            return 3

        user_id, user_name, user_email = row[0], row[1], row[2]
        print(f"[INFO] User: id={user_id} name={user_name} email={user_email}")

        before = tokens.get_balance(db, user_id)
        print(f"[INFO] Balance before: {before}")

        if args.dry_run:
            print(f"[DRY-RUN] Would credit {args.amount} tokens.")
            return 0

        idem = f"manual_grant:{user_id}:{args.key_suffix}"
        print(f"[INFO] idempotency_key = {idem}")

        after = tokens.credit_tokens_safe(
            db,
            user_id=user_id,
            amount=args.amount,
            kind=tokens.KIND_ADMIN_GRANT,
            idempotency_key=idem,
            reference_id=args.reference_id,
            reference_type="admin_manual",
        )

        if after == before:
            print(
                f"[OK] Already granted with this key. Balance unchanged: {after}. "
                f"Use a different --key-suffix to grant again."
            )
        else:
            delta = after - before
            print(f"[OK] Credited {delta} tokens. Balance: {before} -> {after}")
        return 0

    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
