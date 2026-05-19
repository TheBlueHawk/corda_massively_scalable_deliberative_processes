from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

from openai import AsyncOpenAI
import pytest

from msdp_api.db.models import ThreadMessage, TopicCreate, TopicStatus, User
from msdp_api.services.group_assignment import GroupAssignmentService
from msdp_api.services.summarization import (
    CROSS_POLLINATION_PROMPT,
    SUMMARY_PROMPT,
    OpenAISummarizer,
    SummarizationService,
    build_transcript,
)
from msdp_api.services.topic_suggestion import TopicSuggestionService


@pytest.mark.asyncio
async def test_group_assignment_picks_least_full_group(repository):
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
    service = GroupAssignmentService(repository)

    result = await service.assign_user_to_topic(
        topic_id=topic.id,
        user=User(telegram_user_id=1, first_name="Ada"),
        topic=topic,
    )

    assert result.group.id == second_group.id
    assert not result.was_created


@pytest.mark.asyncio
async def test_group_assignment_creates_group_when_existing_groups_are_full(repository):
    topic = await repository.create_topic(TopicCreate(title="Topic"))
    first_group = await repository.create_group(
        topic_id=topic.id,
        thread_id=11,
        invite_link="https://example.com/1",
        capacity=1,
        telegram_topic_name="Group 1",
    )
    await repository.increment_group_member_count(first_group.id)
    service = GroupAssignmentService(repository)

    result = await service.assign_user_to_topic(
        topic_id=topic.id,
        user=User(telegram_user_id=2, first_name="Grace"),
        topic=topic,
    )

    assert result.was_created
    assert result.group.thread_id is None


@pytest.mark.asyncio
async def test_duplicate_start_does_not_create_duplicate_membership(repository):
    topic = await repository.create_topic(TopicCreate(title="Topic"))
    service = GroupAssignmentService(repository)
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
async def test_openai_summarizer_uses_responses_api():
    class FakeResponses:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(output_text="  - Generated summary.  ")

    fake_client = SimpleNamespace(responses=FakeResponses())
    summarizer = OpenAISummarizer(client=cast("AsyncOpenAI", fake_client), model="gpt-5-mini")

    summary = await summarizer.summarize("Speaker: We agree.")
    comment = await summarizer.cross_pollinate(
        target_group_name="Group 1",
        target_summary="- Bikes are useful.",
        other_group_summaries="Group 2:\n- Transit matters.",
    )

    assert summary == "- Generated summary."
    assert comment == "- Generated summary."
    assert fake_client.responses.calls[0] == {
        "model": "gpt-5-mini",
        "instructions": SUMMARY_PROMPT,
        "input": "Speaker: We agree.",
        "max_output_tokens": 500,
    }
    assert fake_client.responses.calls[1]["instructions"] == CROSS_POLLINATION_PROMPT
    assert fake_client.responses.calls[1]["max_output_tokens"] == 180


@pytest.mark.asyncio
async def test_topic_suggestion_service_parses_openai_json():
    class FakeResponses:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                output_text=(
                    '{"description":"A neutral draft.",'
                    '"seed_bullets":["Benefit?","Concern?","Tradeoff?","Evidence?"]}'
                ),
            )

    fake_client = SimpleNamespace(responses=FakeResponses())
    service = TopicSuggestionService(client=cast("AsyncOpenAI", fake_client), model="gpt-5-mini")

    suggestion = await service.suggest(
        title="Mobility pricing",
        description="Existing",
        seed_bullets=["Old prompt"],
    )

    assert suggestion.description == "A neutral draft."
    assert suggestion.seed_bullets == ["Benefit?", "Concern?", "Tradeoff?", "Evidence?"]
    assert fake_client.responses.calls[0]["model"] == "gpt-5-mini"
    assert "Mobility pricing" in fake_client.responses.calls[0]["input"]


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


@pytest.mark.asyncio
async def test_summarization_service_summarizes_due_topics_and_closes_them(
    repository,
    summarizer,
):
    due_topic = await repository.create_topic(
        TopicCreate(
            title="Due topic",
            closes_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
        ),
    )
    future_topic = await repository.create_topic(
        TopicCreate(
            title="Future topic",
            closes_at=datetime(3026, 4, 23, 10, 0, tzinfo=UTC),
        ),
    )
    group = await repository.create_group(
        topic_id=due_topic.id,
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
            text="Cars should be restricted downtown.",
            sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
        ),
    )
    service = SummarizationService(repository, summarizer)

    result = await service.summarize_due_topics(datetime(2026, 4, 23, 11, 0, tzinfo=UTC))

    assert len(result.summarized_topics) == 1
    assert result.summarized_topics[0].topic_id == due_topic.id
    assert result.summarized_topics[0].summarized_groups == 1
    assert (await repository.get_topic(due_topic.id)).status == TopicStatus.CLOSED
    assert (await repository.get_topic(future_topic.id)).status == TopicStatus.ACTIVE


@pytest.mark.asyncio
async def test_cross_pollination_summarizes_and_posts_comments(repository, summarizer):
    topic = await repository.create_topic(
        TopicCreate(title="Shared learning", cross_pollination_interval_seconds=60),
    )
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
    for group, text in (
        (first_group, "Transit access matters."),
        (second_group, "Small businesses need delivery access."),
    ):
        await repository.store_thread_message(
            ThreadMessage(
                message_id=group.thread_id,
                thread_id=group.thread_id,
                group_id=group.id,
                telegram_user_id=1,
                username="speaker",
                first_name="Speaker",
                text=text,
                sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
            ),
        )
    service = SummarizationService(repository, summarizer)

    result = await service.cross_pollinate_topic(
        topic.id, datetime(2026, 4, 23, 11, 0, tzinfo=UTC)
    )

    assert result.summarized_groups == 2
    assert result.comments_posted == 2
    assert result.next_cross_pollination_at == datetime(2026, 4, 23, 11, 1, tzinfo=UTC)
    moderator_msgs = [
        msg
        for group in (first_group, second_group)
        for msg in await repository.list_messages_for_group(group.id)
        if msg.is_moderator
    ]
    assert len(moderator_msgs) == 2


@pytest.mark.asyncio
async def test_cross_pollination_due_topics_only_runs_due_active_topics(repository, summarizer):
    due_topic = await repository.create_topic(
        TopicCreate(title="Due", cross_pollination_interval_seconds=60),
    )
    future_topic = await repository.create_topic(
        TopicCreate(title="Future", cross_pollination_interval_seconds=86_400),
    )
    closed_topic = await repository.create_topic(
        TopicCreate(title="Closed", cross_pollination_interval_seconds=60),
    )
    await repository.schedule_next_cross_pollination(
        due_topic.id,
        datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
    )
    await repository.schedule_next_cross_pollination(
        future_topic.id,
        datetime(2026, 4, 24, 10, 0, tzinfo=UTC),
    )
    await repository.close_topic(closed_topic.id)
    for topic in (due_topic, future_topic):
        await repository.create_group(
            topic_id=topic.id,
            thread_id=len(repository.groups) + 1,
            invite_link="https://example.com/1",
            capacity=2,
            telegram_topic_name="Group 1",
        )
    service = SummarizationService(repository, summarizer)

    result = await service.cross_pollinate_due_topics(datetime(2026, 4, 23, 11, 0, tzinfo=UTC))

    assert [item.topic_id for item in result.cross_pollinated_topics] == [due_topic.id]
    updated_due_topic = await repository.get_topic(due_topic.id)
    assert updated_due_topic is not None
    assert updated_due_topic.next_cross_pollination_at == datetime(
        2026,
        4,
        23,
        11,
        1,
        tzinfo=UTC,
    )
