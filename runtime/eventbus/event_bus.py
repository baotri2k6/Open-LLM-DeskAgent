"""In-process event bus used by services and agents.

Nâng cấp để hỗ trợ cả định dạng cũ publish(event_type, payload)
và định dạng mới của BaseEvent schema.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Union

from runtime.events.base_event import BaseEvent


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], None]) -> None:
        self._subscribers[event_type].append(callback)

    def publish(self, event: Union[BaseEvent, str], payload: dict[str, Any] | None = None) -> None:
        """Phát sự kiện đến tất cả subscribers.

        Hỗ trợ cả:
          - event_bus.publish(BaseEvent.create(...))
          - event_bus.publish("EventTypeString", {"key": "val"})
        """
        if isinstance(event, str):
            event_type = event
            event_payload = payload or {}
        else:
            event_type = event.event_type
            event_payload = event.to_dict()

        for callback in self._subscribers.get(event_type, []):
            try:
                callback(event_payload)
            except Exception as e:
                import logging
                logging.getLogger("ai-companion.eventbus").error("Error in event callback: %s", e)


# Global singleton
event_bus = EventBus()
