from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from msdp_api.app import create_app
from msdp_api.core.config import Settings
from msdp_api.db.models import TopicSuggestionResponse
from msdp_api.repositories.memory import InMemoryRepository
from msdp_api.services.summarization import Summarizer


class FakeSummarizer(Summarizer):
    def __init__(self) -> None:
        self.transcripts: list[str] = []

    async def summarize(self, transcript: str) -> str:
        self.transcripts.append(transcript)
        return f"- Summary generated for transcript with {len(transcript.splitlines())} lines."

    async def cross_pollinate(
        self,
        target_group_name: str,
        target_summary: str,
        other_group_summaries: str,
    ) -> str:
        del target_summary
        return (
            f"Other groups raised a related angle for {target_group_name}: "
            f"{other_group_summaries.splitlines()[0]}"
        )


class FakeTopicSuggestionService:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    async def suggest(
        self,
        title: str,
        description: str | None = None,
        seed_bullets: list[str] | None = None,
    ) -> TopicSuggestionResponse:
        self.requests.append(
            {
                "title": title,
                "description": description,
                "seed_bullets": seed_bullets or [],
            },
        )
        return TopicSuggestionResponse(
            description=f"Discuss {title} from multiple practical angles.",
            seed_bullets=[
                "What benefit would matter most?",
                "Who could be harmed or overlooked?",
                "What tradeoff feels acceptable?",
                "What evidence would change your mind?",
            ],
        )


@pytest.fixture
def settings() -> Settings:
    return Settings.model_validate(
        {
            "DATABASE_URL": "postgresql://corda:test@localhost:5432/corda",
            "OPENAI_API_KEY": "test-openai-key",
            "X_ADMIN_KEY": "admin-key",
            "SUMMARY_MODEL": "test-model",
            "GROUP_CAPACITY": 2,
        },
    )


@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()


@pytest.fixture
def summarizer() -> FakeSummarizer:
    return FakeSummarizer()


@pytest.fixture
def topic_suggestion_service() -> FakeTopicSuggestionService:
    return FakeTopicSuggestionService()


@pytest.fixture
def client(
    settings: Settings,
    repository: InMemoryRepository,
    summarizer: FakeSummarizer,
    topic_suggestion_service: FakeTopicSuggestionService,
) -> TestClient:
    app = create_app(
        settings=settings,
        repository=repository,
        summarizer=summarizer,
        topic_suggestion_service=topic_suggestion_service,
    )
    return TestClient(app)
