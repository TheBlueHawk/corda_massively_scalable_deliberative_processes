"""Summarization workflow."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from openai import AsyncOpenAI

from msdp_api.db.models import (
    CrossPollinationResult,
    DueCrossPollinationResult,
    DueSummarizationResult,
    Group,
    SummarizationResult,
    Summary,
    ThreadMessage,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from msdp_api.repositories.protocols import Repository

SUMMARY_PROMPT = (
    "Summarize the key points of agreement and disagreement from this deliberation. "
    "Be concise, neutral, and use 3 to 5 bullet points."
)
CROSS_POLLINATION_PROMPT = (
    "You are a neutral moderator helping deliberation groups learn from each other. "
    "Write exactly one short comment for the target group. Mention one useful point, "
    "angle, concern, or framing raised by other groups that is not prominent in the target "
    "group summary. Use phrasing like 'Other groups raised...' or "
    "'Other groups approached this from...'. Do not mention group numbers unless needed."
)


class Summarizer:
    """Protocol-like adapter for summary generation."""

    async def summarize(self, transcript: str) -> str:
        """Return a concise summary for the given transcript."""
        raise NotImplementedError

    async def cross_pollinate(
        self,
        target_group_name: str,
        target_summary: str,
        other_group_summaries: str,
    ) -> str:
        """Return one moderator comment connecting other groups to a target group."""
        raise NotImplementedError


class OpenAISummarizer(Summarizer):
    """OpenAI-backed summarizer."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        """Initialize the client."""
        self._client = client
        self._model = model

    async def summarize(self, transcript: str) -> str:
        """Generate a summary using OpenAI."""
        response = await self._client.responses.create(
            model=self._model,
            instructions=SUMMARY_PROMPT,
            input=transcript,
            max_output_tokens=500,
        )
        return response.output_text.strip()

    async def cross_pollinate(
        self,
        target_group_name: str,
        target_summary: str,
        other_group_summaries: str,
    ) -> str:
        """Generate one cross-pollination moderator comment using OpenAI."""
        prompt = (
            f"Target group: {target_group_name}\n\n"
            f"Target group summary:\n{target_summary}\n\n"
            f"Other group summaries:\n{other_group_summaries}"
        )
        response = await self._client.responses.create(
            model=self._model,
            instructions=CROSS_POLLINATION_PROMPT,
            input=prompt,
            max_output_tokens=180,
        )
        return response.output_text.strip()


def build_transcript(messages: Sequence[ThreadMessage]) -> str:
    """Build a readable transcript from stored thread messages."""
    ordered = sorted(messages, key=lambda item: (item.sent_at, item.message_id))
    return "\n".join(
        f"{message.first_name or message.username or 'Participant'}: {message.text}"
        for message in ordered
    )


class SummarizationService:
    """Summarize groups and cross-pollinate ideas across active topics."""

    def __init__(
        self,
        repository: Repository,
        summarizer: Summarizer,
    ) -> None:
        """Initialize the service."""
        self._repository = repository
        self._summarizer = summarizer

    async def summarize_topic(self, topic_id: UUID) -> SummarizationResult:
        """Generate summaries for all groups in the topic."""
        groups = await self._repository.list_groups_for_topic(topic_id)
        summarized_groups = 0
        for group in groups:
            messages = await self._repository.list_thread_messages(group.id)
            if messages:
                transcript = build_transcript(messages)
                content = await self._summarizer.summarize(transcript)
            else:
                content = "- No discussion messages were captured for this group."
            await self._repository.upsert_summary(group.id, content)
            summarized_groups += 1
        return SummarizationResult(topic_id=topic_id, summarized_groups=summarized_groups)

    async def cross_pollinate_topic(
        self,
        topic_id: UUID,
        now: datetime | None = None,
    ) -> CrossPollinationResult:
        """Summarize groups, compare them, and post one moderator comment per group."""
        topic = await self._repository.get_topic(topic_id)
        if topic is None:
            return CrossPollinationResult(
                topic_id=topic_id,
                summarized_groups=0,
                comments_posted=0,
                next_cross_pollination_at=None,
            )
        summary_result = await self.summarize_topic(topic_id)
        groups = list(await self._repository.list_groups_for_topic(topic_id))
        summaries = list(await self._repository.list_summaries_for_topic(topic_id))
        comments_posted = 0
        if len(summaries) > 1:
            comments_posted = await self._post_cross_pollination_comments(groups, summaries)
        cutoff = now or datetime.now(UTC)
        next_run = cutoff + timedelta(seconds=topic.cross_pollination_interval_seconds)
        await self._repository.schedule_next_cross_pollination(topic_id, next_run)
        return CrossPollinationResult(
            topic_id=topic_id,
            summarized_groups=summary_result.summarized_groups,
            comments_posted=comments_posted,
            next_cross_pollination_at=next_run,
        )

    async def _post_cross_pollination_comments(
        self,
        groups: list[Group],
        summaries: list[Summary],
    ) -> int:
        """Generate moderator comments and store them as chat messages in each group."""
        summaries_by_group = {summary.group_id: summary for summary in summaries}
        posted = 0
        for group in groups:
            target_summary = summaries_by_group.get(group.id)
            if target_summary is None:
                continue
            other_summaries = [
                f"{other_group.telegram_topic_name}:\n{summary.content}"
                for other_group in groups
                if other_group.id != group.id
                for summary in [summaries_by_group.get(other_group.id)]
                if summary is not None
            ]
            if not other_summaries:
                continue
            comment = await self._summarizer.cross_pollinate(
                target_group_name=group.telegram_topic_name,
                target_summary=target_summary.content,
                other_group_summaries="\n\n".join(other_summaries),
            )
            if not comment:
                continue
            await self._repository.store_web_message(
                group_id=group.id,
                participant_id=None,
                display_name="Moderator",
                text=comment,
                is_moderator=True,
            )
            posted += 1
        return posted

    async def summarize_due_topics(self, now: datetime | None = None) -> DueSummarizationResult:
        """Summarize every active topic whose close time has passed."""
        cutoff = now or datetime.now(UTC)
        summarized_topics: list[SummarizationResult] = []
        for topic in await self._repository.list_due_topics(cutoff):
            result = await self.summarize_topic(topic.id)
            await self._repository.close_topic(topic.id)
            summarized_topics.append(result)
        return DueSummarizationResult(summarized_topics=summarized_topics)

    async def cross_pollinate_due_topics(
        self,
        now: datetime | None = None,
    ) -> DueCrossPollinationResult:
        """Cross-pollinate every active topic whose periodic cadence is due."""
        cutoff = now or datetime.now(UTC)
        cross_pollinated_topics: list[CrossPollinationResult] = []
        for topic in await self._repository.list_cross_pollination_due_topics(cutoff):
            result = await self.cross_pollinate_topic(topic.id, cutoff)
            cross_pollinated_topics.append(result)
        return DueCrossPollinationResult(cross_pollinated_topics=cross_pollinated_topics)
