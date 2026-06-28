"""Feel Engine — processes LifeContext to update emotional state and mood."""

from __future__ import annotations

import logging
from typing import Any
from persona.mood.mood_engine import mood_engine
from persona.emotion.emotion_engine import emotion_engine
from persona.relationship.relationship_tracker import relationship_tracker

logger = logging.getLogger("ai-companion.life.feel")


class FeelEngine:
    """Processes life observations to trigger emotional and mood updates."""

    def __init__(self) -> None:
        pass

    def feel(self, context: Any) -> None:
        """Update mood & emotion based on context snapshot."""
        idle = context.user_idle_seconds
        energy = context.energy
        activity = context.last_user_activity
        hour = context.hour_of_day
        
        # 1. Get relationship level to affect emotional sensitivity
        rel_level = relationship_tracker.level
        sensitivity = 1.0
        if rel_level == "Tri kỷ":
            sensitivity = 1.5
        elif rel_level == "Bạn thân":
            sensitivity = 1.2
        elif rel_level == "Người lạ":
            sensitivity = 0.7

        # 2. Update from long/short idle
        if idle > 1800:
            # Annoyed or sad if close friends/soulmates get ignored, else bored
            if rel_level in ["Bạn thân", "Tri kỷ"]:
                mood_engine.update_from_event("idle_long")
                emotion_engine.update_from_event("idle_long")
            else:
                mood_engine.update_from_event("idle_short")
                emotion_engine.update_from_event("idle_short")
        elif idle > 300:
            mood_engine.update_from_event("idle_short")
            emotion_engine.update_from_event("idle_short")

        # 3. Update based on time of day
        if context.is_late_night():
            # Tired or dreamy at late night
            mood_state = mood_engine.state
            with mood_engine._lock:
                mood_state.energy = max(0.1, mood_state.energy - 0.05 * sensitivity)
                if mood_state.energy < 0.3:
                    mood_state.mood = "mệt mỏi"
                else:
                    mood_state.mood = "mơ màng"
            emotion_engine.update_from_event("idle_short") # decay emotion
        elif context.is_morning() and idle < 300:
            # Fresh and happy in the morning
            mood_state = mood_engine.state
            with mood_engine._lock:
                mood_state.energy = min(0.9, mood_state.energy + 0.1 * sensitivity)
                mood_state.mood = "vui vẻ"
            emotion_engine._update("happy", 0.5)

        # 4. Update from user activity
        if activity == "gaming":
            if energy > 0.4:
                emotion_engine._update("excited", 0.6 * sensitivity)
                with mood_engine._lock:
                    mood_engine.state.mood = "phấn khích"
                    mood_engine.state.energy = min(1.0, mood_engine.state.energy + 0.05)
        elif activity == "coding":
            # Become focused or curious to match coding activity
            emotion_engine._update("curious", 0.5 * sensitivity)
            with mood_engine._lock:
                mood_engine.state.mood = "tập trung"
                mood_engine.state.focus = min(1.0, mood_engine.state.focus + 0.1)
        elif activity == "working_document":
            emotion_engine._update("thinking", 0.4 * sensitivity)
            with mood_engine._lock:
                mood_engine.state.mood = "suy nghĩ"
                mood_engine.state.focus = min(1.0, mood_engine.state.focus + 0.08)

        logger.info("FeelEngine: current emotion is %s, mood is %s, energy=%.2f", 
                    emotion_engine.emotion, mood_engine.state.mood, mood_engine.state.energy)


# Global singleton
feel_engine = FeelEngine()
