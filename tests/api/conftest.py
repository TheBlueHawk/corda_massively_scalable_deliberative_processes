from __future__ import annotations

from dataclasses import dataclass, field

from fastapi.testclient import TestClient
import pytest

from msdp_api.app import create_app
from msdp_api.core.config import Settings
from msdp_api.repositories.memory import InMemoryRepository
from msdp_api.services.summarization import Summarizer
from msdp_api.telegram.gateway import CreatedTelegramGroup


@dataclass
class FakeTelegramGateway:
    created_groups: list[CreatedTelegramGroup] = field(default_factory=list)
    sent_messages: list[dict[str, str | int]] = field(default_factory=list)
    moderator_comments: list[dict[str, str | int]] = field(default_factory=list)

    async def create_group(
        self,
        ordinal: int,
        capacity: int,
        topic_title: str,
        icon_color: int,
    ) -> CreatedTelegramGroup:
        del capacity, icon_color
        group = CreatedTelegramGroup(
            thread_id=1000 + ordinal,
            invite_link=f"https://t.me/joinchat/group-{ordinal}",
            topic_name=f"{topic_title} · Group {ordinal}",
        )
        self.created_groups.append(group)
        return group

    async def send_assignment_message(
        self,
        chat_id: int,
        thread_id: int,
        invite_link: str,
        topic_title: str,
    ) -> None:
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "thread_id": thread_id,
                "invite_link": invite_link,
                "topic_title": topic_title,
            },
        )

    async def send_moderator_comment(self, thread_id: int, text: str) -> None:
        self.moderator_comments.append({"thread_id": thread_id, "text": text})


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


@pytest.fixture
def settings() -> Settings:
    return Settings.model_validate(
        {
            "DATABASE_URL": "postgresql://corda:test@localhost:5432/corda",
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_SUPERGROUP_ID": -100123,
            "ANTHROPIC_API_KEY": "test-key",
            "OPENAI_API_KEY": "test-openai-key",
            "X_ADMIN_KEY": "admin-key",
            "TELEGRAM_BOT_USERNAME": "corda_test_bot",
            "SUMMARY_MODEL": "test-model",
            "GROUP_CAPACITY": 2,
        },
    )


@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()


@pytest.fixture
def telegram_gateway() -> FakeTelegramGateway:
    return FakeTelegramGateway()


@pytest.fixture
def summarizer() -> FakeSummarizer:
    return FakeSummarizer()


@pytest.fixture
def client(
    settings: Settings,
    repository: InMemoryRepository,
    telegram_gateway: FakeTelegramGateway,
    summarizer: FakeSummarizer,
) -> TestClient:
    app = create_app(
        settings=settings,
        repository=repository,
        telegram_gateway=telegram_gateway,
        summarizer=summarizer,
    )
    return TestClient(app)
