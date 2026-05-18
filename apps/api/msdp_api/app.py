"""FastAPI application factory."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from typing import TYPE_CHECKING

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from msdp_api.api.routes_admin import router as admin_router
from msdp_api.api.routes_chat import router as chat_router
from msdp_api.api.routes_public import router as public_router
from msdp_api.core.config import Settings, get_settings
from msdp_api.db.migrations import apply_migrations
from msdp_api.repositories.memory import InMemoryRepository
from msdp_api.repositories.postgres import PostgresRepository
from msdp_api.services.cover_image import CoverImageService
from msdp_api.services.summarization import OpenAISummarizer, SummarizationService, Summarizer
from msdp_api.services.topic_suggestion import TopicSuggesterProtocol, TopicSuggestionService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from uuid import UUID

    from msdp_api.repositories.protocols import Repository

logger = logging.getLogger(__name__)


async def _run_due_summarization_loop(
    summarization_service: SummarizationService,
    interval_seconds: int,
) -> None:
    """Periodically run due close summaries and active-topic cross-pollination."""
    while True:
        try:
            await summarization_service.summarize_due_topics()
            await summarization_service.cross_pollinate_due_topics()
        except Exception:
            logger.exception("Failed to run due summarization jobs.")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create runtime resources for the application."""
    settings = get_settings()
    pool: asyncpg.Pool | None = None
    try:
        pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=0,
            max_inactive_connection_lifetime=60,
        )
        await apply_migrations(pool)
    except Exception:
        logger.exception(
            "Database unavailable at startup; DB-dependent endpoints will return errors."
        )
    repository = PostgresRepository(pool) if pool is not None else InMemoryRepository()
    summarization_service = SummarizationService(
        repository=repository,
        summarizer=OpenAISummarizer(
            client=AsyncOpenAI(api_key=settings.openai_api_key),
            model=settings.summary_model,
        ),
    )
    cover_image_service = CoverImageService(
        repository=repository,
        client=AsyncOpenAI(api_key=settings.openai_api_key),
        model=settings.cover_image_model,
        blob_token=settings.blob_read_write_token,
    )
    topic_suggestion_service = TopicSuggestionService(
        client=AsyncOpenAI(api_key=settings.openai_api_key),
        model=settings.summary_model,
    )
    app.state.settings = settings
    app.state.pool = pool
    app.state.repository = repository
    app.state.summarization_service = summarization_service
    app.state.cover_image_service = cover_image_service
    app.state.topic_suggestion_service = topic_suggestion_service
    app.state.group_subscribers: dict[UUID, list[asyncio.Queue]] = {}  # type: ignore[assignment]
    summary_task = asyncio.create_task(
        _run_due_summarization_loop(
            summarization_service=summarization_service,
            interval_seconds=settings.summary_check_interval_seconds,
        ),
    )
    app.state.summary_task = summary_task
    try:
        yield
    finally:
        summary_task.cancel()
        with suppress(asyncio.CancelledError):
            await summary_task
        if pool is not None:
            await pool.close()


def create_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
    summarizer: Summarizer | None = None,
    topic_suggestion_service: TopicSuggesterProtocol | None = None,
) -> FastAPI:
    """Build the FastAPI application."""
    app = FastAPI(
        title="CORDA Deliberation API",
        lifespan=lifespan if settings is None and repository is None else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-Admin-Key", "X-Participant-Id"],
    )
    app.include_router(public_router)
    app.include_router(chat_router)
    app.include_router(admin_router)

    if repository is not None:
        runtime_settings = settings or get_settings()
        runtime_repository = repository
        runtime_summarizer = summarizer or OpenAISummarizer(
            client=AsyncOpenAI(api_key=runtime_settings.openai_api_key),
            model=runtime_settings.summary_model,
        )
        app.state.settings = runtime_settings
        app.state.repository = runtime_repository
        app.state.summarization_service = SummarizationService(
            repository=runtime_repository,
            summarizer=runtime_summarizer,
        )
        app.state.cover_image_service = CoverImageService(
            repository=runtime_repository,
            client=AsyncOpenAI(api_key=runtime_settings.openai_api_key),
            model=runtime_settings.cover_image_model,
            blob_token=runtime_settings.blob_read_write_token,
        )
        app.state.topic_suggestion_service = topic_suggestion_service or TopicSuggestionService(
            client=AsyncOpenAI(api_key=runtime_settings.openai_api_key),
            model=runtime_settings.summary_model,
        )
        app.state.group_subscribers: dict[UUID, list[asyncio.Queue]] = {}  # type: ignore[assignment]
    return app


def create_test_app(settings: Settings) -> FastAPI:
    """Build a test application with in-memory persistence."""
    return create_app(settings=settings, repository=InMemoryRepository())
