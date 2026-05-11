"""Apply tracked SQL migrations using only ``DATABASE_URL``."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys

import asyncpg
from dotenv import load_dotenv

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from msdp_api.db.migrations import apply_migrations  # noqa: E402


def _get_database_url() -> str:
    """Return the configured database URL or fail with an explicit error.

    Raises:
        RuntimeError: when ``DATABASE_URL`` is not configured.
    """
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        msg = "DATABASE_URL is required to apply database migrations."
        raise RuntimeError(msg)
    return database_url


async def main() -> None:
    """Apply pending SQL migrations to the configured database."""
    conn = await asyncpg.connect(_get_database_url())
    try:
        await apply_migrations(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
