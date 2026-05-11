"""Database migration helpers."""

from __future__ import annotations

from pathlib import Path

import asyncpg

MIGRATIONS_PATH = Path(__file__).resolve().parents[2] / "sql" / "migrations"
MIGRATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


async def apply_migrations(connection: asyncpg.Connection | asyncpg.Pool) -> None:
    """Apply all tracked SQL migrations in lexical order.

    Applied file names are recorded in ``schema_migrations`` so future
    non-idempotent migrations are not re-run in CI or on app startup.
    """
    if isinstance(connection, asyncpg.Pool):
        async with connection.acquire() as acquired_connection:
            await _apply_migrations(acquired_connection)
        return
    await _apply_migrations(connection)


async def _apply_migrations(connection: asyncpg.Connection) -> None:
    """Apply pending SQL migration files using one transaction."""
    async with connection.transaction():
        await connection.execute(MIGRATION_TABLE_SQL)
        rows = await connection.fetch("SELECT name FROM schema_migrations")
        applied_migrations = {row["name"] for row in rows}
        for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
            migration_name = migration_path.name
            if migration_name in applied_migrations:
                continue
            await connection.execute(migration_path.read_text(encoding="utf-8"))
            await connection.execute(
                "INSERT INTO schema_migrations (name) VALUES ($1)",
                migration_name,
            )
