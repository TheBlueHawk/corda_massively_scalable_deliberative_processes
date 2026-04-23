"""Normalized Telegram webhook payload models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TelegramUserPayload(BaseModel):
    """Relevant Telegram user fields."""

    id: int
    username: str | None = None
    first_name: str | None = None


class TelegramMessagePayload(BaseModel):
    """Relevant Telegram message fields."""

    message_id: int
    date: int
    message_thread_id: int | None = None
    text: str | None = None
    caption: str | None = None
    from_: TelegramUserPayload | None = Field(default=None, alias="from")

    model_config = ConfigDict(populate_by_name=True)

    @property
    def content_text(self) -> str | None:
        """Return the message text or caption, if present."""
        return self.text or self.caption

    @property
    def sent_at(self) -> datetime:
        """Return the message timestamp as UTC datetime."""
        return datetime.fromtimestamp(self.date, tz=UTC)


class TelegramChatMemberPayload(BaseModel):
    """Subset of a chat member update payload."""

    new_chat_member: dict[str, Any]
    old_chat_member: dict[str, Any]
    from_: TelegramUserPayload | None = Field(default=None, alias="from")
    message_thread_id: int | None = None

    model_config = ConfigDict(populate_by_name=True)


class TelegramWebhookPayload(BaseModel):
    """Top-level Telegram webhook payload."""

    update_id: int
    message: TelegramMessagePayload | None = None
    chat_member: TelegramChatMemberPayload | None = None


class TelegramUserIdentity(BaseModel):
    """Normalized user information used internally."""

    telegram_user_id: int
    username: str | None = None
    first_name: str | None = None
