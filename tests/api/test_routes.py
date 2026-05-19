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


def test_admin_creates_topic_with_cross_pollination_interval(client):
    response = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={
            "title": "Cross-pollination cadence",
            "cross_pollination_interval_seconds": 3_600,
        },
    )

    assert response.status_code == 200
    topic = response.json()["topic"]
    assert topic["cross_pollination_interval_seconds"] == 3_600
    assert topic["next_cross_pollination_at"] is not None


def test_admin_suggests_topic_fields(client, topic_suggestion_service):
    response = client.post(
        "/admin/topics/suggest",
        headers={"X-Admin-Key": "admin-key"},
        json={
            "title": "Should city streets prioritize bikes?",
            "description": "Current draft",
            "seed_bullets": ["Existing prompt"],
        },
    )

    assert response.status_code == 200
    suggestion = response.json()
    assert suggestion["description"].startswith("Discuss Should city streets prioritize bikes?")
    assert len(suggestion["seed_bullets"]) == 4
    assert topic_suggestion_service.requests == [
        {
            "title": "Should city streets prioritize bikes?",
            "description": "Current draft",
            "seed_bullets": ["Existing prompt"],
        },
    ]


def test_list_topics_newest_first(client):
    first = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "First discussion", "description": "Earlier topic."},
    ).json()["topic"]
    second = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Second discussion", "description": "Later topic."},
    ).json()["topic"]

    response = client.get("/topics")

    assert response.status_code == 200
    topics = response.json()
    assert [item["id"] for item in topics] == [second["id"], first["id"]]
    assert topics[0]["status"] == "active"
    assert topics[0]["created_at"] is not None


def test_get_topic(client):
    topic = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Cars downtown", "description": "Discuss car restrictions."},
    ).json()["topic"]

    response = client.get(f"/topics/{topic['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Cars downtown"
    assert response.json()["status"] == "active"


def test_admin_requires_correct_key(client):
    response = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "wrong"},
        json={"title": "Nope"},
    )

    assert response.status_code == 401


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


def test_admin_dashboard_includes_topic_group_and_activity(client, repository):
    topic = asyncio.run(repository.create_topic(TopicCreate(title="Dashboard topic")))
    group = asyncio.run(
        repository.create_group(
            topic_id=topic.id,
            thread_id=1,
            invite_link="https://example.com/1",
            capacity=2,
            telegram_topic_name="Group 1",
        ),
    )
    asyncio.run(repository.increment_group_member_count(group.id))
    asyncio.run(
        repository.store_thread_message(
            ThreadMessage(
                message_id=1,
                thread_id=1,
                group_id=group.id,
                telegram_user_id=1,
                username="participant",
                first_name="Participant",
                text="One message.",
                sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
            ),
        ),
    )
    asyncio.run(repository.upsert_summary(group.id, "- Summary"))

    response = client.get("/admin/dashboard", headers={"X-Admin-Key": "admin-key"})

    assert response.status_code == 200
    dashboard = response.json()
    assert dashboard["active_topic_id"] == str(topic.id)
    assert dashboard["topics"][0]["topic"]["title"] == "Dashboard topic"
    assert dashboard["topics"][0]["participant_count"] == 1
    assert dashboard["topics"][0]["message_count"] == 1
    assert dashboard["topics"][0]["summary_count"] == 1
    assert dashboard["topics"][0]["groups"][0]["has_summary"] is True


def test_admin_updates_topic_end_and_derives_status(client):
    topic = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Topic with adjustable end"},
    ).json()["topic"]

    future_update = client.patch(
        f"/admin/topics/{topic['id']}",
        headers={"X-Admin-Key": "admin-key"},
        json={"closes_at": "3026-05-04T15:00:00Z"},
    )
    past_update = client.patch(
        f"/admin/topics/{topic['id']}",
        headers={"X-Admin-Key": "admin-key"},
        json={"closes_at": "2026-04-30T10:00:00Z"},
    )

    assert future_update.status_code == 200
    assert future_update.json()["topic"]["title"] == "Topic with adjustable end"
    assert future_update.json()["topic"]["status"] == "active"
    assert past_update.status_code == 200
    assert past_update.json()["topic"]["status"] == "closed"


def test_admin_updates_cross_pollination_interval_without_clearing_end(client):
    topic = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Adjust cadence", "closes_at": "3026-05-04T15:00:00Z"},
    ).json()["topic"]

    response = client.patch(
        f"/admin/topics/{topic['id']}",
        headers={"X-Admin-Key": "admin-key"},
        json={"cross_pollination_interval_seconds": 7_200},
    )

    assert response.status_code == 200
    updated = response.json()["topic"]
    assert updated["cross_pollination_interval_seconds"] == 7_200
    assert updated["closes_at"] == "3026-05-04T15:00:00Z"
    assert updated["next_cross_pollination_at"] is not None


def test_admin_rejects_naive_topic_end_datetime(client):
    topic = client.post(
        "/admin/topics",
        headers={"X-Admin-Key": "admin-key"},
        json={"title": "Timezone validation"},
    ).json()["topic"]

    response = client.patch(
        f"/admin/topics/{topic['id']}",
        headers={"X-Admin-Key": "admin-key"},
        json={"closes_at": "2026-05-01T10:00:00"},
    )

    assert response.status_code == 422


def test_admin_list_group_messages(client, repository):
    topic = asyncio.run(repository.create_topic(TopicCreate(title="Transcript topic")))
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
                text="Transcript message.",
                sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
            ),
        ),
    )

    response = client.get(
        f"/admin/groups/{group.id}/messages",
        headers={"X-Admin-Key": "admin-key"},
    )

    assert response.status_code == 200
    assert response.json()[0]["text"] == "Transcript message."


def test_admin_summarize_due_topics(client, repository):
    due_topic = asyncio.run(
        repository.create_topic(
            TopicCreate(
                title="Closed discussion",
                closes_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
            ),
        ),
    )
    future_topic = asyncio.run(
        repository.create_topic(
            TopicCreate(
                title="Future discussion",
                closes_at=datetime(3026, 4, 23, 10, 0, tzinfo=UTC),
            ),
        ),
    )
    asyncio.run(
        repository.create_group(
            topic_id=due_topic.id,
            thread_id=1,
            invite_link="https://example.com/1",
            capacity=2,
            telegram_topic_name="Group 1",
        ),
    )

    response = client.post("/admin/summarize-due", headers={"X-Admin-Key": "admin-key"})

    assert response.status_code == 200
    assert len(response.json()["summarized_topics"]) == 1
    assert response.json()["summarized_topics"][0]["topic_id"] == str(due_topic.id)
    assert asyncio.run(repository.get_topic(due_topic.id)).status == "closed"
    assert asyncio.run(repository.get_topic(future_topic.id)).status == "active"


def test_admin_cross_pollinate_due_topics(client, repository):
    due_topic = asyncio.run(
        repository.create_topic(
            TopicCreate(title="Due sharing", cross_pollination_interval_seconds=60),
        ),
    )
    groups = [
        asyncio.run(
            repository.create_group(
                topic_id=due_topic.id,
                thread_id=thread_id,
                invite_link=f"https://example.com/{thread_id}",
                capacity=2,
                telegram_topic_name=f"Group {thread_id}",
            ),
        )
        for thread_id in (1, 2)
    ]
    for group in groups:
        asyncio.run(
            repository.store_thread_message(
                ThreadMessage(
                    message_id=group.thread_id,
                    thread_id=group.thread_id,
                    group_id=group.id,
                    telegram_user_id=1,
                    username="participant",
                    first_name="Participant",
                    text=f"Message from {group.telegram_topic_name}.",
                    sent_at=datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
                ),
            ),
        )
    asyncio.run(
        repository.schedule_next_cross_pollination(
            due_topic.id,
            datetime(2026, 4, 23, 10, 0, tzinfo=UTC),
        ),
    )

    response = client.post("/admin/cross-pollinate-due", headers={"X-Admin-Key": "admin-key"})

    assert response.status_code == 200
    assert len(response.json()["cross_pollinated_topics"]) == 1
    assert response.json()["cross_pollinated_topics"][0]["comments_posted"] == 2
    moderator_msgs = [
        msg
        for msgs in (asyncio.run(repository.list_messages_for_group(g.id)) for g in groups)
        for msg in msgs
        if msg.is_moderator
    ]
    assert len(moderator_msgs) == 2


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
