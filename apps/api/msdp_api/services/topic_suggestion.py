"""AI-assisted drafting for deliberation topic setup."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, Field, ValidationError

from msdp_api.db.models import MAX_SEED_BULLETS, TopicSuggestionResponse

if TYPE_CHECKING:
    from openai import AsyncOpenAI

_SUGGESTION_PROMPT = (
    "You help admins prepare neutral public deliberation topics. "
    "Return only valid JSON with keys description and seed_bullets. "
    "The description should be 2 concise sentences that make the topic concrete "
    "without taking a side. seed_bullets must contain 4 to 6 short prompts, one "
    "per line when displayed, balanced across pro, con, tradeoff, and open-question angles."
)


class _TopicSuggestionPayload(BaseModel):
    """Validated model response for topic draft suggestions."""

    description: str = Field(min_length=1)
    seed_bullets: list[str] = Field(min_length=1, max_length=MAX_SEED_BULLETS)


class TopicSuggestionService:
    """Generate editable topic descriptions and seed prompts using OpenAI."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        """Initialize the service."""
        self._client = client
        self._model = model

    async def suggest(
        self,
        title: str,
        description: str | None = None,
        seed_bullets: list[str] | None = None,
    ) -> TopicSuggestionResponse:
        """Return an editable description and seed bullets for a topic title.

        Raises:
            RuntimeError: when the model returns invalid or empty JSON.
        """
        prompt = (
            f"Topic title: {title.strip()}\n"
            f"Current description: {(description or '').strip() or 'None'}\n"
            "Current seed bullets:\n"
            f"{json.dumps(seed_bullets or [], ensure_ascii=False)}"
        )
        response = await self._client.responses.create(
            model=self._model,
            instructions=_SUGGESTION_PROMPT,
            input=prompt,
            max_output_tokens=700,
        )
        try:
            payload = _TopicSuggestionPayload.model_validate_json(response.output_text)
        except (ValidationError, ValueError) as exc:
            msg = "OpenAI returned an invalid topic suggestion."
            raise RuntimeError(msg) from exc
        return TopicSuggestionResponse(
            description=payload.description.strip(),
            seed_bullets=[item.strip() for item in payload.seed_bullets if item.strip()],
        )


class TopicSuggesterProtocol(Protocol):
    """Adapter protocol for topic draft suggestions."""

    async def suggest(
        self,
        title: str,
        description: str | None = None,
        seed_bullets: list[str] | None = None,
    ) -> TopicSuggestionResponse:
        """Return an editable description and seed bullets for a topic title."""
        raise NotImplementedError
