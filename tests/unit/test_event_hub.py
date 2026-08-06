import asyncio

import pytest

from app.event_hub import SmartFrameEventHub


@pytest.mark.asyncio
async def test_event_hub_subscription_and_broadcast():
    hub = SmartFrameEventHub()
    queue = hub.subscribe()

    playlist = [
        {
            "filename": "image_1.png",
            "url": "image_1.png?v=1",
            "label": "Latest",
            "index": 0,
        },
        {
            "filename": "image_2.png",
            "url": "image_2.png?v=1",
            "label": "T-5m",
            "index": 1,
        },
        {
            "filename": "image_3.png",
            "url": "image_3.png?v=1",
            "label": "T-10m",
            "index": 2,
        },
    ]

    hub.set_playlist(playlist, active_index=0)

    # Verify message in subscriber queue
    msg = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert "event: new_photo" in msg
    assert "image_1.png?v=1" in msg

    # Test rotation (0 -> 1 -> 2 -> 0)
    state1 = hub.rotate()
    assert state1["active_index"] == 1
    assert state1["active_image_url"] == "image_2.png?v=1"

    msg_rot1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert "event: rotate" in msg_rot1
    assert "image_2.png?v=1" in msg_rot1

    state2 = hub.rotate()
    assert state2["active_index"] == 2
    assert state2["active_image_url"] == "image_3.png?v=1"

    state3 = hub.rotate()
    assert state3["active_index"] == 0
    assert state3["active_image_url"] == "image_1.png?v=1"

    # Test specific jump
    state_jump = hub.rotate(next_index=2)
    assert state_jump["active_index"] == 2

    # Unsubscribe
    hub.unsubscribe(queue)
    assert hub.get_state()["subscriber_count"] == 0
