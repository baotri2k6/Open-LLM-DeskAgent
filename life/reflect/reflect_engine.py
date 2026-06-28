"""Reflect Engine — reflects on loop cycle outcomes and records insights."""

from __future__ import annotations

import logging
from typing import Any
from persona.relationship.relationship_tracker import relationship_tracker

logger = logging.getLogger("ai-companion.life.reflect")


class ReflectEngine:
    """Performs post-cycle reflection to adjust companion goals and beliefs."""

    def __init__(self) -> None:
        pass

    def reflect_cycle(self, context: Any, decision: Any, action_taken: bool) -> None:
        """Reflect on the decision made and action outcome."""
        if action_taken:
            # Increments shared experiences
            relationship_tracker.add_shared_experience()
            logger.info("ReflectEngine: Action was taken, incremented shared experiences")
        else:
            if context.user_idle_seconds < 300:
                logger.info("ReflectEngine: Stayed silent to respect user concentration")
            else:
                logger.info("ReflectEngine: Stayed silent in standby mode")


# Global singleton
reflect_engine = ReflectEngine()
