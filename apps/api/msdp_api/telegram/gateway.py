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


_FORUM_ICON_COLORS: tuple[int, ...] = (
    7322096,
    16766590,
    13338331,
    9367192,
    16749490,
    16478047,
)


def pick_forum_icon_color(seed: str) -> int:
    """Map an arbitrary string to one of Telegram's six allowed forum icon colors.

    Telegram only accepts these six integer values for `icon_color`; arbitrary RGB
    values are rejected. Using a stable hash of the topic id (or title) gives each
    debate its own consistent badge color in the participant's forum sidebar.
    """
    digest = sum(ord(character) for character in seed)
    return _FORUM_ICON_COLORS[digest % len(_FORUM_ICON_COLORS)]


class TelegramGateway(Protocol):
    """Protocol for Telegram side effects."""

    async def create_group(
        self,
        ordinal: int,
        capacity: int,
        topic_title: str,
        icon_color: int,
    ) -> CreatedTelegramGroup: ...

    async def send_assignment_message(
        self,
        chat_id: int,
        thread_id: int,
        invite_link: str,
        topic_title: str,
    ) -> None: ...

    async def send_moderator_comment(self, thread_id: int, text: str) -> None: ...


_MAX_TOPIC_TITLE_PREFIX = 60


def _build_topic_name(topic_title: str, ordinal: int) -> str:
    """Build a forum topic name that is unique across debates.

    Telegram caps forum topic names at 128 characters; the title prefix is
    truncated to leave room for the group ordinal suffix.
    """
    prefix = topic_title.strip()[:_MAX_TOPIC_TITLE_PREFIX].rstrip()
    return f"{prefix} · Group {ordinal}" if prefix else f"Group {ordinal}"


def build_assignment_message(invite_link: str, thread_id: int, topic_title: str) -> str:
    """Build the direct Telegram welcome message for a group assignment."""
    return (
        "Welcome to the CORDA Deliberation Group Chat.\n\n"
        "Here, you can take part in structured conversations on topics that matter to all "
        "of us.\n\n"
        f"Below is your link to join a group to discuss {topic_title}:\n"
        f"{invite_link}\n\n"
        f"After joining, open forum topic #{thread_id} in the sidebar.\n\n"
        "Once inside a group:\n"
        "- Read through the description and the main arguments\n"
        "- Take a moment to read what others have shared\n"
        "- Add your perspective\n"
        "- Stay open to different viewpoints\n\n"
        "Please remember: There are no right or wrong opinions - just different perspectives to "
        'explore together. You don\'t need to have the "perfect" answer - just start '
        "where you are. "
        "We encourage thoughtful contributions, clarity, and respectful exchange."
    )


class TelegramBotGateway:
    """Production Telegram gateway backed by python-telegram-bot."""

    def __init__(self, token: str, supergroup_id: int) -> None:
        """Initialize the gateway with bot credentials."""
        self._supergroup_id = supergroup_id
        self._bot = Bot(token)

    async def create_group(
        self,
        ordinal: int,
        capacity: int,
        topic_title: str,
        icon_color: int,
    ) -> CreatedTelegramGroup:
        """Create a new forum topic and invite link.

        The Telegram forum topic name and invite-link label are prefixed with the
        deliberation topic title so participants can distinguish groups across
        successive debates in the same supergroup. ``icon_color`` controls the
        forum-topic badge color (Telegram restricts this to one of six fixed
        integers — see ``pick_forum_icon_color``).
        """
        topic_name = _build_topic_name(topic_title=topic_title, ordinal=ordinal)
        topic = await self._bot.create_forum_topic(
            chat_id=self._supergroup_id,
            name=topic_name,
            icon_color=icon_color,
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
            text=build_assignment_message(
                invite_link=invite_link,
                thread_id=thread_id,
                topic_title=topic_title,
            ),
        )

    async def send_moderator_comment(self, thread_id: int, text: str) -> None:
        """Post a moderator comment into a Telegram forum topic."""
        await self._bot.send_message(
            chat_id=self._supergroup_id,
            message_thread_id=thread_id,
            text=text,
        )
