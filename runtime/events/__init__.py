"""runtime/events package — event schema & type registry."""
from runtime.events.base_event import BaseEvent
from runtime.events.event_types import EventType

__all__ = ["BaseEvent", "EventType"]
