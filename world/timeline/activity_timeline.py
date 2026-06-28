"""User activity timeline."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger("ai-companion.world.timeline")


@dataclass
class TimelineEvent:
    """An event on the user activity timeline."""
    activity: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_seconds: float = 0.0


class ActivityTimeline:
    """Chronologically logs and retrieves user activities."""

    def __init__(self) -> None:
        self._events: List[TimelineEvent] = []

    def record_activity(self, activity: str) -> None:
        """Record the start of a new user activity, ending the previous one if active."""
        now = time.time()
        
        # 1. Close current event
        if self._events and self._events[-1].end_time is None:
            prev = self._events[-1]
            prev.end_time = now
            prev.duration_seconds = now - prev.start_time
            
        # 2. Add new event
        evt = TimelineEvent(activity=activity, start_time=now)
        self._events.append(evt)
        logger.info("ActivityTimeline: Recorded new activity '%s'", activity)

    def get_recent_events(self, limit: int = 10) -> List[TimelineEvent]:
        """Get the most recent timeline events."""
        return self._events[-limit:]


# Global singleton
activity_timeline = ActivityTimeline()
