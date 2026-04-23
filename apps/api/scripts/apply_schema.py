"""Apply the backend schema to the configured Postgres database."""

from __future__ import annotations

import asyncio
from pathlib import Path

import asyncpg

from msdp_api.core.config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"


async def main() -> None:
    """Apply the SQL schema file to the configured database."""
    settings = get_settings()
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn = await asyncpg.connect(settings.database_url)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
