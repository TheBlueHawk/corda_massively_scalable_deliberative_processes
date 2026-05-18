"""Group assignment logic (kept for backward-compatibility; see web_group_assignment.py)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from msdp_api.db.models import GroupAssignmentResult, Topic, User

if TYPE_CHECKING:
    from uuid import UUID

    from msdp_api.repositories.protocols import Repository


def _build_seed_message(bullets: list[str]) -> str:
    """Format seed talking points as a moderator comment posted into a new group."""
    rendered = "\n".join(f"• {bullet}" for bullet in bullets)
    return f"To get the conversation started, here are a few angles to weigh in on:\n\n{rendered}"


class GroupAssignmentService:
    """Assign users to the least-full available group for a topic."""

    def __init__(
        self,
        repository: Repository,
    ) -> None:
        """Initialize the service."""
        self._repository = repository

    async def assign_user_to_topic(
        self,
        topic_id: UUID,
        user: User,
        topic: Topic,
    ) -> GroupAssignmentResult:
        """Assign the given user to an existing or newly created group."""
        await self._repository.upsert_user(user)
        groups = sorted(
            await self._repository.list_groups_for_topic(topic_id),
            key=lambda item: (item.member_count, item.thread_id or 0),
        )
        group = next((item for item in groups if item.member_count < item.capacity), None)
        was_created = False
        if group is None:
            ordinal = len(groups) + 1
            group_name = f"{topic.title[:80].rstrip()} · Group {ordinal}"
            group = await self._repository.create_group(
                topic_id=topic_id,
                thread_id=None,
                invite_link=None,
                capacity=topic.group_capacity,
                telegram_topic_name=group_name,
            )
            was_created = True
            if topic.seed_bullets:
                seed_message = _build_seed_message(topic.seed_bullets)
                await self._repository.store_web_message(
                    group_id=group.id,
                    participant_id=None,
                    display_name="Moderator",
                    text=seed_message,
                    is_moderator=True,
                )

        created_membership = await self._repository.create_membership(
            telegram_user_id=user.telegram_user_id,
            group_id=group.id,
        )
        if created_membership:
            await self._repository.increment_group_member_count(group.id)
            group = next(
                item
                for item in await self._repository.list_groups_for_topic(topic_id)
                if item.id == group.id
            )

        return GroupAssignmentResult(
            group=group,
            was_created=was_created,
            already_member=not created_membership,
        )
