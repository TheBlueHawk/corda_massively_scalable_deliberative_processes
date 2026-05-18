"""Postgres repository implementation backed by asyncpg."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg

from msdp_api.db.models import (
    Group,
    Participant,
    Summary,
    ThreadMessage,
    Topic,
    TopicCreate,
    TopicStatus,
    TopicUpdate,
    User,
)


def _row_to_topic(row: asyncpg.Record) -> Topic:
    """Convert a topic row into a model."""
    return Topic(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        status=TopicStatus(row["status"]),
        closes_at=row["closes_at"],
        cross_pollination_interval_seconds=row["cross_pollination_interval_seconds"],
        next_cross_pollination_at=row["next_cross_pollination_at"],
        group_capacity=row["group_capacity"],
        seed_bullets=list(row["seed_bullets"]),
        cover_image_url=row["cover_image_url"],
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
        id=row["id"],
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        group_id=row["group_id"],
        participant_id=row["participant_id"],
        telegram_user_id=row["telegram_user_id"],
        username=row["username"],
        first_name=row["first_name"],
        text=row["text"],
        sent_at=row["sent_at"],
        is_moderator=row["is_moderator"],
    )


class PostgresRepository:
    """Repository implementation using asyncpg."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize the repository."""
        self._pool = pool

    async def get_active_topic(self) -> Topic | None:
        """Return the first active topic."""
        query = """
            SELECT
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
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
            SELECT
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
            FROM topics
            WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, topic_id)
        return _row_to_topic(row) if row else None

    async def list_topics(self) -> Sequence[Topic]:
        """Return all public topics, newest first."""
        query = """
            SELECT
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
            FROM topics
            ORDER BY created_at DESC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
        return [_row_to_topic(row) for row in rows]

    async def list_due_topics(self, now: datetime) -> Sequence[Topic]:
        """Return active topics whose close time has passed."""
        query = """
            SELECT
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
            FROM topics
            WHERE status = 'active'
                AND closes_at IS NOT NULL
                AND closes_at <= $1
            ORDER BY closes_at ASC, created_at ASC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, now)
        return [_row_to_topic(row) for row in rows]

    async def list_cross_pollination_due_topics(self, now: datetime) -> Sequence[Topic]:
        """Return active topics whose cross-pollination cadence is due."""
        query = """
            SELECT
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
            FROM topics
            WHERE status = 'active'
                AND next_cross_pollination_at IS NOT NULL
                AND next_cross_pollination_at <= $1
            ORDER BY next_cross_pollination_at ASC, created_at ASC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, now)
        return [_row_to_topic(row) for row in rows]

    async def create_topic(self, payload: TopicCreate) -> Topic:
        """Create a topic."""
        query = """
            INSERT INTO topics (
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
            )
            VALUES ($1, $2, 'active', $3, $4, $5, $6, $7, NULL, $8)
            RETURNING
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
        """
        now = datetime.now(UTC)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                payload.title,
                payload.description,
                payload.closes_at,
                payload.cross_pollination_interval_seconds,
                now + timedelta(seconds=payload.cross_pollination_interval_seconds),
                payload.group_capacity,
                payload.seed_bullets,
                now,
            )
        if row is None:
            msg = "Topic insert returned no row."
            raise RuntimeError(msg)
        return _row_to_topic(row)

    async def update_topic(self, topic_id: UUID, payload: TopicUpdate) -> Topic | None:
        """Update a topic's editable fields and derived status."""
        existing = await self.get_topic(topic_id)
        if existing is None:
            return None
        fields_set = payload.model_fields_set
        next_title = payload.title if "title" in fields_set else existing.title
        next_description = (
            payload.description if "description" in fields_set else existing.description
        )
        next_closes_at = payload.closes_at if "closes_at" in fields_set else existing.closes_at
        now = datetime.now(UTC)
        next_status = (
            TopicStatus.ACTIVE
            if next_closes_at is None or next_closes_at > now
            else TopicStatus.CLOSED
        )
        next_interval = (
            payload.cross_pollination_interval_seconds
            if payload.cross_pollination_interval_seconds is not None
            else existing.cross_pollination_interval_seconds
        )
        next_cross_pollination_at = existing.next_cross_pollination_at
        if (
            payload.cross_pollination_interval_seconds is not None
            and next_status == TopicStatus.ACTIVE
        ):
            next_cross_pollination_at = now
        if next_status == TopicStatus.CLOSED:
            next_cross_pollination_at = None
        next_group_capacity = (
            payload.group_capacity
            if payload.group_capacity is not None
            else existing.group_capacity
        )
        next_seed_bullets = (
            payload.seed_bullets if payload.seed_bullets is not None else existing.seed_bullets
        )
        query = """
            UPDATE topics
            SET
                title = $2,
                description = $3,
                closes_at = $4,
                status = $5,
                cross_pollination_interval_seconds = $6,
                next_cross_pollination_at = $7,
                group_capacity = $8,
                seed_bullets = $9
            WHERE id = $1
            RETURNING
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                query,
                topic_id,
                next_title,
                next_description,
                next_closes_at,
                next_status.value,
                next_interval,
                next_cross_pollination_at,
                next_group_capacity,
                next_seed_bullets,
            )
        return _row_to_topic(row) if row else None

    async def set_topic_cover_image_url(
        self,
        topic_id: UUID,
        cover_image_url: str,
    ) -> Topic | None:
        """Persist a generated cover image URL for the topic."""
        query = """
            UPDATE topics
            SET cover_image_url = $2
            WHERE id = $1
            RETURNING
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, topic_id, cover_image_url)
        return _row_to_topic(row) if row else None

    async def schedule_next_cross_pollination(
        self,
        topic_id: UUID,
        next_run_at: datetime | None,
    ) -> Topic | None:
        """Set the next cross-pollination run for a topic."""
        query = """
            UPDATE topics
            SET next_cross_pollination_at = $2
            WHERE id = $1
            RETURNING
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, topic_id, next_run_at)
        return _row_to_topic(row) if row else None

    async def close_topic(self, topic_id: UUID) -> Topic | None:
        """Mark a topic as closed."""
        query = """
            UPDATE topics
            SET status = 'closed', next_cross_pollination_at = NULL
            WHERE id = $1
            RETURNING
                id,
                title,
                description,
                status,
                closes_at,
                cross_pollination_interval_seconds,
                next_cross_pollination_at,
                group_capacity,
                seed_bullets,
                cover_image_url,
                created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, topic_id)
        return _row_to_topic(row) if row else None

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
        thread_id: int | None,
        invite_link: str | None,
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
        """Store a thread message (Telegram-originated)."""
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
            ON CONFLICT (message_id, thread_id)
            WHERE message_id IS NOT NULL AND thread_id IS NOT NULL
            DO NOTHING
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
                id,
                message_id,
                thread_id,
                group_id,
                participant_id,
                telegram_user_id,
                username,
                first_name,
                text,
                sent_at,
                is_moderator
            FROM thread_messages
            WHERE group_id = $1
            ORDER BY sent_at ASC, id ASC
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

    async def create_participant(self, display_name: str) -> Participant:
        """Create a new web participant."""
        query = """
            INSERT INTO participants (display_name)
            VALUES ($1)
            RETURNING id, display_name, created_at
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, display_name)
        if row is None:
            msg = "Participant insert returned no row."
            raise RuntimeError(msg)
        return Participant(
            id=row["id"], display_name=row["display_name"], created_at=row["created_at"]
        )

    async def get_participant(self, participant_id: UUID) -> Participant | None:
        """Return a participant by id."""
        query = "SELECT id, display_name, created_at FROM participants WHERE id = $1"
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, participant_id)
        if row is None:
            return None
        return Participant(
            id=row["id"], display_name=row["display_name"], created_at=row["created_at"]
        )

    async def get_participant_group_for_topic(
        self,
        participant_id: UUID,
        topic_id: UUID,
    ) -> Group | None:
        """Return the group the participant belongs to for the given topic."""
        query = """
            SELECT g.id, g.topic_id, g.thread_id, g.invite_link,
                   g.capacity, g.member_count, g.telegram_topic_name
            FROM groups g
            JOIN memberships m ON m.group_id = g.id
            WHERE m.participant_id = $1
              AND g.topic_id = $2
            LIMIT 1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, participant_id, topic_id)
        return _row_to_group(row) if row else None

    async def get_group(self, group_id: UUID) -> Group | None:
        """Return a group by id."""
        query = """
            SELECT id, topic_id, thread_id, invite_link, capacity,
                   member_count, telegram_topic_name
            FROM groups WHERE id = $1
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, group_id)
        return _row_to_group(row) if row else None

    async def create_web_membership(self, participant_id: UUID, group_id: UUID) -> bool:
        """Insert web membership when missing; returns True if created."""
        query = """
            INSERT INTO memberships (participant_id, group_id)
            VALUES ($1, $2)
            ON CONFLICT (participant_id, group_id)
            WHERE participant_id IS NOT NULL
            DO NOTHING
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(query, participant_id, group_id)
        return result.endswith("1")

    async def store_web_message(
        self,
        group_id: UUID,
        participant_id: UUID | None,
        display_name: str,
        text: str,
        *,
        is_moderator: bool = False,
    ) -> ThreadMessage:
        """Persist a web-originated chat message and return the stored record."""
        query = """
            INSERT INTO thread_messages
                (group_id, participant_id, first_name, text, sent_at, is_moderator)
            VALUES ($1, $2, $3, $4, now(), $5)
            RETURNING id, message_id, thread_id, group_id, participant_id,
                      telegram_user_id, username, first_name, text, sent_at, is_moderator
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                query, group_id, participant_id, display_name, text, is_moderator
            )
        if row is None:
            msg = "Message insert returned no row."
            raise RuntimeError(msg)
        return _row_to_message(row)

    async def list_messages_for_group(self, group_id: UUID) -> Sequence[ThreadMessage]:
        """Return all messages for a group ordered by sent_at."""
        query = """
            SELECT id, message_id, thread_id, group_id, participant_id,
                   telegram_user_id, username, first_name, text, sent_at, is_moderator
            FROM thread_messages
            WHERE group_id = $1
            ORDER BY sent_at ASC, id ASC
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, group_id)
        return [_row_to_message(row) for row in rows]
