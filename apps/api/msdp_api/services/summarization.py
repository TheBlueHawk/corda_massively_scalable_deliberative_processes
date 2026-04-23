"""Summarization workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from anthropic import AsyncAnthropic

from msdp_api.db.models import SummarizationResult, ThreadMessage

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from msdp_api.repositories.protocols import Repository

SUMMARY_PROMPT = (
    "Summarize the key points of agreement and disagreement from this deliberation. "
    "Be concise, neutral, and use 3 to 5 bullet points."
)


class Summarizer:
    """Protocol-like adapter for summary generation."""

    async def summarize(self, transcript: str) -> str:
        """Return a concise summary for the given transcript."""
        raise NotImplementedError


class AnthropicSummarizer(Summarizer):
    """Anthropic-backed summarizer."""

    def __init__(self, api_key: str, model: str) -> None:
        """Initialize the client."""
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def summarize(self, transcript: str) -> str:
        """Generate a summary using Anthropic."""
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=500,
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": transcript}],
        )
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "\n".join(parts).strip()


def build_transcript(messages: Sequence[ThreadMessage]) -> str:
    """Build a readable transcript from stored thread messages."""
    ordered = sorted(messages, key=lambda item: (item.sent_at, item.message_id))
    return "\n".join(
        f"{message.first_name or message.username or 'Participant'}: {message.text}"
        for message in ordered
    )


class SummarizationService:
    """Summarize every group for a topic from stored messages."""

    def __init__(self, repository: Repository, summarizer: Summarizer) -> None:
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
