"""In-process async-enabled event bus used by services and agents.

Supports both synchronous and asynchronous subscriber callbacks,
and accepts both string/payload publishes and BaseEvent schema publishes.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Union

from runtime.events.base_event import BaseEvent

logger = logging.getLogger("ai-companion.eventbus")


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[dict[str, Any]], Any]]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable[[dict[str, Any]], Any]) -> None:
        """Register a subscriber callback for an event type.

        Callback can be either synchronous or asynchronous.
        """
        self._subscribers[event_type].append(callback)
        logger.debug("Subscribed to %s", event_type)

    def publish(self, event: Union[BaseEvent, str], payload: dict[str, Any] | None = None) -> None:
        """Publishes an event to all subscribers.

        Dispatches synchronously for standard callables, and schedules
        async callables (coroutines) on the running event loop.
        """
        if isinstance(event, str):
            event_type = event
            event_payload = payload or {}
        else:
            event_type = event.event_type
            event_payload = event.to_dict()

        for callback in self._subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    # Check if there is a running event loop
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(callback(event_payload))
                    except RuntimeError:
                        # Fallback if no loop is running
                        asyncio.run(callback(event_payload))
                else:
                    callback(event_payload)
            except Exception as e:
                logger.error("Error in event callback for event %s: %s", event_type, e)

    async def publish_async(self, event: Union[BaseEvent, str], payload: dict[str, Any] | None = None) -> None:
        """Publishes an event and awaits all asynchronous subscribers."""
        if isinstance(event, str):
            event_type = event
            event_payload = payload or {}
        else:
            event_type = event.event_type
            event_payload = event.to_dict()

        tasks = []
        for callback in self._subscribers.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event_payload))
                else:
                    callback(event_payload)
            except Exception as e:
                logger.error("Error invoking subscriber for event %s: %s", event_type, e)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Global singleton
event_bus = EventBus()
