"""Postgres repository implementation backed by asyncpg."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import asyncpg

from msdp_api.db.models import Group, Summary, ThreadMessage, Topic, TopicCreate, TopicStatus, User


def _row_to_topic(row: asyncpg.Record) -> Topic:
    """Convert a topic row into a model."""
    return Topic(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=TopicStatus(row["status"]),
        closes_at=row["closes_at"],
        created_at=row["created_at"],
    )


def _row_to_group(row: asyncpg.Record) -> Group:
    """Convert a group row into a model."""
    return Group(
        id=row["id"],
        topic_id=row["topic_id"],
        thread_id=row["thread_id"],
        invite_link=row["invite_link"],
        capacity=row["capacity"],
        member_count=row["member_count"],
        telegram_topic_name=row["telegram_topic_name"],
    )


def _row_to_summary(row: asyncpg.Record) -> Summary:
    """Convert a summary row into a model."""
    return Summary(
        id=row["id"],
        group_id=row["group_id"],
        content=row["content"],
        created_at=row["created_at"],
    )


def _row_to_message(row: asyncpg.Record) -> ThreadMessage:
    """Convert a thread message row into a model."""
    return ThreadMessage(
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        group_id=row["group_id"],
        telegram_user_id=row["telegram_user_id"],
        username=row["username"],
        first_name=row["first_name"],
        text=row["text"],
        sent_at=row["sent_at"],
    )


class PostgresRepository:
    """Repository implementation using asyncpg."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize the repository."""
        self._pool = pool

    async def get_active_topic(self) -> Topic | None:
        """Return the first active topic."""
        query = """
            SELECT id, title, description, status, closes_at, created_at
            FROM topics
            WHERE status = 'active'
            ORDER BY created_at ASC
            LIMIT 1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query)
        return _row_to_topic(row) if row else None

    async def get_topic(self, topic_id: UUID) -> Topic | None:
        """Return a topic by id."""
        query = """
            SELECT id, title, description, status, closes_at, created_at
            FROM topics
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, topic_id)
        return _row_to_topic(row) if row else None

    async def create_topic(self, payload: TopicCreate) -> Topic:
        """Create a topic."""
        query = """
            INSERT INTO topics (title, description, status, closes_at, created_at)
            VALUES ($1, $2, 'active', $3, $4)
            RETURNING id, title, description, status, closes_at, created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                payload.title,
                payload.description,
                payload.closes_at,
                datetime.now(UTC),
            )
        if row is None:
            msg = "Topic insert returned no row."
            raise RuntimeError(msg)
        return _row_to_topic(row)

    async def list_groups_for_topic(self, topic_id: UUID) -> Sequence[Group]:
        """Return groups for a topic."""
        query = """
            SELECT
                id, topic_id, thread_id, invite_link, capacity, member_count, telegram_topic_name
            FROM groups
            WHERE topic_id = $1
            ORDER BY member_count ASC, thread_id ASC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, topic_id)
        return [_row_to_group(row) for row in rows]

    async def find_group_by_thread_id(self, thread_id: int) -> Group | None:
        """Return the group for a given thread id."""
        query = """
            SELECT
                id, topic_id, thread_id, invite_link, capacity, member_count, telegram_topic_name
            FROM groups
            WHERE thread_id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, thread_id)
        return _row_to_group(row) if row else None

    async def create_group(
        self,
        topic_id: UUID,
        thread_id: int,
        invite_link: str,
        capacity: int,
        telegram_topic_name: str,
    ) -> Group:
        """Create a group."""
        query = """
            INSERT INTO groups (
                topic_id, thread_id, invite_link, capacity, member_count, telegram_topic_name
            )
            VALUES ($1, $2, $3, $4, 0, $5)
            RETURNING
                id, topic_id, thread_id, invite_link, capacity, member_count, telegram_topic_name
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                topic_id,
                thread_id,
                invite_link,
                capacity,
                telegram_topic_name,
            )
        if row is None:
            msg = "Group insert returned no row."
            raise RuntimeError(msg)
        return _row_to_group(row)

    async def upsert_user(self, user: User) -> User:
        """Insert or update a user."""
        query = """
            INSERT INTO users (telegram_user_id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_user_id) DO UPDATE
            SET username = EXCLUDED.username, first_name = EXCLUDED.first_name
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                user.telegram_user_id,
                user.username,
                user.first_name,
            )
        return user

    async def create_membership(self, telegram_user_id: int, group_id: UUID) -> bool:
        """Create a membership if missing."""
        query = """
            INSERT INTO memberships (telegram_user_id, group_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, telegram_user_id, group_id)
        return result.endswith("1")

    async def remove_membership(self, telegram_user_id: int, group_id: UUID) -> bool:
        """Remove a membership when present."""
        query = """
            DELETE FROM memberships
            WHERE telegram_user_id = $1 AND group_id = $2
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, telegram_user_id, group_id)
        return result.endswith("1")

    async def increment_group_member_count(self, group_id: UUID) -> None:
        """Increment the group member count."""
        query = """
            UPDATE groups
            SET member_count = member_count + 1
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, group_id)

    async def decrement_group_member_count(self, group_id: UUID) -> None:
        """Decrement the group member count."""
        query = """
            UPDATE groups
            SET member_count = GREATEST(member_count - 1, 0)
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(query, group_id)

    async def store_thread_message(self, message: ThreadMessage) -> None:
        """Store a thread message."""
        query = """
            INSERT INTO thread_messages (
                message_id,
                thread_id,
                group_id,
                telegram_user_id,
                username,
                first_name,
                text,
                sent_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (message_id, thread_id) DO NOTHING
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                query,
                message.message_id,
                message.thread_id,
                message.group_id,
                message.telegram_user_id,
                message.username,
                message.first_name,
                message.text,
                message.sent_at,
            )

    async def list_thread_messages(self, group_id: UUID) -> Sequence[ThreadMessage]:
        """Return stored messages for a group."""
        query = """
            SELECT
                message_id,
                thread_id,
                group_id,
                telegram_user_id,
                username,
                first_name,
                text,
                sent_at
            FROM thread_messages
            WHERE group_id = $1
            ORDER BY sent_at ASC, message_id ASC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, group_id)
        return [_row_to_message(row) for row in rows]

    async def upsert_summary(self, group_id: UUID, content: str) -> Summary:
        """Create or update a summary."""
        query = """
            INSERT INTO summaries (group_id, content)
            VALUES ($1, $2)
            ON CONFLICT (group_id) DO UPDATE
            SET content = EXCLUDED.content, created_at = now()
            RETURNING id, group_id, content, created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, group_id, content)
        if row is None:
            msg = "Summary upsert returned no row."
            raise RuntimeError(msg)
        return _row_to_summary(row)

    async def list_summaries_for_topic(self, topic_id: UUID) -> Sequence[Summary]:
        """Return all summaries for a topic."""
        query = """
            SELECT s.id, s.group_id, s.content, s.created_at
            FROM summaries AS s
            JOIN groups AS g ON g.id = s.group_id
            WHERE g.topic_id = $1
            ORDER BY s.created_at ASC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, topic_id)
        return [_row_to_summary(row) for row in rows]
