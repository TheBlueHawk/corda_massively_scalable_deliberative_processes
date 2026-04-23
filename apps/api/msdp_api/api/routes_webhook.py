"""Telegram webhook API route."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from msdp_api.api.dependencies import get_telegram_webhook_service
from msdp_api.telegram.models import TelegramWebhookPayload
from msdp_api.telegram.service import TelegramWebhookService

router = APIRouter()


@router.post("/webhook/telegram")
async def telegram_webhook(
    payload: TelegramWebhookPayload,
    service: Annotated[TelegramWebhookService, Depends(get_telegram_webhook_service)],
) -> dict[str, bool]:
    """Handle Telegram webhook callbacks."""
    return await service.handle_update(payload)
