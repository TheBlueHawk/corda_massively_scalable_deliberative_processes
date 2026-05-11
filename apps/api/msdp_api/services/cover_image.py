"""Generate per-topic cover images via OpenAI's image API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai import AsyncOpenAI

if TYPE_CHECKING:
    from uuid import UUID

    from msdp_api.db.models import Topic
    from msdp_api.repositories.protocols import Repository


_PROMPT_TEMPLATE = (
    "Editorial cover illustration for a public deliberation topic titled "
    '"{title}". {description}'
    " Style: muted, abstract, civic, editorial — no text, no logos, no faces. "
    "Use a warm, paper-like background with one or two strong focal shapes. "
    "Square 1:1 composition."
)


def _build_prompt(title: str, description: str | None) -> str:
    """Compose the image-generation prompt from the topic title and description."""
    description_blurb = f"The debate centers on: {description.strip()}." if description else ""
    return _PROMPT_TEMPLATE.format(title=title.strip(), description=description_blurb)


class CoverImageService:
    """Generate and persist cover images for deliberation topics."""

    def __init__(
        self,
        repository: Repository,
        client: AsyncOpenAI,
        model: str,
    ) -> None:
        """Initialize the service with its dependencies."""
        self._repository = repository
        self._client = client
        self._model = model

    async def generate_and_persist(self, topic_id: UUID) -> Topic:
        """Generate a cover image for ``topic_id`` and store it on the topic.

        The base64 PNG returned by OpenAI is wrapped as a ``data:`` URL and
        written to ``topics.cover_image_url``. Storing it inline keeps the
        rollout free of external object-storage credentials; a future change
        can swap this for Vercel Blob without touching callers.

        Raises:
            ValueError: when the topic does not exist.
            RuntimeError: when the model returns no image data.
        """
        topic = await self._repository.get_topic(topic_id)
        if topic is None:
            msg = f"Topic {topic_id} not found."
            raise ValueError(msg)
        prompt = _build_prompt(title=topic.title, description=topic.description)
        response = await self._client.images.generate(
            model=self._model,
            prompt=prompt,
            size="1024x1024",
            n=1,
        )
        if not response.data:
            msg = "Image generation returned no data."
            raise RuntimeError(msg)
        b64 = response.data[0].b64_json
        if not b64:
            msg = "Image generation returned no b64_json payload."
            raise RuntimeError(msg)
        data_url = f"data:image/png;base64,{b64}"
        updated = await self._repository.set_topic_cover_image_url(topic_id, data_url)
        if updated is None:
            msg = f"Failed to persist cover image for topic {topic_id}."
            raise RuntimeError(msg)
        return updated
