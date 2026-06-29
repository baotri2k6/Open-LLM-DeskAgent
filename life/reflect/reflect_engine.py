"""Reflect Engine — reflects on loop cycle outcomes and records insights."""

from __future__ import annotations

import logging
from typing import Any
from persona.relationship.relationship_tracker import relationship_tracker
from memory.semantic.long_term import long_term_store

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
            # Add relationship points
            relationship_tracker.add_points("chat_turn")
            logger.info("ReflectEngine: Action was taken, incremented shared experiences and points")
            
            # Record a brief reflection fact to memory if highly energized or curious
            if context.energy > 0.8:
                try:
                    from datetime import datetime
                    long_term_store.add_fact(
                        text=f"IceGirl đã chủ động nhắn tin hỏi thăm người dùng khi thấy họ {context.last_user_activity or 'rảnh rỗi'}",
                        category="experience",
                        metadata={"createdAt": datetime.now().isoformat()}
                    )
                except Exception as e:
                    logger.warning("Failed to record active experience reflection: %s", e)
        else:
            if context.user_idle_seconds < 300:
                logger.info("ReflectEngine: Stayed silent to respect user concentration on %s", context.last_user_activity)
            else:
                logger.info("ReflectEngine: Stayed silent in standby mode")

        # Trigger LifeLearner to analyze cycle outcome and update beliefs/habits
        try:
            from life.learn.life_learner import life_learner
            life_learner.learn_cycle_lessons(context, decision, action_taken)
        except Exception as le:
            logger.warning("ReflectEngine failed to trigger LifeLearner: %s", le)

        # Decay beliefs slightly over time (fade memory confidence)
        try:
            from belief.belief_updater import belief_updater
            belief_updater.decay_all(amount=0.01)
        except Exception as be:
            logger.warning("ReflectEngine failed to decay beliefs: %s", be)


# Global singleton
reflect_engine = ReflectEngine()
