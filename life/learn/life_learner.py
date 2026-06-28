"""Extracts lessons from each life cycle iteration."""

from __future__ import annotations

import logging
from typing import Any
from belief.user_model import user_model

logger = logging.getLogger("ai-companion.life.learn")


class LifeLearner:
    """Extracts lessons from each life cycle iteration."""

    def __init__(self) -> None:
        pass

    def learn_cycle_lessons(self, context: Any, decision: Any, success: bool) -> None:
        """Learn user habits or task preferences based on cycle outcomes."""
        if not success:
            return
            
        activity = context.last_user_activity
        if activity and activity != "unknown":
            # Learn that the user enjoys or spends time on this activity
            traits = user_model.get_user_traits()
            if activity == "gaming" and "gamer" not in traits:
                user_model.set_preference("favorite_activity", "gaming")
                logger.info("LifeLearner: Learned user favorite activity is gaming")
            elif activity == "coding" and "coder" not in traits:
                user_model.set_preference("favorite_activity", "coding")
                logger.info("LifeLearner: Learned user favorite activity is coding")


# Global singleton
life_learner = LifeLearner()
