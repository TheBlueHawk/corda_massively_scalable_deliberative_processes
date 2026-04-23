"""Admin API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from msdp_api.api.dependencies import (
    get_repository,
    get_summarization_service,
    require_admin_key,
)
from msdp_api.db.models import SummarizationResult, TopicCreate, TopicCreatedResponse
from msdp_api.repositories.protocols import Repository
from msdp_api.services.summarization import SummarizationService

router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin_key)],
)


@router.post("/topics", response_model=TopicCreatedResponse)
async def create_topic(
    payload: TopicCreate,
    repository: Annotated[Repository, Depends(get_repository)],
) -> TopicCreatedResponse:
    """Create a new topic."""
    topic = await repository.create_topic(payload)
    return TopicCreatedResponse(topic=topic)


@router.post("/summarize/{topic_id}", response_model=SummarizationResult)
async def summarize_topic(
    topic_id: UUID,
    summarization_service: Annotated[SummarizationService, Depends(get_summarization_service)],
) -> SummarizationResult:
    """Trigger summarization for a topic."""
    return await summarization_service.summarize_topic(topic_id)
