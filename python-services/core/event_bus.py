"""In-process event bus used by services and agents."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        for callback in self._subscribers.get(event_type, []):
            callback(payload)


event_bus = EventBus()
