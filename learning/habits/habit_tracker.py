"""Detects and stores user behavioral patterns with time-of-day correlations and belief updates."""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger("ai-companion.learning.habits")


class HabitTracker:
    """Detects and stores user behavioral patterns.
    
    Tracks pattern transition counts, time-of-day correlations, and
    automatically reinforces user model preferences when thresholds are met.
    """

    def __init__(self, threshold: int = 5) -> None:
        self.patterns: Dict[str, int] = {}
        self.transitions: Dict[Tuple[str, str], int] = {}
        self.hourly_logs: Dict[str, List[int]] = {}  # activity -> list of hours recorded
        self.threshold = threshold
        self._last_activity: Optional[str] = None

    def track_pattern(self, pattern: str) -> None:
        """Track user activity pattern, including time-of-day and transitions."""
        # 1. Update frequency count
        self.patterns[pattern] = self.patterns.get(pattern, 0) + 1
        logger.info("HabitTracker (Learning): Pattern tracked: %s (count=%d)", pattern, self.patterns[pattern])

        # 2. Track transition from last activity
        if self._last_activity and self._last_activity != pattern:
            transition = (self._last_activity, pattern)
            self.transitions[transition] = self.transitions.get(transition, 0) + 1
            logger.info("HabitTracker (Learning): Transition detected: %s -> %s", self._last_activity, pattern)
        
        self._last_activity = pattern

        # 3. Track hourly correlation (time of day)
        hour = time.localtime().tm_hour
        if pattern not in self.hourly_logs:
            self.hourly_logs[pattern] = []
        self.hourly_logs[pattern].append(hour)

        # 4. Auto-reinforce belief if threshold is exceeded
        self._check_and_reinforce_habits(pattern)

    def _check_and_reinforce_habits(self, pattern: str) -> None:
        """Auto-reinforce beliefs and user preferences based on habit counts."""
        count = self.patterns[pattern]
        if count >= self.threshold:
            # We have a strong habit pattern! Reinforce the belief
            try:
                from belief.belief_updater import belief_updater
                belief_updater.register_evidence(
                    key=f"user.habit.{pattern}",
                    value="established",
                    confidence=min(1.0, 0.5 + (count * 0.05)),
                    source="habit_tracker"
                )
            except Exception as e:
                logger.warning("HabitTracker failed to auto-update belief: %s", e)

    def get_time_of_day_preference(self, activity: str) -> str:
        """Classify time of day preference for an activity (e.g. morning, afternoon, night)."""
        hours = self.hourly_logs.get(activity, [])
        if not hours:
            return "unknown"
            
        morning_count = sum(1 for h in hours if 5 <= h < 12)
        afternoon_count = sum(1 for h in hours if 12 <= h < 18)
        evening_count = sum(1 for h in hours if 18 <= h < 24 or 0 <= h < 5)
        
        counts = {
            "morning": morning_count,
            "afternoon": afternoon_count,
            "evening/night": evening_count
        }
        return max(counts, key=counts.get)

    def get_top_transitions(self, limit: int = 3) -> List[Tuple[Tuple[str, str], int]]:
        """Get the most frequent activity transition sequences."""
        sorted_trans = sorted(self.transitions.items(), key=lambda item: item[1], reverse=True)
        return sorted_trans[:limit]


# Global singleton
habit_tracker = HabitTracker()
