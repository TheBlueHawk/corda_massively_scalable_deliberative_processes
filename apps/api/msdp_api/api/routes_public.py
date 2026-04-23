"""Public read-only API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from msdp_api.api.dependencies import get_repository
from msdp_api.db.models import ActiveTopicResponse, SummaryResponse
from msdp_api.repositories.protocols import Repository

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Return a basic health response."""
    return {"status": "ok"}


@router.get("/topics/active", response_model=ActiveTopicResponse)
async def get_active_topic(
    repository: Annotated[Repository, Depends(get_repository)],
) -> ActiveTopicResponse:
    """Return the currently active topic."""
    topic = await repository.get_active_topic()
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active topic.")
    return ActiveTopicResponse(
        id=topic.id,
        title=topic.title,
        description=topic.description,
        closes_at=topic.closes_at,
    )


@router.get("/topics/{topic_id}/summaries", response_model=list[SummaryResponse])
async def list_topic_summaries(
    topic_id: UUID,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[SummaryResponse]:
    """Return summaries for a topic."""
    summaries = await repository.list_summaries_for_topic(topic_id)
    return [
        SummaryResponse(group_id=item.group_id, content=item.content, created_at=item.created_at)
        for item in summaries
    ]
