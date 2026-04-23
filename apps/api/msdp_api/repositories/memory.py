"""In-memory repository for tests."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from msdp_api.db.models import Group, Summary, ThreadMessage, Topic, TopicCreate, TopicStatus, User


class InMemoryRepository:
    """Simple in-memory repository implementation."""

    def __init__(self) -> None:
        """Initialize empty storage."""
        self.topics: dict[UUID, Topic] = {}
        self.groups: dict[UUID, Group] = {}
        self.users: dict[int, User] = {}
        self.memberships: set[tuple[int, UUID]] = set()
        self.messages: dict[UUID, list[ThreadMessage]] = defaultdict(list)
        self.summaries: dict[UUID, Summary] = {}

    async def get_active_topic(self) -> Topic | None:
        """Return the first active topic ordered by creation time."""
        active = [topic for topic in self.topics.values() if topic.status == TopicStatus.ACTIVE]
        active.sort(key=lambda item: item.created_at)
        return active[0] if active else None

    async def get_topic(self, topic_id: UUID) -> Topic | None:
        """Return a topic by id."""
        return self.topics.get(topic_id)

    async def create_topic(self, payload: TopicCreate) -> Topic:
        """Create and store a topic."""
        topic = Topic(
            id=uuid4(),
            title=payload.title,
            description=payload.description,
            status=TopicStatus.ACTIVE,
            closes_at=payload.closes_at,
            created_at=datetime.now(UTC),
        )
        self.topics[topic.id] = topic
        return topic

    async def list_groups_for_topic(self, topic_id: UUID) -> list[Group]:
        """Return groups belonging to the topic."""
        return [group for group in self.groups.values() if group.topic_id == topic_id]

    async def find_group_by_thread_id(self, thread_id: int) -> Group | None:
        """Return the group that owns a Telegram thread id."""
        return next(
            (group for group in self.groups.values() if group.thread_id == thread_id),
            None,
        )

    async def create_group(
        self,
        topic_id: UUID,
        thread_id: int,
        invite_link: str,
        capacity: int,
        telegram_topic_name: str,
    ) -> Group:
        """Create a group."""
        group = Group(
            id=uuid4(),
            topic_id=topic_id,
            thread_id=thread_id,
            invite_link=invite_link,
            capacity=capacity,
            member_count=0,
            telegram_topic_name=telegram_topic_name,
        )
        self.groups[group.id] = group
        return group

    async def upsert_user(self, user: User) -> User:
        """Insert or update a user."""
        self.users[user.telegram_user_id] = user
        return user

    async def create_membership(self, telegram_user_id: int, group_id: UUID) -> bool:
        """Insert membership when missing."""
        key = (telegram_user_id, group_id)
        if key in self.memberships:
            return False
        self.memberships.add(key)
        return True

    async def remove_membership(self, telegram_user_id: int, group_id: UUID) -> bool:
        """Remove membership when present."""
        key = (telegram_user_id, group_id)
        if key not in self.memberships:
            return False
        self.memberships.remove(key)
        return True

    async def increment_group_member_count(self, group_id: UUID) -> None:
        """Increase the group member count."""
        group = self.groups[group_id]
        self.groups[group_id] = group.model_copy(update={"member_count": group.member_count + 1})

    async def decrement_group_member_count(self, group_id: UUID) -> None:
        """Decrease the group member count."""
        group = self.groups[group_id]
        next_count = max(group.member_count - 1, 0)
        self.groups[group_id] = group.model_copy(update={"member_count": next_count})

    async def store_thread_message(self, message: ThreadMessage) -> None:
        """Persist a captured thread message."""
        bucket = self.messages[message.group_id]
        if any(item.message_id == message.message_id for item in bucket):
            return
        bucket.append(message)

    async def list_thread_messages(self, group_id: UUID) -> list[ThreadMessage]:
        """Return stored thread messages for a group."""
        return list(self.messages[group_id])

    async def upsert_summary(self, group_id: UUID, content: str) -> Summary:
        """Create or update a summary."""
        summary = Summary(
            id=self.summaries.get(
                group_id,
                Summary(
                    id=uuid4(),
                    group_id=group_id,
                    content=content,
                    created_at=datetime.now(UTC),
                ),
            ).id,
            group_id=group_id,
            content=content,
            created_at=datetime.now(UTC),
        )
        self.summaries[group_id] = summary
        return summary

    async def list_summaries_for_topic(self, topic_id: UUID) -> list[Summary]:
        """Return summaries for groups belonging to a topic."""
        topic_group_ids = {
            group.id for group in self.groups.values() if group.topic_id == topic_id
        }
        return [
            summary for group_id, summary in self.summaries.items() if group_id in topic_group_ids
        ]
