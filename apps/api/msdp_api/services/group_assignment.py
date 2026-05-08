"""Group assignment logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from msdp_api.db.models import GroupAssignmentResult, Topic, User

if TYPE_CHECKING:
    from uuid import UUID

    from msdp_api.repositories.protocols import Repository
    from msdp_api.telegram.gateway import TelegramGateway


def _build_seed_message(bullets: list[str]) -> str:
    """Format seed talking points as a moderator comment posted into a new group."""
    rendered = "\n".join(f"• {bullet}" for bullet in bullets)
    return f"To get the conversation started, here are a few angles to weigh in on:\n\n{rendered}"


class GroupAssignmentService:
    """Assign users to the least-full available group for a topic."""

    def __init__(
        self,
        repository: Repository,
        telegram_gateway: TelegramGateway,
    ) -> None:
        """Initialize the service."""
        self._repository = repository
        self._telegram_gateway = telegram_gateway

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
            key=lambda item: (item.member_count, item.thread_id),
        )
        group = next((item for item in groups if item.member_count < item.capacity), None)
        was_created = False
        if group is None:
            telegram_group = await self._telegram_gateway.create_group(
                ordinal=len(groups) + 1,
                capacity=topic.group_capacity,
                topic_title=topic.title,
            )
            group = await self._repository.create_group(
                topic_id=topic_id,
                thread_id=telegram_group.thread_id,
                invite_link=telegram_group.invite_link,
                capacity=topic.group_capacity,
                telegram_topic_name=telegram_group.topic_name,
            )
            was_created = True
            if topic.seed_bullets:
                seed_message = _build_seed_message(topic.seed_bullets)
                await self._telegram_gateway.send_moderator_comment(
                    thread_id=group.thread_id,
                    text=seed_message,
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

        await self._telegram_gateway.send_assignment_message(
            chat_id=user.telegram_user_id,
            thread_id=group.thread_id,
            invite_link=group.invite_link,
            topic_title=topic.title,
        )
        return GroupAssignmentResult(
            group=group,
            was_created=was_created,
            already_member=not created_membership,
        )
