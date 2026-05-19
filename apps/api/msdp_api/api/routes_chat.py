"""Web chat API routes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import contextlib
import json
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from msdp_api.api.dependencies import get_repository, get_runtime_settings
from msdp_api.db.models import (
    ChatJoinResponse,
    ChatMessageResponse,
    Participant,
    ParticipantCreate,
    ThreadMessage,
)
from msdp_api.repositories.postgres import PostgresRepository
from msdp_api.repositories.protocols import Repository
from msdp_api.services.web_group_assignment import WebGroupAssignmentService

router = APIRouter(prefix="/chat")
_MAX_MESSAGE_LENGTH = 4000


def _message_to_response(msg: ThreadMessage, display_name: str) -> ChatMessageResponse:
    """Convert a ThreadMessage to the public chat response shape."""
    return ChatMessageResponse(
        id=msg.id,
        group_id=msg.group_id,
        participant_id=msg.participant_id,
        display_name=display_name,
        text=msg.text,
        sent_at=msg.sent_at,
        is_moderator=msg.is_moderator,
    )


def _serialize_message(msg: ChatMessageResponse) -> dict[str, object]:
    """Return a JSON-serialisable dict for an SSE data payload."""
    return {
        "id": str(msg.id),
        "group_id": str(msg.group_id),
        "participant_id": str(msg.participant_id) if msg.participant_id else None,
        "display_name": msg.display_name,
        "text": msg.text,
        "sent_at": msg.sent_at.isoformat(),
        "is_moderator": msg.is_moderator,
    }


async def _resolve_participant(
    repository: Repository,
    x_participant_id: str | None,
) -> Participant:
    """Validate X-Participant-Id and return the matching participant.

    Raises:
        HTTPException: 401 if the header is missing, malformed, or unknown.
    """
    if not x_participant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Participant-Id header is required.",
        )
    try:
        pid = UUID(x_participant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid participant id.",
        ) from exc
    participant = await repository.get_participant(pid)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown participant.",
        )
    return participant


async def _resolve_display_names(
    repository: Repository,
    messages: list[ThreadMessage],
) -> dict[UUID, str]:
    """Return a map of message.id → display_name for a batch of messages."""
    participant_ids = {m.participant_id for m in messages if m.participant_id is not None}
    names: dict[UUID, str] = {}
    for pid in participant_ids:
        p = await repository.get_participant(pid)
        if p:
            names[pid] = p.display_name
    result: dict[UUID, str] = {}
    for msg in messages:
        if msg.is_moderator:
            result[msg.id] = "Moderator"
        elif msg.participant_id and msg.participant_id in names:
            result[msg.id] = names[msg.participant_id]
        else:
            result[msg.id] = msg.first_name or msg.username or "Participant"
    return result


async def _require_group(repository: Repository, group_id: UUID) -> UUID:
    """Return the topic_id for a group, or raise 404 if the group does not exist."""
    group = await repository.get_group(group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    return group.topic_id


async def _publish(request: Request, group_id: UUID, response: ChatMessageResponse) -> None:
    """Put a new message into every SSE queue subscribed to the group."""
    subscribers: list[asyncio.Queue[ChatMessageResponse]] = (
        request.app.state.group_subscribers.get(group_id, [])
    )
    for queue in subscribers:
        await queue.put(response)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/my-groups")
async def list_my_groups(
    repository: Annotated[Repository, Depends(get_repository)],
    x_participant_id: Annotated[str | None, Header(alias="X-Participant-Id")] = None,
) -> list[dict[str, object]]:
    """Return all groups and their topics for the authenticated participant."""
    participant = await _resolve_participant(repository, x_participant_id)
    entries = await repository.list_participant_groups(participant.id)
    return [
        {
            "group": {
                "id": str(g.id),
                "topic_id": str(g.topic_id),
                "telegram_topic_name": g.telegram_topic_name,
                "capacity": g.capacity,
                "member_count": g.member_count,
            },
            "topic": {
                "id": str(t.id),
                "title": t.title,
                "status": t.status.value,
            },
        }
        for g, t in entries
    ]


@router.post("/participants", response_model=Participant, status_code=status.HTTP_201_CREATED)
async def create_participant(
    payload: ParticipantCreate,
    repository: Annotated[Repository, Depends(get_repository)],
) -> Participant:
    """Register a new web participant and return their session id."""
    return await repository.create_participant(payload.display_name)


@router.get("/topics/{topic_id}/my-group")
async def get_my_group(
    topic_id: UUID,
    repository: Annotated[Repository, Depends(get_repository)],
    x_participant_id: Annotated[str | None, Header(alias="X-Participant-Id")] = None,
) -> dict[str, object]:
    """Return the participant's assigned group for a topic, or 404 if not joined."""
    participant = await _resolve_participant(repository, x_participant_id)
    group = await repository.get_participant_group_for_topic(participant.id, topic_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not joined.")
    return {
        "id": str(group.id),
        "topic_id": str(group.topic_id),
        "telegram_topic_name": group.telegram_topic_name,
        "capacity": group.capacity,
        "member_count": group.member_count,
    }


@router.post("/topics/{topic_id}/join", response_model=ChatJoinResponse)
async def join_topic(
    topic_id: UUID,
    repository: Annotated[Repository, Depends(get_repository)],
    x_participant_id: Annotated[str | None, Header(alias="X-Participant-Id")] = None,
) -> ChatJoinResponse:
    """Assign the participant to a group and return the group with message history."""
    participant = await _resolve_participant(repository, x_participant_id)

    topic = await repository.get_topic(topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    if topic.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Topic is closed; new participants cannot join.",
        )

    service = WebGroupAssignmentService(repository)
    result = await service.assign_participant(
        topic_id=topic_id,
        participant_id=participant.id,
        topic=topic,
    )

    raw_messages = await repository.list_messages_for_group(result.group.id)
    display_names = await _resolve_display_names(repository, list(raw_messages))
    messages = [_message_to_response(m, display_names[m.id]) for m in raw_messages]

    return ChatJoinResponse(
        group=result.group,
        messages=messages,
        already_member=result.already_member,
    )


@router.get("/groups/{group_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    group_id: UUID,
    repository: Annotated[Repository, Depends(get_repository)],
    x_participant_id: Annotated[str | None, Header(alias="X-Participant-Id")] = None,
) -> list[ChatMessageResponse]:
    """Return all messages for a group (participant must be a member)."""
    participant = await _resolve_participant(repository, x_participant_id)
    topic_id = await _require_group(repository, group_id)
    member_group = await repository.get_participant_group_for_topic(participant.id, topic_id)
    if member_group is None or member_group.id != group_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member.")

    raw_messages = await repository.list_messages_for_group(group_id)
    display_names = await _resolve_display_names(repository, list(raw_messages))
    return [_message_to_response(m, display_names[m.id]) for m in raw_messages]


@router.post("/groups/{group_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    group_id: UUID,
    payload: dict[str, str],
    request: Request,
    repository: Annotated[Repository, Depends(get_repository)],
    x_participant_id: Annotated[str | None, Header(alias="X-Participant-Id")] = None,
) -> ChatMessageResponse:
    """Send a message to a group."""
    participant = await _resolve_participant(repository, x_participant_id)

    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="text is required.",
        )
    if len(text) > _MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message too long.",
        )

    topic_id = await _require_group(repository, group_id)
    member_group = await repository.get_participant_group_for_topic(participant.id, topic_id)
    if member_group is None or member_group.id != group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group."
        )

    stored = await repository.store_web_message(
        group_id=group_id,
        participant_id=participant.id,
        display_name=participant.display_name,
        text=text,
    )
    response = _message_to_response(stored, participant.display_name)
    await _publish(request, group_id, response)
    return response


@router.get("/groups/{group_id}/stream")
async def stream_messages(
    group_id: UUID,
    request: Request,
    participant_id: str | None = None,
) -> StreamingResponse:
    """SSE stream of new messages for a group.

    Yields ``data: <json>`` events for each new message and ``: heartbeat``
    comments every 25 seconds to keep the connection alive.

    ``participant_id`` is accepted as a query parameter because the browser
    EventSource API does not support custom request headers.

    A short-lived DB connection is opened only for the three upfront validation
    queries, then closed before the long-running stream begins.  This prevents
    an idle connection from blocking Neon scale-to-zero for the lifetime of a
    browser tab.
    """
    # Validate membership with a short-lived connection; close before streaming.
    if hasattr(request.app.state, "repository"):
        repository: Repository = request.app.state.repository
        participant = await _resolve_participant(repository, participant_id)
        topic_id = await _require_group(repository, group_id)
        member_group = await repository.get_participant_group_for_topic(participant.id, topic_id)
    else:
        settings = get_runtime_settings(request)
        conn = await asyncpg.connect(settings.database_url, statement_cache_size=0)
        try:
            repo = PostgresRepository(conn)
            participant = await _resolve_participant(repo, participant_id)
            topic_id = await _require_group(repo, group_id)
            member_group = await repo.get_participant_group_for_topic(participant.id, topic_id)
        finally:
            await conn.close()

    if member_group is None or member_group.id != group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group."
        )

    queue: asyncio.Queue[ChatMessageResponse] = asyncio.Queue()
    subscribers: list[asyncio.Queue[ChatMessageResponse]] = (
        request.app.state.group_subscribers.setdefault(group_id, [])
    )
    subscribers.append(queue)

    async def event_generator() -> AsyncIterator[str]:
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"data: {json.dumps(_serialize_message(msg))}\n\n"
                except TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            with contextlib.suppress(ValueError):
                subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
