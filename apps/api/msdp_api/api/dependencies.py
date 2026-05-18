"""FastAPI dependency helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

import asyncpg
from fastapi import Depends, Header, HTTPException, Request, status

from msdp_api.core.config import Settings, get_settings
from msdp_api.repositories.postgres import PostgresRepository
from msdp_api.repositories.protocols import Repository
from msdp_api.services.cover_image import CoverImageService
from msdp_api.services.summarization import OpenAISummarizer, SummarizationService
from msdp_api.services.topic_suggestion import TopicSuggesterProtocol, TopicSuggestionService


def get_runtime_settings(request: Request) -> Settings:
    """Return settings from app state when available, else from the environment."""
    return getattr(request.app.state, "settings", None) or get_settings()


async def get_repository(request: Request) -> AsyncGenerator[Repository]:
    """Yield a repository backed by a short-lived per-request DB connection.

    In test mode (repository pre-injected on app.state) the existing instance
    is yielded directly without opening a new connection.
    """
    if hasattr(request.app.state, "repository"):
        yield request.app.state.repository
        return
    settings = get_runtime_settings(request)
    conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
    try:
        yield PostgresRepository(conn)
    finally:
        await conn.close()


def get_summarization_service(
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
) -> SummarizationService:
    """Return a summarization service scoped to the current request."""
    if hasattr(request.app.state, "summarization_service"):
        return request.app.state.summarization_service  # type: ignore[no-any-return]
    settings = get_runtime_settings(request)
    return SummarizationService(
        repository=repository,
        summarizer=OpenAISummarizer(
            client=request.app.state.openai_client,
            model=settings.summary_model,
        ),
    )


def get_cover_image_service(
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
) -> CoverImageService:
    """Return a cover image service scoped to the current request."""
    if hasattr(request.app.state, "cover_image_service"):
        return request.app.state.cover_image_service  # type: ignore[no-any-return]
    settings = get_runtime_settings(request)
    return CoverImageService(
        repository=repository,
        client=request.app.state.openai_client,
        model=settings.cover_image_model,
        blob_token=settings.blob_read_write_token,
    )


def get_topic_suggestion_service(request: Request) -> TopicSuggesterProtocol:
    """Return a topic suggestion service scoped to the current request."""
    if hasattr(request.app.state, "topic_suggestion_service"):
        return request.app.state.topic_suggestion_service  # type: ignore[no-any-return]
    settings = get_runtime_settings(request)
    return TopicSuggestionService(
        client=request.app.state.openai_client,
        model=settings.summary_model,
    )


def require_admin_key(
    request: Request,
    x_admin_key: Annotated[str, Header(alias="X-Admin-Key")],
) -> None:
    """Validate the admin header."""
    settings = get_runtime_settings(request)
    if x_admin_key != settings.x_admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key.")
