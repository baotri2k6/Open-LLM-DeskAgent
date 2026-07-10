"""Tracks user habits and preferences."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.persona.habits")


class HabitTracker:
    """Tracks user habits and preferences."""

    def __init__(self) -> None:
        self.habits: dict[str, int] = {}

    def record_activity(self, activity: str) -> None:
        self.habits[activity] = self.habits.get(activity, 0) + 1
        logger.info("HabitTracker: Recorded activity '%s' (count=%d)", activity, self.habits[activity])

    def get_frequent_activity(self) -> str:
        if not self.habits:
            return "unknown"
        return max(self.habits, key=self.habits.get)


# Global singleton
habit_tracker = HabitTracker()
