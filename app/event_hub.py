import asyncio
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class SmartFrameEventHub:
    """
    Manages Server-Sent Events (SSE) subscriptions, smart frame active state,
    and broadcasts photo rotation and new bulletin generation events to connected clients.
    """

    def __init__(self):
        self._subscribers: set[asyncio.Queue] = set()
        self._active_index: int = 0
        self._playlist: list[dict[str, Any]] = []
        self._version: int = 0
        self._rotation_interval_seconds: int = 300
        self._last_updated: str = datetime.now().isoformat()

    def get_state(self) -> dict[str, Any]:
        """Returns the current state snapshot of the smart frame playlist."""
        active_item = self._playlist[self._active_index] if self._playlist else None
        return {
            "version": self._version,
            "active_index": self._active_index,
            "active_image_url": active_item["url"] if active_item else "image_1.png",
            "active_label": active_item.get("label", "Latest Bulletin")
            if active_item
            else "Latest Bulletin",
            "rotation_interval_seconds": self._rotation_interval_seconds,
            "playlist": self._playlist,
            "subscriber_count": len(self._subscribers),
            "last_updated": self._last_updated,
        }

    def set_rotation_interval(self, seconds: int) -> None:
        """Sets the slideshow rotation interval."""
        self._rotation_interval_seconds = max(5, seconds)

    def set_playlist(
        self, playlist: list[dict[str, Any]], active_index: int = 0
    ) -> None:
        """
        Updates the playlist (e.g. after PublisherTool runs) and broadcasts a new_photo event.
        """
        self._playlist = playlist
        self._version += 1
        self._active_index = (
            min(active_index, max(0, len(playlist) - 1)) if playlist else 0
        )
        self._last_updated = datetime.now().isoformat()

        logger.info(
            f"EventHub: Playlist updated (v{self._version}) with {len(playlist)} items. Broadcasting to {len(self._subscribers)} clients."
        )
        self.broadcast(event_type="new_photo", data=self.get_state())

    def rotate(self, next_index: int | None = None) -> dict[str, Any]:
        """
        Rotates the currently active photo to the next photo in the FIFO queue (0 -> 1 -> 2 -> 0).
        """
        if not self._playlist:
            return self.get_state()

        if next_index is not None:
            self._active_index = next_index % len(self._playlist)
        else:
            self._active_index = (self._active_index + 1) % len(self._playlist)

        state = self.get_state()
        logger.debug(
            f"EventHub: Rotated active photo to index {self._active_index} ({state['active_image_url']})"
        )
        self.broadcast(event_type="rotate", data=state)
        return state

    def subscribe(self) -> asyncio.Queue:
        """Subscribes a new client and returns an async queue for SSE messages."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        logger.info(
            f"EventHub: New SSE client connected. Active subscribers: {len(self._subscribers)}"
        )
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Removes a client queue when disconnected."""
        self._subscribers.discard(queue)
        logger.info(
            f"EventHub: SSE client disconnected. Active subscribers: {len(self._subscribers)}"
        )

    def broadcast(self, event_type: str, data: Any) -> None:
        """Pushes an SSE-formatted string to all connected subscriber queues."""
        message = self.format_sse_message(event_type=event_type, data=data)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("EventHub: Dropping message for slow subscriber queue.")

    @staticmethod
    def format_sse_message(event_type: str, data: Any) -> str:
        """Formats data into standard Server-Sent Events (SSE) wire format."""
        if isinstance(data, dict | list):
            data_str = json.dumps(data)
        else:
            data_str = str(data)
        return f"event: {event_type}\ndata: {data_str}\n\n"


# Global singleton event hub instance
event_hub = SmartFrameEventHub()
