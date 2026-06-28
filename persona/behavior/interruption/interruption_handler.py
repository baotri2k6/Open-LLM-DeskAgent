"""Handles when and how to interrupt the user gracefully."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.persona.behavior.interruption")


class InterruptionHandler:
    """Handles logic for interrupting active companion tasks when user talks or acts."""

    def __init__(self) -> None:
        self._interrupted = False

    def should_interrupt(self, user_active: bool, idle_time: float) -> bool:
        """Check if user activity should trigger companion speech interruption."""
        # If user starts typing or talking while companion is active
        if user_active and idle_time < 1.0:
            return True
        return False

    def trigger_interruption(self) -> None:
        """Interrupt active operations."""
        logger.info("InterruptionHandler: Interrupting active generation/speech.")
        self._interrupted = True

        try:
            import api.server
            api.server._generation_interrupted = True
        except Exception as e:
            logger.warning("Failed to set generation interruption flag: %s", e)

    def reset(self) -> None:
        """Reset state."""
        self._interrupted = False


# Global singleton
interruption_handler = InterruptionHandler()
