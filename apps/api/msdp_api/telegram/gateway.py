"""Telegram bot gateway abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from telegram import Bot


@dataclass(slots=True)
class CreatedTelegramGroup:
    """Telegram resources created for a new deliberation group."""

    thread_id: int
    invite_link: str
    topic_name: str


class TelegramGateway(Protocol):
    """Protocol for Telegram side effects."""

    async def create_group(self, ordinal: int, capacity: int) -> CreatedTelegramGroup: ...

    async def send_assignment_message(
        self,
        chat_id: int,
        thread_id: int,
        invite_link: str,
        topic_title: str,
    ) -> None: ...


class TelegramBotGateway:
    """Production Telegram gateway backed by python-telegram-bot."""

    def __init__(self, token: str, supergroup_id: int) -> None:
        """Initialize the gateway with bot credentials."""
        self._supergroup_id = supergroup_id
        self._bot = Bot(token)

    async def create_group(self, ordinal: int, capacity: int) -> CreatedTelegramGroup:
        """Create a new forum topic and invite link."""
        topic_name = f"Group {ordinal}"
        topic = await self._bot.create_forum_topic(
            chat_id=self._supergroup_id,
            name=topic_name,
        )
        invite = await self._bot.create_chat_invite_link(
            chat_id=self._supergroup_id,
            member_limit=capacity,
            name=topic_name,
        )
        return CreatedTelegramGroup(
            thread_id=topic.message_thread_id,
            invite_link=invite.invite_link,
            topic_name=topic_name,
        )

    async def send_assignment_message(
        self,
        chat_id: int,
        thread_id: int,
        invite_link: str,
        topic_title: str,
    ) -> None:
        """Send an assignment message to the user via direct message."""
        await self._bot.send_message(
            chat_id=chat_id,
            text=(
                f"Your discussion group for '{topic_title}' is ready.\n\n"
                f"Join the supergroup: {invite_link}\n"
                f"Then open forum topic #{thread_id} in the sidebar."
            ),
        )
