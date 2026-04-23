"""Telegram webhook handling service."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status

from msdp_api.db.models import ThreadMessage, User
from msdp_api.telegram.models import TelegramMessagePayload, TelegramWebhookPayload

if TYPE_CHECKING:
    from msdp_api.repositories.protocols import Repository
    from msdp_api.services.group_assignment import GroupAssignmentService


START_PARTS_LENGTH = 2


class TelegramWebhookService:
    """Handle Telegram webhook updates."""

    def __init__(
        self,
        repository: Repository,
        group_assignment_service: GroupAssignmentService,
    ) -> None:
        """Initialize the service."""
        self._repository = repository
        self._group_assignment_service = group_assignment_service

    async def handle_update(self, payload: TelegramWebhookPayload) -> dict[str, bool]:
        """Dispatch the webhook update to the appropriate handler."""
        if payload.message is not None:
            await self._handle_message(payload)
        if payload.chat_member is not None:
            await self._handle_chat_member(payload)
        return {"ok": True}

    async def _handle_message(self, payload: TelegramWebhookPayload) -> None:
        """Handle a Telegram message update."""
        message = payload.message
        if message is None:
            return
        text = message.content_text
        if text and text.startswith("/start"):
            await self._handle_start_command(text, message)
            return
        thread_id = message.message_thread_id
        if thread_id is None or not text:
            return
        group = await self._repository.find_group_by_thread_id(thread_id)
        if group is None:
            return
        sender = message.from_
        await self._repository.store_thread_message(
            ThreadMessage(
                message_id=message.message_id,
                thread_id=thread_id,
                group_id=group.id,
                telegram_user_id=sender.id if sender else None,
                username=sender.username if sender else None,
                first_name=sender.first_name if sender else None,
                text=text,
                sent_at=message.sent_at,
            ),
        )

    async def _handle_start_command(
        self,
        text: str,
        message: TelegramMessagePayload,
    ) -> None:
        """Handle the `/start <topic_id>` Telegram command."""
        parts = text.split(maxsplit=1)
        if len(parts) != START_PARTS_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing topic id in /start command.",
            )
        try:
            topic_id = UUID(parts[1])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid topic id in /start command.",
            ) from exc
        topic = await self._repository.get_topic(topic_id)
        if topic is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown topic.")
        sender = message.from_
        if sender is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram update missing sender.",
            )
        await self._group_assignment_service.assign_user_to_topic(
            topic_id=topic.id,
            topic=topic,
            user=User(
                telegram_user_id=sender.id,
                username=sender.username,
                first_name=sender.first_name,
            ),
        )

    async def _handle_chat_member(self, payload: TelegramWebhookPayload) -> None:
        """Handle join and leave updates."""
        chat_member = payload.chat_member
        if (
            chat_member is None
            or chat_member.message_thread_id is None
            or chat_member.from_ is None
        ):
            return
        group = await self._repository.find_group_by_thread_id(chat_member.message_thread_id)
        if group is None:
            return
        old_status = chat_member.old_chat_member.get("status")
        new_status = chat_member.new_chat_member.get("status")
        if old_status in {"left", "kicked"} and new_status in {"member", "administrator"}:
            created = await self._repository.create_membership(chat_member.from_.id, group.id)
            if created:
                await self._repository.increment_group_member_count(group.id)
        if old_status in {"member", "administrator"} and new_status in {"left", "kicked"}:
            removed = await self._repository.remove_membership(chat_member.from_.id, group.id)
            if removed:
                await self._repository.decrement_group_member_count(group.id)
