"""Extracts lessons from each life cycle iteration, learning habits, traits and preferences dynamically."""

from __future__ import annotations

import logging
from typing import Any
from belief.user_model import user_model
from belief.belief_updater import belief_updater

logger = logging.getLogger("ai-companion.life.learn")


class LifeLearner:
    """Extracts lessons from each life cycle iteration, learning habits, traits and preferences dynamically."""

    def __init__(self) -> None:
        self._activity_counters: dict[str, int] = {}

    def learn_cycle_lessons(self, context: Any, decision: Any, success: bool) -> None:
        """Learn user habits or task preferences based on cycle outcomes."""
        if not success:
            return
            
        # 1. Learn from user activity
        activity = getattr(context, "last_user_activity", None)
        if not activity:
            # Fallback check dict
            if isinstance(context, dict):
                activity = context.get("activity")
                
        if activity and activity != "unknown":
            self._activity_counters[activity] = self._activity_counters.get(activity, 0) + 1
            count = self._activity_counters[activity]
            
            # If we observe this activity at least 3 times, promote to a strong preference/habit
            if count >= 3:
                user_model.set_preference("favorite_activity", activity)
                belief_updater.register_evidence(f"user.habit.{activity}", "active", confidence=0.8, source="observation")
                logger.info("LifeLearner: Promoted '%s' to favorite activity (observed %d times)", activity, count)

        # 2. Learn from user text in context packet if available
        user_msg = getattr(context, "user_message", None)
        if not user_msg:
            if isinstance(context, dict):
                user_msg = context.get("user_message")
                
        if user_msg:
            # Dynamically learn preferences mentioned by the user
            from learning.knowledge.knowledge_extractor import knowledge_extractor
            extracted = knowledge_extractor.extract_from_text(user_msg)
            for k, v in extracted.items():
                logger.info("LifeLearner: Learnt fact from user message: %s = %s", k, v)


# Global singleton
life_learner = LifeLearner()
