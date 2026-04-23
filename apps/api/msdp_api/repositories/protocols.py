"""Repository protocols used by the application."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from msdp_api.db.models import Group, Summary, ThreadMessage, Topic, TopicCreate, User


class Repository(Protocol):
    """Persistence contract for the application."""

    async def get_active_topic(self) -> Topic | None: ...

    async def get_topic(self, topic_id: UUID) -> Topic | None: ...

    async def create_topic(self, payload: TopicCreate) -> Topic: ...

    async def list_groups_for_topic(self, topic_id: UUID) -> Sequence[Group]: ...

    async def find_group_by_thread_id(self, thread_id: int) -> Group | None: ...

    async def create_group(
        self,
        topic_id: UUID,
        thread_id: int,
        invite_link: str,
        capacity: int,
        telegram_topic_name: str,
    ) -> Group: ...

    async def upsert_user(self, user: User) -> User: ...

    async def create_membership(
        self,
        telegram_user_id: int,
        group_id: UUID,
    ) -> bool: ...

    async def remove_membership(
        self,
        telegram_user_id: int,
        group_id: UUID,
    ) -> bool: ...

    async def increment_group_member_count(self, group_id: UUID) -> None: ...

    async def decrement_group_member_count(self, group_id: UUID) -> None: ...

    async def store_thread_message(self, message: ThreadMessage) -> None: ...

    async def list_thread_messages(self, group_id: UUID) -> Sequence[ThreadMessage]: ...

    async def upsert_summary(self, group_id: UUID, content: str) -> Summary: ...

    async def list_summaries_for_topic(self, topic_id: UUID) -> Sequence[Summary]: ...
