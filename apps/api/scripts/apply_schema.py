"""Apply the backend schema to the configured Postgres database."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

from msdp_api.db.migrations import apply_migrations

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"


async def main() -> None:
    """Apply the SQL schema file to the configured database."""
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        msg = "DATABASE_URL is required to apply the database schema."
        raise RuntimeError(msg)
    conn = await asyncpg.connect(database_url)
    try:
        if SCHEMA_PATH.exists():
            await conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        await apply_migrations(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
