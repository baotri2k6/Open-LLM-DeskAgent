"""Handles when and how to interrupt the active companion tasks gracefully."""

from __future__ import annotations

import logging
from typing import Any
from social.etiquette.social_rules import social_rules

logger = logging.getLogger("ai-companion.persona.behavior.interruption")


class InterruptionHandler:
    """Handles logic for interrupting active companion tasks when user talks or acts (Barge-in)."""

    def __init__(self) -> None:
        self._interrupted = False
        self._is_speaking = False
        self._is_generating = False

    def set_companion_states(self, is_speaking: bool, is_generating: bool) -> None:
        """Update active states of the companion."""
        self._is_speaking = is_speaking
        self._is_generating = is_generating

    def should_interrupt(
        self,
        user_active: bool,
        idle_time: float,
        current_activity: str = "unknown",
        urgency: str = "normal"
    ) -> bool:
        """Check if user activity or proactive companion intent should trigger companion interruption/etiquette rules."""
        # 1. Direct user interaction barge-in
        if user_active and (self._is_speaking or self._is_generating):
            return True

        # 2. General user activity check
        if user_active and idle_time < 1.0:
            return True

        # 3. Proactive etiquette-based interruption check
        return social_rules.should_interrupt(current_activity, urgency)

    def should_barge_in(self, user_active: bool) -> bool:
        """Determine if user input should trigger immediate companion speech barge-in."""
        return user_active and (self._is_speaking or self._is_generating or self._interrupted)

    def trigger_interruption(self) -> None:
        """Interrupt active operations (Aborts speech playback and text generation)."""
        logger.info("InterruptionHandler: Triggering barge-in/interruption on active generation and speech.")
        self._interrupted = True
        self._is_speaking = False
        self._is_generating = False

        # Set Python generation interrupt flag
        try:
            import api.server
            api.server._generation_interrupted = True
            
            # Broadcast audio stop notification to WS / polling clients
            api.server.ws_broadcast({
                "type": "audio:stop",
                "reason": "interrupted"
            })
        except Exception as e:
            logger.warning("Failed to set generation interruption flag or broadcast audio:stop: %s", e)

    def reset(self) -> None:
        """Reset state."""
        self._interrupted = False


# Global singleton
interruption_handler = InterruptionHandler()
