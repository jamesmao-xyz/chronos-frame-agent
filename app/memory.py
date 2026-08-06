import json
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Persistent history storage path in smart_frame_web directory
MEMORY_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "smart_frame_web", ".headline_history.json"
    )
)


class HeadlineMemory:
    """
    Manages agent memory of previously featured headlines using a strict sliding window
    to prevent repetitive stories across the 3-image FIFO gallery without unbounded growth.
    """

    def __init__(self, filepath: str = MEMORY_FILE, max_history: int = 25):
        self.filepath = filepath
        self.max_history = (
            max_history  # Strict sliding window cap (last ~5 generation cycles)
        )
        self._history: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Loads headline history from disk if exists, applying sliding window cap."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    raw_history = data.get("history", [])
                    # Enforce strict sliding window on load
                    self._history = raw_history[-self.max_history :]
            except Exception as e:
                logger.warning(
                    f"Failed to load headline memory from {self.filepath}: {e}"
                )
                self._history = []
        else:
            self._history = []

    def _save(self) -> None:
        """Persists bounded headline history to disk."""
        try:
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "updated_at": datetime.now().isoformat(),
                        "total_count": len(self._history),
                        "history": self._history[-self.max_history :],
                    },
                    f,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"Failed to save headline memory to {self.filepath}: {e}")

    def get_recent_headlines(self, limit: int = 15) -> list[str]:
        """
        Returns the list of recently featured headline titles.
        Default limit is 15 (matching the 3-image FIFO gallery: 3 images x 5 headlines).
        """
        return [item["title"] for item in self._history[-limit:] if "title" in item]

    def is_duplicate(self, title: str) -> bool:
        """
        Checks if a headline is a duplicate of a recently used headline using keyword matching.
        """
        normalized_input = self._normalize(title)
        input_keywords = {w for w in normalized_input.split() if len(w) > 3}
        if not input_keywords:
            return False

        for item in self._history[-self.max_history :]:
            past_title = item.get("title", "")
            normalized_past = self._normalize(past_title)
            past_keywords = {w for w in normalized_past.split() if len(w) > 3}

            # Jaccard keyword overlap
            intersection = input_keywords.intersection(past_keywords)
            union = input_keywords.union(past_keywords)
            if union and (len(intersection) / len(union)) > 0.45:
                return True
        return False

    def add_headlines(self, headlines: list[str]) -> None:
        """Records newly featured headlines into memory, discarding oldest outside sliding window."""
        now_str = datetime.now().isoformat()
        for h in headlines:
            clean_title = self._clean_title(h)
            if clean_title:
                self._history.append(
                    {"title": clean_title, "raw": h, "timestamp": now_str}
                )
        # Strictly truncate history to sliding window size
        self._history = self._history[-self.max_history :]
        self._save()

    def clear(self) -> None:
        """Clears memory history (used for tests)."""
        self._history = []
        if os.path.exists(self.filepath):
            try:
                os.remove(self.filepath)
            except Exception:
                pass

    @staticmethod
    def _clean_title(headline: str) -> str:
        """Extracts title part from formatted headline line (e.g. '1. Title: Summary')."""
        line = headline.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            parts = line.split(".", 1)
            if len(parts) > 1:
                line = parts[1].strip()
        if ":" in line:
            return line.split(":", 1)[0].strip()
        return line.strip()

    @staticmethod
    def _normalize(text: str) -> str:
        """Lowercases and strips punctuation."""
        return "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in text)


# Global singleton instance
memory = HeadlineMemory()
