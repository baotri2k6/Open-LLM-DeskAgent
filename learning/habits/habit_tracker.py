"""Detects and stores user behavioral patterns."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.learning.habits")


class HabitTracker:
    """Detects and stores user behavioral patterns."""

    def __init__(self) -> None:
        self.patterns: dict[str, int] = {}

    def track_pattern(self, pattern: str) -> None:
        self.patterns[pattern] = self.patterns.get(pattern, 0) + 1
        logger.info("HabitTracker (Learning): Pattern tracked: %s", pattern)


# Global singleton
habit_tracker = HabitTracker()
