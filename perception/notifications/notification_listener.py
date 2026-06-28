"""Listens for OS-level notifications."""

from __future__ import annotations

from collections import deque
from datetime import datetime


class NotificationListener:
    """In-process notification buffer used when OS hooks are unavailable."""

    def __init__(self, max_items: int = 50) -> None:
        self._events: deque[dict] = deque(maxlen=max_items)

    def record(self, title: str, message: str = "", source: str = "system") -> dict:
        event = {
            "title": title,
            "message": message,
            "source": source,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self._events.append(event)
        return event

    def recent(self, limit: int = 10) -> list[dict]:
        return list(self._events)[-limit:]

    def clear(self) -> None:
        self._events.clear()


notification_listener = NotificationListener()
