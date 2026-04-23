"""Pydantic domain models for the backend."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TopicStatus(StrEnum):
    """Allowed topic lifecycle states."""

    ACTIVE = "active"
    CLOSED = "closed"


class Topic(BaseModel):
    """A deliberation topic."""

    id: UUID
    title: str
    description: str | None
    status: TopicStatus
    closes_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicCreate(BaseModel):
    """Payload used to create a new deliberation topic."""

    title: str = Field(min_length=1)
    description: str | None = None
    closes_at: datetime | None = None


class Group(BaseModel):
    """A Telegram forum topic backing a deliberation group."""

    id: UUID
    topic_id: UUID
    thread_id: int
    invite_link: str
    capacity: int
    member_count: int
    telegram_topic_name: str

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    """A Telegram user known to the application."""

    telegram_user_id: int
    username: str | None = None
    first_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class Membership(BaseModel):
    """A user assignment to a deliberation group."""

    telegram_user_id: int
    group_id: UUID
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Summary(BaseModel):
    """A stored summary for a group."""

    id: UUID
    group_id: UUID
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadMessage(BaseModel):
    """A captured message from a Telegram forum topic."""

    message_id: int
    thread_id: int
    group_id: UUID
    telegram_user_id: int | None
    username: str | None = None
    first_name: str | None = None
    text: str
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActiveTopicResponse(BaseModel):
    """Public response for the single active topic."""

    id: UUID
    title: str
    description: str | None
    closes_at: datetime | None


class SummaryResponse(BaseModel):
    """Public response for group summaries."""

    group_id: UUID
    content: str
    created_at: datetime


class TopicCreatedResponse(BaseModel):
    """Admin response after topic creation."""

    topic: Topic


class GroupAssignmentResult(BaseModel):
    """Result returned after assigning a user to a group."""

    group: Group
    was_created: bool
    already_member: bool


class SummarizationResult(BaseModel):
    """Admin response after topic summarization."""

    topic_id: UUID
    summarized_groups: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
