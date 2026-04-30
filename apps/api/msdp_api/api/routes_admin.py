"""Admin API routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from msdp_api.api.dependencies import (
    get_repository,
    get_summarization_service,
    require_admin_key,
)
from msdp_api.db.models import (
    AdminDashboardResponse,
    AdminGroupOverview,
    AdminThreadMessageResponse,
    AdminTopicOverview,
    DueSummarizationResult,
    SummarizationResult,
    TopicCreate,
    TopicCreatedResponse,
    TopicUpdate,
    TopicUpdatedResponse,
)
from msdp_api.repositories.protocols import Repository
from msdp_api.services.summarization import SummarizationService

router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(require_admin_key)],
)


async def _build_dashboard(repository: Repository) -> AdminDashboardResponse:
    """Build the admin dashboard read model from repository data."""
    topics = await repository.list_topics()
    active_topic = await repository.get_active_topic()
    topic_overviews: list[AdminTopicOverview] = []
    for topic in topics:
        groups = await repository.list_groups_for_topic(topic.id)
        summaries = await repository.list_summaries_for_topic(topic.id)
        summaries_by_group = {summary.group_id: summary for summary in summaries}
        group_overviews: list[AdminGroupOverview] = []
        for group in groups:
            message_count = len(await repository.list_thread_messages(group.id))
            summary = summaries_by_group.get(group.id)
            group_overviews.append(
                AdminGroupOverview(
                    id=group.id,
                    topic_id=group.topic_id,
                    thread_id=group.thread_id,
                    invite_link=group.invite_link,
                    capacity=group.capacity,
                    member_count=group.member_count,
                    telegram_topic_name=group.telegram_topic_name,
                    message_count=message_count,
                    has_summary=summary is not None,
                    summary_created_at=summary.created_at if summary else None,
                ),
            )
        topic_overviews.append(
            AdminTopicOverview(
                topic=topic,
                groups=group_overviews,
                participant_count=sum(group.member_count for group in groups),
                message_count=sum(group.message_count for group in group_overviews),
                summary_count=len(summaries),
            ),
        )
    return AdminDashboardResponse(
        topics=topic_overviews,
        active_topic_id=active_topic.id if active_topic else None,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(
    repository: Annotated[Repository, Depends(get_repository)],
) -> AdminDashboardResponse:
    """Return topic, group, summary, and activity data for the admin dashboard."""
    return await _build_dashboard(repository)


@router.post("/topics", response_model=TopicCreatedResponse)
async def create_topic(
    payload: TopicCreate,
    repository: Annotated[Repository, Depends(get_repository)],
) -> TopicCreatedResponse:
    """Create a new topic."""
    topic = await repository.create_topic(payload)
    return TopicCreatedResponse(topic=topic)


@router.patch("/topics/{topic_id}", response_model=TopicUpdatedResponse)
async def update_topic(
    topic_id: UUID,
    payload: TopicUpdate,
    repository: Annotated[Repository, Depends(get_repository)],
) -> TopicUpdatedResponse:
    """Update a topic's editable fields."""
    topic = await repository.update_topic(topic_id, payload)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    return TopicUpdatedResponse(topic=topic)


@router.post("/topics/{topic_id}/close", response_model=TopicUpdatedResponse)
async def close_topic(
    topic_id: UUID,
    repository: Annotated[Repository, Depends(get_repository)],
) -> TopicUpdatedResponse:
    """Close a topic manually."""
    topic = await repository.close_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    return TopicUpdatedResponse(topic=topic)


@router.get("/groups/{group_id}/messages", response_model=list[AdminThreadMessageResponse])
async def list_group_messages(
    group_id: UUID,
    repository: Annotated[Repository, Depends(get_repository)],
) -> list[AdminThreadMessageResponse]:
    """Return captured messages for an admin transcript view."""
    messages = await repository.list_thread_messages(group_id)
    return [
        AdminThreadMessageResponse(
            message_id=message.message_id,
            thread_id=message.thread_id,
            group_id=message.group_id,
            telegram_user_id=message.telegram_user_id,
            username=message.username,
            first_name=message.first_name,
            text=message.text,
            sent_at=message.sent_at,
        )
        for message in messages
    ]


@router.post("/summarize-due", response_model=DueSummarizationResult)
async def summarize_due_topics(
    summarization_service: Annotated[SummarizationService, Depends(get_summarization_service)],
) -> DueSummarizationResult:
    """Trigger summarization for all due active topics."""
    return await summarization_service.summarize_due_topics()


@router.post("/summarize/{topic_id}", response_model=SummarizationResult)
async def summarize_topic(
    topic_id: UUID,
    summarization_service: Annotated[SummarizationService, Depends(get_summarization_service)],
) -> SummarizationResult:
    """Trigger summarization for a topic."""
    return await summarization_service.summarize_topic(topic_id)
