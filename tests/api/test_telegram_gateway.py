from __future__ import annotations

from msdp_api.telegram.gateway import build_assignment_message


def test_build_assignment_message_uses_welcome_guidelines() -> None:
    message = build_assignment_message(
        invite_link="https://t.me/joinchat/group-1",
        thread_id=1001,
        topic_title="Should cities restrict private cars in downtown areas?",
    )

    assert "Welcome to the CORDA Deliberation Group Chat." in message
    assert (
        "Below is your link to join a group to discuss Should cities restrict private cars"
        in message
    )
    assert "https://t.me/joinchat/group-1" in message
    assert "After joining, open forum topic #1001 in the sidebar." in message
    assert "- Add your perspective" in message
    assert "There are no right or wrong opinions" in message
