"""Feel Engine — processes LifeContext to update emotional state and mood."""

from __future__ import annotations

import logging
from typing import Any
from persona.mood.mood_engine import mood_engine
from persona.emotion.emotion_engine import emotion_engine

logger = logging.getLogger("ai-companion.life.feel")


class FeelEngine:
    """Processes life observations to trigger emotional and mood updates."""

    def __init__(self) -> None:
        pass

    def feel(self, context: Any) -> None:
        """Update mood & emotion based on context snapshot."""
        idle = context.user_idle_seconds
        energy = context.energy
        
        # 1. Update from long/short idle
        if idle > 1800:
            mood_engine.update_from_event("idle_long")
            emotion_engine.update_from_event("idle_long")
        elif idle > 300:
            mood_engine.update_from_event("idle_short")
            emotion_engine.update_from_event("idle_short")
        
        # 2. Update from user activity
        if context.last_user_activity == "gaming" and energy > 0.4:
            emotion_engine.update_from_event("user_gaming")
            mood_engine.update_from_event("user_gaming")
            
        logger.info("FeelEngine: current emotion is %s, mood is %s", emotion_engine.emotion, mood_engine.state.mood)


# Global singleton
feel_engine = FeelEngine()
