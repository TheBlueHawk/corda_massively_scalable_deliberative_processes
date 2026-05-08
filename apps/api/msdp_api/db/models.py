"""Pydantic domain models for the backend."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_CROSS_POLLINATION_INTERVAL_SECONDS = 86_400
DEFAULT_GROUP_CAPACITY = 8
MAX_SEED_BULLETS = 6


def _require_timezone(value: datetime | None) -> datetime | None:
    """Require API datetimes to include timezone information."""
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        msg = "Datetime must include timezone information."
        raise ValueError(msg)
    return value


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
    cross_pollination_interval_seconds: int
    next_cross_pollination_at: datetime | None
    group_capacity: int
    seed_bullets: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicCreate(BaseModel):
    """Payload used to create a new deliberation topic."""

    title: str = Field(min_length=1)
    description: str | None = None
    closes_at: datetime | None = None
    cross_pollination_interval_seconds: int = Field(
        default=DEFAULT_CROSS_POLLINATION_INTERVAL_SECONDS,
        gt=0,
    )
    group_capacity: int = Field(default=DEFAULT_GROUP_CAPACITY, gt=0)
    seed_bullets: list[str] = Field(default_factory=list, max_length=MAX_SEED_BULLETS)

    _validate_closes_at = field_validator("closes_at")(_require_timezone)


class TopicUpdate(BaseModel):
    """Payload used to update an existing topic's editable fields."""

    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    closes_at: datetime | None = None
    cross_pollination_interval_seconds: int | None = Field(default=None, gt=0)
    group_capacity: int | None = Field(default=None, gt=0)
    seed_bullets: list[str] | None = Field(default=None, max_length=MAX_SEED_BULLETS)

    _validate_closes_at = field_validator("closes_at")(_require_timezone)


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


class TopicListItemResponse(BaseModel):
    """Public response for a topic listed on the homepage."""

    id: UUID
    title: str
    description: str | None
    status: TopicStatus
    closes_at: datetime | None
    cross_pollination_interval_seconds: int
    next_cross_pollination_at: datetime | None
    group_capacity: int
    created_at: datetime


class SummaryResponse(BaseModel):
    """Public response for group summaries."""

    group_id: UUID
    content: str
    created_at: datetime


class TopicCreatedResponse(BaseModel):
    """Admin response after topic creation."""

    topic: Topic


class AdminGroupOverview(BaseModel):
    """Admin-facing group status and activity metrics."""

    id: UUID
    topic_id: UUID
    thread_id: int
    invite_link: str
    capacity: int
    member_count: int
    telegram_topic_name: str
    message_count: int
    has_summary: bool
    summary_created_at: datetime | None


class AdminTopicOverview(BaseModel):
    """Admin-facing topic status, controls, and aggregate metrics."""

    topic: Topic
    groups: list[AdminGroupOverview]
    participant_count: int
    message_count: int
    summary_count: int


class AdminDashboardResponse(BaseModel):
    """Admin dashboard payload."""

    topics: list[AdminTopicOverview]
    active_topic_id: UUID | None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AdminThreadMessageResponse(BaseModel):
    """Admin response item for a captured thread message."""

    message_id: int
    thread_id: int
    group_id: UUID
    telegram_user_id: int | None
    username: str | None
    first_name: str | None
    text: str
    sent_at: datetime


class TopicUpdatedResponse(BaseModel):
    """Admin response after topic update or close."""

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


class CrossPollinationResult(BaseModel):
    """Admin response after one topic cross-pollination run."""

    topic_id: UUID
    summarized_groups: int
    comments_posted: int
    next_cross_pollination_at: datetime | None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DueSummarizationResult(BaseModel):
    """Admin response after summarizing all due topics."""

    summarized_topics: list[SummarizationResult]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DueCrossPollinationResult(BaseModel):
    """Admin response after cross-pollinating all due topics."""

    cross_pollinated_topics: list[CrossPollinationResult]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
