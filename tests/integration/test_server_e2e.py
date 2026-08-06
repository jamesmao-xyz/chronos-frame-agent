import pytest
from aiohttp.test_utils import TestClient as AioTestClient
from aiohttp.test_utils import TestServer
from fastapi.testclient import TestClient

from app.event_hub import event_hub
from app.fast_api_app import app as fastapi_app
from run_loop import create_web_application


def test_fastapi_app_initialization():
    """Verify FastAPI application initializes properly."""
    with TestClient(fastapi_app) as client:
        assert client.app.title is not None


@pytest.mark.asyncio
async def test_sse_web_server_endpoints():
    """Verify SSE web server /events, /api/state, /api/rotate and static index endpoints."""
    # Seed event_hub playlist
    event_hub.set_playlist(
        [
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
        ],
        active_index=0,
    )

    server_app = create_web_application()
    server = TestServer(server_app)
    client = AioTestClient(server)
    await client.start_server()

    try:
        # Test /api/state
        resp = await client.get("/api/state")
        assert resp.status == 200
        state = await resp.json()
        assert "playlist" in state
        assert len(state["playlist"]) >= 2
        assert state["active_index"] == 0

        # Test /api/rotate
        rot_resp = await client.post("/api/rotate", json={"index": 1})
        assert rot_resp.status == 200
        rot_state = await rot_resp.json()
        assert rot_state["active_index"] == 1

        # Test index.html serving
        index_resp = await client.get("/")
        assert index_resp.status == 200
        html = await index_resp.text()
        assert "Chronos Smart Frame" in html
        assert "EventSource" in html

    finally:
        await client.close()
