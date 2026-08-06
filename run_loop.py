#!/usr/bin/env python3
"""
Chronos Frame Agent Scheduler & SSE Web Server Runner.
Runs the ADK 2.0 Graph Workflow Agent on a periodic schedule while serving `smart_frame_web/`
over HTTP with real-time Server-Sent Events (SSE) for seamless, race-condition-free photo rotation.
"""

import asyncio
import json
import logging
import os
from datetime import datetime

from aiohttp import web
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from app.agent import app
from app.event_hub import event_hub

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("ChronosRunner")

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "smart_frame_web"))
PORT = int(os.environ.get("PORT", "8168"))
SCHEDULE_INTERVAL_SECONDS = int(os.environ.get("SCHEDULE_INTERVAL_SECONDS", "900"))
ROTATION_INTERVAL_SECONDS = int(os.environ.get("ROTATION_INTERVAL_SECONDS", "300"))


def init_event_hub_from_disk():
    """Initializes EventHub playlist state from existing files on disk upon startup."""
    event_hub.set_rotation_interval(ROTATION_INTERVAL_SECONDS)
    playlist_path = os.path.join(WEB_DIR, "playlist.json")

    if os.path.exists(playlist_path):
        try:
            with open(playlist_path, encoding="utf-8") as f:
                data = json.load(f)
                loaded_playlist = data.get("playlist", [])
                if loaded_playlist:
                    event_hub.set_playlist(loaded_playlist, active_index=0)
                    logger.info(
                        f"Loaded {len(loaded_playlist)} playlist items from disk."
                    )
                    return
        except Exception as e:
            logger.warning(f"Could not load playlist.json from disk: {e}")

    # Fallback to inspecting static image files
    v_tag = int(datetime.now().timestamp())
    found_playlist = []
    for idx, name in enumerate(["image_1.png", "image_2.png", "image_3.png"]):
        fpath = os.path.join(WEB_DIR, name)
        if os.path.exists(fpath):
            label = "Latest Bulletin" if idx == 0 else f"-{idx * 15} min"
            found_playlist.append(
                {
                    "filename": name,
                    "url": f"{name}?v={v_tag}",
                    "label": f"{name} ({label})",
                    "age": label,
                    "timestamp": datetime.now().strftime("%A, %B %d, %Y • %H:%M"),
                    "index": idx,
                }
            )
    if found_playlist:
        event_hub.set_playlist(found_playlist, active_index=0)
        logger.info(
            f"Initialized EventHub with {len(found_playlist)} discovered images."
        )


async def sse_events_handler(request: web.Request) -> web.StreamResponse:
    """
    SSE stream endpoint (/events) that pushes real-time photo rotation and new bulletin updates
    to connected smart frame displays (e.g. Fully Kiosk Browser on Lenovo Smart Frame).
    """
    response = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "X-Accel-Buffering": "no",
        },
    )
    await response.prepare(request)

    # Send initial state snapshot immediately to newly connected client
    init_msg = event_hub.format_sse_message("init", event_hub.get_state())
    await response.write(init_msg.encode("utf-8"))

    client_queue = event_hub.subscribe()
    try:
        while True:
            try:
                # Wait for next event or send keepalive ping every 15 seconds
                msg = await asyncio.wait_for(client_queue.get(), timeout=15.0)
                await response.write(msg.encode("utf-8"))
            except TimeoutError:
                # Keepalive comment to prevent connection dropouts on Wi-Fi / Kiosk browsers
                keepalive = ": keepalive\n\n"
                await response.write(keepalive.encode("utf-8"))
    except (asyncio.CancelledError, ConnectionResetError, web.HTTPException):
        pass
    finally:
        event_hub.unsubscribe(client_queue)

    return response


async def api_state_handler(request: web.Request) -> web.Response:
    """Returns current smart frame playlist state."""
    return web.json_response(event_hub.get_state())


async def api_rotate_handler(request: web.Request) -> web.Response:
    """Manually rotates the active photo or jumps to a specific index."""
    try:
        body = await request.json()
        target_index = body.get("index")
    except Exception:
        target_index = None

    state = event_hub.rotate(next_index=target_index)
    return web.json_response(state)


background_tasks: set[asyncio.Task] = set()


async def api_trigger_generation_handler(request: web.Request) -> web.Response:
    """Triggers an immediate background agent generation workflow cycle."""
    task = asyncio.create_task(run_agent_workflow())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return web.json_response(
        {"status": "triggered", "timestamp": datetime.now().isoformat()}
    )


async def index_handler(request: web.Request) -> web.FileResponse:
    """Serves the smart frame display index.html."""
    index_file = os.path.join(WEB_DIR, "index.html")
    return web.FileResponse(index_file)


def create_web_application() -> web.Application:
    """Configures the aiohttp web server application."""
    os.makedirs(WEB_DIR, exist_ok=True)
    server_app = web.Application()

    # SSE & API endpoints
    server_app.router.add_get("/events", sse_events_handler)
    server_app.router.add_get("/api/state", api_state_handler)
    server_app.router.add_post("/api/rotate", api_rotate_handler)
    server_app.router.add_post("/api/generate", api_trigger_generation_handler)

    # Static file serving (explicit index.html + assets)
    server_app.router.add_get("/", index_handler)
    server_app.router.add_get("/index.html", index_handler)
    server_app.router.add_static("/", WEB_DIR, show_index=False, follow_symlinks=True)
    return server_app


async def run_agent_workflow():
    """Executes a single cycle of the ADK 2.0 Graph Workflow Agent."""
    runner = InMemoryRunner(app=app)
    session = await runner.session_service.create_session(
        app_name="chronos_frame_agent", user_id="smart_frame_user"
    )
    logger.info("Triggering Chronos Frame Agent workflow cycle...")

    try:
        async for event in runner.run_async(
            user_id="smart_frame_user",
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part.from_text(text="Generate new smart frame bulletin")],
            ),
        ):
            if event.output:
                logger.info(f"Workflow node output: {event.output}")
    except Exception as e:
        logger.error(f"Error during agent workflow execution: {e}")


async def photo_rotation_loop(interval_seconds: int = 30):
    """
    Background coordinator that smoothly advances the active photo (0 -> 1 -> 2 -> 0)
    every interval_seconds and broadcasts the rotation event to all SSE clients.
    """
    logger.info(f"Starting photo rotation loop ({interval_seconds}s interval)...")
    while True:
        await asyncio.sleep(interval_seconds)
        state = event_hub.get_state()
        if state.get("playlist") and len(state["playlist"]) > 1:
            event_hub.rotate()


async def scheduler_loop(interval_seconds: int = 300):
    """
    Periodic background loop that triggers fresh news fetching and image generation
    via the ADK agent workflow.
    """
    logger.info(
        f"Starting autonomous generation schedule loop ({interval_seconds}s interval)..."
    )
    while True:
        try:
            await run_agent_workflow()
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        await asyncio.sleep(interval_seconds)


async def main_async():
    """Main async entrypoint running web server, photo rotation, and generation scheduler."""
    init_event_hub_from_disk()

    # Configure and start aiohttp web server
    server_app = create_web_application()
    runner = web.AppRunner(server_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(
        f"Chronos Smart Frame SSE Server running on http://0.0.0.0:{PORT} serving {WEB_DIR}"
    )

    # Launch background tasks concurrently
    rotation_task = asyncio.create_task(
        photo_rotation_loop(interval_seconds=ROTATION_INTERVAL_SECONDS)
    )
    scheduler_task = asyncio.create_task(
        scheduler_loop(interval_seconds=SCHEDULE_INTERVAL_SECONDS)
    )

    try:
        await asyncio.gather(rotation_task, scheduler_task)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down Chronos web runner...")
        await runner.cleanup()


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Chronos Frame Agent runner stopped by user.")


if __name__ == "__main__":
    main()
