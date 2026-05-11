from __future__ import annotations

from pathlib import Path
from typing import cast

import asyncpg
import pytest

from msdp_api.db import migrations


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeMigrationConnection:
    def __init__(self, applied: set[str] | None = None) -> None:
        self.applied = applied or set()
        self.executed: list[tuple[str, str | None]] = []

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    async def execute(self, sql: str, migration_name: str | None = None) -> None:
        self.executed.append((sql, migration_name))
        if sql.startswith("INSERT INTO schema_migrations") and migration_name is not None:
            self.applied.add(migration_name)

    async def fetch(self, sql: str) -> list[dict[str, str]]:
        assert sql == "SELECT name FROM schema_migrations"
        return [{"name": migration_name} for migration_name in self.applied]


@pytest.mark.asyncio
async def test_apply_migrations_records_only_pending_files(monkeypatch, tmp_path):
    first = tmp_path / "20260101_first.sql"
    second = tmp_path / "20260102_second.sql"
    first.write_text("SELECT 1;", encoding="utf-8")
    second.write_text("SELECT 2;", encoding="utf-8")
    monkeypatch.setattr(migrations, "MIGRATIONS_PATH", Path(tmp_path))
    connection = FakeMigrationConnection(applied={"20260101_first.sql"})

    await migrations.apply_migrations(cast("asyncpg.Connection", connection))

    assert ("SELECT 1;", None) not in connection.executed
    assert ("SELECT 2;", None) in connection.executed
    assert ("INSERT INTO schema_migrations (name) VALUES ($1)", "20260102_second.sql") in (
        connection.executed
    )
    assert connection.applied == {"20260101_first.sql", "20260102_second.sql"}
