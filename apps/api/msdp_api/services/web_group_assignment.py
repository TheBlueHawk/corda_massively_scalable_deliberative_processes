"""Web-native group assignment — no Telegram required."""

from __future__ import annotations

from typing import TYPE_CHECKING

from msdp_api.db.models import Group, Topic

if TYPE_CHECKING:
    from uuid import UUID

    from msdp_api.repositories.protocols import Repository

_MAX_TITLE_PREFIX = 80


def _build_group_name(topic_title: str, ordinal: int) -> str:
    """Build a group display name that is unique within a topic."""
    prefix = topic_title.strip()[:_MAX_TITLE_PREFIX].rstrip()
    return f"{prefix} · Group {ordinal}" if prefix else f"Group {ordinal}"


def _build_seed_message(bullets: list[str]) -> str:
    """Format seed talking points as a moderator message posted into a new group."""
    rendered = "\n".join(f"• {bullet}" for bullet in bullets)
    return f"To get the conversation started, here are a few angles to weigh in on:\n\n{rendered}"


class WebGroupAssignmentResult:
    """Outcome of assigning a participant to a deliberation group."""

    def __init__(self, group: Group, *, was_created: bool, already_member: bool) -> None:
        """Store the assignment result."""
        self.group = group
        self.was_created = was_created
        self.already_member = already_member


class WebGroupAssignmentService:
    """Assign web participants to the least-full available group for a topic."""

    def __init__(self, repository: Repository) -> None:
        """Initialize the service."""
        self._repository = repository

    async def assign_participant(
        self,
        topic_id: UUID,
        participant_id: UUID,
        topic: Topic,
    ) -> WebGroupAssignmentResult:
        """Assign the given participant to an existing or newly created group.

        Returns the assigned group plus flags indicating whether the group was
        newly created and whether the participant was already a member.
        """
        existing = await self._repository.get_participant_group_for_topic(participant_id, topic_id)
        if existing is not None:
            return WebGroupAssignmentResult(group=existing, was_created=False, already_member=True)

        groups = sorted(
            await self._repository.list_groups_for_topic(topic_id),
            key=lambda g: (g.member_count, g.id),
        )
        group = next((g for g in groups if g.member_count < g.capacity), None)
        was_created = False

        if group is None:
            ordinal = len(groups) + 1
            group_name = _build_group_name(topic.title, ordinal)
            group = await self._repository.create_group(
                topic_id=topic_id,
                thread_id=None,
                invite_link=None,
                capacity=topic.group_capacity,
                telegram_topic_name=group_name,
            )
            was_created = True
            if topic.seed_bullets:
                await self._repository.store_web_message(
                    group_id=group.id,
                    participant_id=None,
                    display_name="Moderator",
                    text=_build_seed_message(topic.seed_bullets),
                    is_moderator=True,
                )

        created = await self._repository.create_web_membership(participant_id, group.id)
        if created:
            await self._repository.increment_group_member_count(group.id)
            groups_after = await self._repository.list_groups_for_topic(topic_id)
            group = next(g for g in groups_after if g.id == group.id)

        return WebGroupAssignmentResult(
            group=group, was_created=was_created, already_member=not created
        )
