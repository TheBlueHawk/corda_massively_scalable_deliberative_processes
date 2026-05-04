"""FastAPI application factory."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from typing import TYPE_CHECKING

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from msdp_api.api.routes_admin import router as admin_router
from msdp_api.api.routes_public import router as public_router
from msdp_api.api.routes_webhook import router as webhook_router
from msdp_api.core.config import Settings, get_settings
from msdp_api.repositories.memory import InMemoryRepository
from msdp_api.repositories.postgres import PostgresRepository
from msdp_api.services.group_assignment import GroupAssignmentService
from msdp_api.services.summarization import AnthropicSummarizer, SummarizationService, Summarizer
from msdp_api.telegram.gateway import TelegramBotGateway, TelegramGateway
from msdp_api.telegram.service import TelegramWebhookService

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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
    pool = await asyncpg.create_pool(settings.database_url)
    repository = PostgresRepository(pool)
    telegram_gateway = TelegramBotGateway(
        token=settings.telegram_bot_token,
        supergroup_id=settings.telegram_supergroup_id,
    )
    group_assignment_service = GroupAssignmentService(
        repository=repository,
        telegram_gateway=telegram_gateway,
        group_capacity=settings.group_capacity,
    )
    summarization_service = SummarizationService(
        repository=repository,
        summarizer=AnthropicSummarizer(
            api_key=settings.anthropic_api_key,
            model=settings.summary_model,
        ),
        telegram_gateway=telegram_gateway,
    )
    app.state.settings = settings
    app.state.pool = pool
    app.state.repository = repository
    app.state.group_assignment_service = group_assignment_service
    app.state.summarization_service = summarization_service
    summary_task = asyncio.create_task(
        _run_due_summarization_loop(
            summarization_service=summarization_service,
            interval_seconds=settings.summary_check_interval_seconds,
        ),
    )
    app.state.summary_task = summary_task
    app.state.telegram_webhook_service = TelegramWebhookService(
        repository=repository,
        group_assignment_service=group_assignment_service,
    )
    try:
        yield
    finally:
        summary_task.cancel()
        with suppress(asyncio.CancelledError):
            await summary_task
        await pool.close()


def create_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
    telegram_gateway: TelegramGateway | None = None,
    summarizer: Summarizer | None = None,
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
        allow_headers=["Content-Type", "X-Admin-Key"],
    )
    app.include_router(public_router)
    app.include_router(webhook_router)
    app.include_router(admin_router)

    if repository is not None:
        runtime_settings = settings or get_settings()
        runtime_repository = repository
        runtime_gateway = telegram_gateway or TelegramBotGateway(
            token=runtime_settings.telegram_bot_token,
            supergroup_id=runtime_settings.telegram_supergroup_id,
        )
        group_assignment_service = GroupAssignmentService(
            repository=runtime_repository,
            telegram_gateway=runtime_gateway,
            group_capacity=runtime_settings.group_capacity,
        )
        runtime_summarizer = summarizer or AnthropicSummarizer(
            api_key=runtime_settings.anthropic_api_key,
            model=runtime_settings.summary_model,
        )
        app.state.settings = runtime_settings
        app.state.repository = runtime_repository
        app.state.group_assignment_service = group_assignment_service
        app.state.summarization_service = SummarizationService(
            repository=runtime_repository,
            summarizer=runtime_summarizer,
            telegram_gateway=runtime_gateway,
        )
        app.state.telegram_webhook_service = TelegramWebhookService(
            repository=runtime_repository,
            group_assignment_service=group_assignment_service,
        )
    return app


def create_test_app(settings: Settings) -> FastAPI:
    """Build a test application with in-memory persistence."""
    return create_app(settings=settings, repository=InMemoryRepository())
