"""User activity timeline with persistence and productivity analysis."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("ai-companion.world.timeline")

try:
    from config.config import WRITABLE_ROOT
    _TIMELINE_PATH = WRITABLE_ROOT / "data" / "user_timeline.json"
except Exception:
    _TIMELINE_PATH = Path("data") / "user_timeline.json"


@dataclass
class TimelineEvent:
    """An event on the user activity timeline."""
    activity: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "activity": self.activity,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds
        }


class ActivityTimeline:
    """Chronologically logs, retrieves, and analyzes user activities with persistence."""

    def __init__(self, file_path: Path | None = None) -> None:
        self.file_path = file_path or _TIMELINE_PATH
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._events: List[TimelineEvent] = []
        self._load()

    def _load(self) -> None:
        if self.file_path.exists() and self.file_path.stat().st_size > 0:
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        self._events.append(TimelineEvent(
                            activity=item["activity"],
                            start_time=item["start_time"],
                            end_time=item["end_time"],
                            duration_seconds=item["duration_seconds"]
                        ))
            except Exception as e:
                logger.error("Failed to load activity timeline: %s", e)

    def _save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([e.to_dict() for e in self._events], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save activity timeline: %s", e)

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
        self._save()

    def get_recent_events(self, limit: int = 10) -> List[TimelineEvent]:
        """Get the most recent timeline events."""
        return self._events[-limit:]

    def get_productivity_summary(self) -> Dict[str, float]:
        """Calculate percentage breakdown of user activities."""
        now = time.time()
        durations: Dict[str, float] = {}
        total = 0.0
        
        for e in self._events:
            dur = e.duration_seconds
            if e.end_time is None:
                dur = now - e.start_time
            durations[e.activity] = durations.get(e.activity, 0.0) + dur
            total += dur
            
        if total == 0:
            return {}
            
        return {act: round((dur / total) * 100.0, 1) for act, dur in durations.items()}


# Global singleton
activity_timeline = ActivityTimeline()
