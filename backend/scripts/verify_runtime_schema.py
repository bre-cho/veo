from __future__ import annotations

"""Runtime DB schema guard.

Verifies that:
1. The Alembic migration history has exactly **one** head (no divergent branches).
2. The connected database is currently at that head (i.e. all migrations applied).

Exit codes
----------
0   RUNTIME_SCHEMA_GUARD_PASS — everything is fine; worker may continue.
10  Multiple Alembic heads found — a migration merge is required.
20  Database is behind the repo head — ``alembic upgrade head`` must run first.

Usage::

    python /app/scripts/verify_runtime_schema.py

The script reads the database URL from the ``DATABASE_URL`` environment
variable, falling back to ``sqlalchemy.url`` in ``alembic.ini``.
"""

import os
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BASE_DIR / "alembic.ini"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    cfg = Config(str(ALEMBIC_INI))
    return cfg.get_main_option("sqlalchemy.url")


def _alembic_config(url: str) -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def main() -> int:
    url = _database_url()
    cfg = _alembic_config(url)
    script = ScriptDirectory.from_config(cfg)

    heads = set(script.get_heads())
    if len(heads) != 1:
        print(
            f"RUNTIME_SCHEMA_GUARD_FAIL: expected 1 alembic head, "
            f"got {len(heads)}: {sorted(heads)}"
        )
        return 10

    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        context = MigrationContext.configure(conn)
        current = set(context.get_current_heads())

    if current != heads:
        print(
            "RUNTIME_SCHEMA_GUARD_FAIL: database schema is not at repo head. "
            f"current={sorted(current)} expected={sorted(heads)}"
        )
        return 20

    print(f"RUNTIME_SCHEMA_GUARD_PASS: current={sorted(current)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
