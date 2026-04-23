from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from msdp_api.db.models import ThreadMessage, TopicCreate, User
from msdp_api.services.group_assignment import GroupAssignmentService
from msdp_api.services.summarization import SummarizationService, build_transcript


@pytest.mark.asyncio
async def test_group_assignment_picks_least_full_group(
    repository,
    telegram_gateway,
    settings,
):
    topic = await repository.create_topic(TopicCreate(title="Topic"))
    first_group = await repository.create_group(
        topic_id=topic.id,
        thread_id=11,
        invite_link="https://example.com/1",
        capacity=2,
        telegram_topic_name="Group 1",
    )
    second_group = await repository.create_group(
        topic_id=topic.id,
        thread_id=12,
        invite_link="https://example.com/2",
        capacity=2,
        telegram_topic_name="Group 2",
    )
    await repository.increment_group_member_count(first_group.id)
    service = GroupAssignmentService(repository, telegram_gateway, settings.group_capacity)

    result = await service.assign_user_to_topic(
        topic_id=topic.id,
        user=User(telegram_user_id=1, first_name="Ada"),
        topic=topic,
    )

    assert result.group.id == second_group.id
    assert not result.was_created


@pytest.mark.asyncio
async def test_group_assignment_creates_group_when_existing_groups_are_full(
    repository,
    telegram_gateway,
    settings,
):
    topic = await repository.create_topic(TopicCreate(title="Topic"))
    first_group = await repository.create_group(
        topic_id=topic.id,
        thread_id=11,
        invite_link="https://example.com/1",
        capacity=1,
        telegram_topic_name="Group 1",
    )
    await repository.increment_group_member_count(first_group.id)
    service = GroupAssignmentService(repository, telegram_gateway, settings.group_capacity)

    result = await service.assign_user_to_topic(
        topic_id=topic.id,
        user=User(telegram_user_id=2, first_name="Grace"),
        topic=topic,
    )

    assert result.was_created
    assert result.group.thread_id == 1000 + 2


@pytest.mark.asyncio
async def test_duplicate_start_does_not_create_duplicate_membership(
    repository,
    telegram_gateway,
    settings,
):
    topic = await repository.create_topic(TopicCreate(title="Topic"))
    service = GroupAssignmentService(repository, telegram_gateway, settings.group_capacity)
    user = User(telegram_user_id=3, first_name="Lin")

    first = await service.assign_user_to_topic(topic.id, user, topic)
    second = await service.assign_user_to_topic(topic.id, user, topic)

    assert first.group.id == second.group.id
    assert second.already_member
    assert len(repository.memberships) == 1


def test_build_transcript_orders_messages_by_timestamp():
    group_id = uuid4()
    messages = [
        ThreadMessage(
            message_id=2,
            thread_id=10,
            group_id=group_id,
            telegram_user_id=1,
            username="later",
            first_name="Later",
            text="Second point",
            sent_at=datetime(2026, 4, 23, 10, 1, tzinfo=UTC),
        ),
        ThreadMessage(
            message_id=1,
            thread_id=10,
            group_id=group_id,
            telegram_user_id=2,
            username="earlier",
            first_name="Earlier",
            text="First point",
            sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
        ),
    ]

    transcript = build_transcript(messages)

    assert transcript.splitlines()[0].endswith("First point")
    assert transcript.splitlines()[1].endswith("Second point")


@pytest.mark.asyncio
async def test_summarization_service_upserts_one_summary_per_group(repository, summarizer):
    topic = await repository.create_topic(TopicCreate(title="Topic"))
    group = await repository.create_group(
        topic_id=topic.id,
        thread_id=11,
        invite_link="https://example.com/1",
        capacity=2,
        telegram_topic_name="Group 1",
    )
    await repository.store_thread_message(
        ThreadMessage(
            message_id=1,
            thread_id=11,
            group_id=group.id,
            telegram_user_id=1,
            username="speaker",
            first_name="Speaker",
            text="We agree on one thing.",
            sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
        ),
    )
    service = SummarizationService(repository, summarizer)

    first_result = await service.summarize_topic(topic.id)
    second_result = await service.summarize_topic(topic.id)

    assert first_result.summarized_groups == 1
    assert second_result.summarized_groups == 1
    assert len(await repository.list_summaries_for_topic(topic.id)) == 1
