"""Database migration helpers."""

from __future__ import annotations

from pathlib import Path

import asyncpg

MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / "sql" / "migrations"


async def apply_migrations(connection: asyncpg.Connection | asyncpg.Pool) -> None:
    """Apply all tracked SQL migrations in lexical order.

    The migrations are written to be idempotent so startup can safely re-run them.
    """
    for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
        await connection.execute(migration_path.read_text(encoding="utf-8"))
