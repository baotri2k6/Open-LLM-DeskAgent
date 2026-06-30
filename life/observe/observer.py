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
    focus_index: float       = 0.0   # 0.0 relaxed → 1.0 deeply focused

    # Session context
    session_message_count: int = 0   # messages in current session
    session_started: bool      = False

    # Screen / world
    screen_activity: str  = "unknown"  # from ScreenWatcher / WorldModel
    active_window: str    = ""
    active_app: str       = ""
    screen_text: str      = ""

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
            "focus_index":   round(self.focus_index, 2),
            "active_app":    self.active_app,
            "active_window": self.active_window,
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
        timeline_is_fresh = False
        active_window = ""
        active_app = ""
        screen_text = ""
        try:
            from world.timeline.activity_timeline import activity_timeline
            recent = activity_timeline.get_recent_events(limit=1)
            if recent:
                resolved_activity = recent[0].activity
                timeline_is_fresh = (time.time() - recent[0].start_time) < 300
        except Exception:
            pass

        # Prefer live world/activity context when available. This keeps LifeLoop
        # connected to the actual foreground app instead of relying only on
        # stale timeline entries.
        try:
            from world.activity.activity_tracker import activity_tracker
            act_info = activity_tracker.get_current_activity()
            live_activity = act_info.get("activity", "unknown")
            if live_activity and live_activity != "unknown" and (not timeline_is_fresh or resolved_activity == "unknown"):
                resolved_activity = live_activity
            active_window = act_info.get("window", "")
            active_app = act_info.get("app", "")
        except Exception:
            pass

        try:
            from api import server as api_server
            watcher = getattr(api_server, "screen_watcher", None)
            if watcher:
                watcher_activity = watcher.get_current_activity()
                if watcher_activity and watcher_activity != "unknown":
                    resolved_activity = watcher_activity
                screen_text = watcher.get_current_context() or ""
        except Exception:
            pass

        focus_index = self._compute_focus_index(
            activity=resolved_activity,
            idle_seconds=time.time() - self._last_user_message_time,
            active_app=active_app,
            active_window=active_window,
            screen_text=screen_text,
        )

        return LifeContext(
            timestamp            = time.time(),
            hour_of_day          = now.hour,
            day_of_week          = now.strftime("%A"),
            user_idle_seconds    = time.time() - self._last_user_message_time,
            last_user_activity   = resolved_activity,
            focus_index          = focus_index,
            session_message_count= self._session_message_count,
            session_started      = self._session_message_count > 0,
            screen_activity      = resolved_activity,
            active_window        = active_window,
            active_app           = active_app,
            screen_text          = screen_text,
            mood                 = mood,
            emotion              = emotion,
            energy               = energy,
        )

    def _compute_focus_index(
        self,
        activity: str,
        idle_seconds: float,
        active_app: str = "",
        active_window: str = "",
        screen_text: str = "",
    ) -> float:
        """Estimate whether the user is in a focus-heavy workflow."""
        score = 0.0
        activity = (activity or "").lower()
        app_text = f"{active_app} {active_window}".lower()
        screen = (screen_text or "").lower()

        if activity in {"coding", "terminal_work", "working_document"}:
            score += 0.45
        if any(token in app_text for token in ["code", "terminal", "powershell", "pycharm", "intellij"]):
            score += 0.25
        if any(token in screen for token in ["traceback", "error:", "def ", "class ", "import ", "npm ", "pytest"]):
            score += 0.2
        if idle_seconds < 120:
            score += 0.1
        elif idle_seconds > 900:
            score -= 0.25

        return round(max(0.0, min(1.0, score)), 3)


# ── Global singleton ───────────────────────────────────────────────────────────
life_observer = LifeObserver()
