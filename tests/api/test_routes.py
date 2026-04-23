from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from msdp_api.db.models import ThreadMessage, TopicCreate


def test_get_active_topic(client, repository):
    topic = repository.topics
    assert topic == {}
    created = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Citizens assembly", "description": "Discuss climate policy."},
    )
    assert created.status_code == 200

    response = client.get("/topics/active")

    assert response.status_code == 200
    assert response.json()["title"] == "Citizens assembly"


def test_admin_requires_correct_key(client):
    response = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "wrong"},
        json={"title": "Nope"},
    )

    assert response.status_code == 401


def test_webhook_start_assigns_group(client, repository, telegram_gateway):
    topic = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Housing"},
    ).json()["topic"]

    response = client.post(
        "/webhook/telegram",
        json={
            "update_id": 1,
            "message": {
                "message_id": 11,
                "date": 1_713_873_600,
                "text": f"/start {topic['id']}",
                "from": {"id": 42, "username": "participant", "first_name": "Pat"},
            },
        },
    )

    assert response.status_code == 200
    assert len(repository.groups) == 1
    assert len(repository.memberships) == 1
    assert telegram_gateway.sent_messages[0]["chat_id"] == 42


def test_admin_summarize_topic(client, repository):
    topic = asyncio.run(repository.create_topic(TopicCreate(title="Budget priorities")))
    group = asyncio.run(
        repository.create_group(
            topic_id=topic.id,
            thread_id=1,
            invite_link="https://example.com/1",
            capacity=2,
            telegram_topic_name="Group 1",
        ),
    )
    asyncio.run(
        repository.store_thread_message(
            ThreadMessage(
                message_id=1,
                thread_id=1,
                group_id=group.id,
                telegram_user_id=1,
                username="participant",
                first_name="Participant",
                text="We should fund transit first.",
                sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
            ),
        ),
    )

    response = client.post(f"/admin/summarize/{topic.id}", headers={"X-Admin-Key": "admin-key"})

    assert response.status_code == 200
    assert response.json()["summarized_groups"] == 1


def test_get_topic_summaries(client, repository):
    topic = asyncio.run(repository.create_topic(TopicCreate(title="Food policy")))
    group = asyncio.run(
        repository.create_group(
            topic_id=topic.id,
            thread_id=1,
            invite_link="https://example.com/1",
            capacity=2,
            telegram_topic_name="Group 1",
        ),
    )
    asyncio.run(repository.upsert_summary(group.id, "- Summary"))

    response = client.get(f"/topics/{topic.id}/summaries")

    assert response.status_code == 200
    assert response.json()[0]["group_id"] == str(group.id)
