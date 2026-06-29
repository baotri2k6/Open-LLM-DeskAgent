"""Observer — collects context snapshot for the Life Loop."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class LifeContext:
    """
    A snapshot of the current world state, used by the Life Loop
    to make decisions about autonomous behavior.
    """

    # Time context
    timestamp: float        = field(default_factory=time.time)
    hour_of_day: int        = 0       # 0–23
    day_of_week: str        = ""      # "Monday"…

    # User activity
    user_idle_seconds: float = 0.0   # seconds since last user message
    last_user_activity: str  = ""    # last detected activity (coding, gaming…)

    # Session context
    session_message_count: int = 0   # messages in current session
    session_started: bool      = False

    # Screen / world
    screen_activity: str  = "unknown"  # from ScreenWatcher

    # Companion state (filled by LifeLoop)
    mood: str          = "vui vẻ"
    emotion: str       = "neutral"
    energy: float      = 0.7

    def is_morning(self) -> bool:
        return 6 <= self.hour_of_day < 12

    def is_afternoon(self) -> bool:
        return 12 <= self.hour_of_day < 18

    def is_evening(self) -> bool:
        return 18 <= self.hour_of_day < 23

    def is_late_night(self) -> bool:
        return self.hour_of_day >= 23 or self.hour_of_day < 6

    def user_is_idle(self, threshold_seconds: float = 300) -> bool:
        return self.user_idle_seconds >= threshold_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour":          self.hour_of_day,
            "day":           self.day_of_week,
            "idle_seconds":  round(self.user_idle_seconds),
            "activity":      self.last_user_activity,
            "msg_count":     self.session_message_count,
            "mood":          self.mood,
            "emotion":       self.emotion,
            "energy":        round(self.energy, 2),
        }


class LifeObserver:
    """
    Collects a LifeContext snapshot from available system state.
    Designed to be lightweight and called frequently.
    """

    def __init__(self) -> None:
        self._last_user_message_time: float = time.time()
        self._session_message_count: int    = 0
        self._last_activity: str            = "unknown"

    def record_user_message(self) -> None:
        """Call this when the user sends a message."""
        self._last_user_message_time = time.time()
        self._session_message_count += 1

    def record_activity(self, activity: str) -> None:
        """Update the detected user activity."""
        self._last_activity = activity

    def observe(
        self,
        mood: str     = "vui vẻ",
        emotion: str  = "neutral",
        energy: float = 0.7,
    ) -> LifeContext:
        """Produce a LifeContext snapshot."""
        now = datetime.now()
        
        # Query ActivityTimeline for the most recent activity
        resolved_activity = self._last_activity
        try:
            from world.timeline.activity_timeline import activity_timeline
            recent = activity_timeline.get_recent_events(limit=1)
            if recent:
                resolved_activity = recent[0].activity
        except Exception:
            pass

        return LifeContext(
            timestamp            = time.time(),
            hour_of_day          = now.hour,
            day_of_week          = now.strftime("%A"),
            user_idle_seconds    = time.time() - self._last_user_message_time,
            last_user_activity   = resolved_activity,
            session_message_count= self._session_message_count,
            session_started      = self._session_message_count > 0,
            screen_activity      = resolved_activity,
            mood                 = mood,
            emotion              = emotion,
            energy               = energy,
        )


# ── Global singleton ───────────────────────────────────────────────────────────
life_observer = LifeObserver()
