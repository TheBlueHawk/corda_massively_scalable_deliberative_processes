"""FastAPI dependency helpers."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header, HTTPException, Request, status

from msdp_api.core.config import Settings, get_settings
from msdp_api.repositories.protocols import Repository
from msdp_api.services.group_assignment import GroupAssignmentService
from msdp_api.services.summarization import SummarizationService
from msdp_api.telegram.service import TelegramWebhookService


def get_repository(request: Request) -> Repository:
    """Return the repository stored on the application state."""
    return request.app.state.repository


def get_group_assignment_service(request: Request) -> GroupAssignmentService:
    """Return the group assignment service stored on the application state."""
    return request.app.state.group_assignment_service


def get_telegram_webhook_service(request: Request) -> TelegramWebhookService:
    """Return the Telegram webhook service stored on the application state."""
    return request.app.state.telegram_webhook_service


def get_summarization_service(request: Request) -> SummarizationService:
    """Return the summarization service stored on the application state."""
    return request.app.state.summarization_service


def get_runtime_settings(request: Request) -> Settings:
    """Return settings from app state when available, else from the environment."""
    return getattr(request.app.state, "settings", None) or get_settings()


def require_admin_key(
    request: Request,
    x_admin_key: Annotated[str, Header(alias="X-Admin-Key")],
) -> None:
    """Validate the admin header."""
    settings = get_runtime_settings(request)
    if x_admin_key != settings.x_admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key.")
