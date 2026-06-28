"""Registry of Live2D body motions."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.persona.motions")


class MotionRegistry:
    """Registry of Live2D body motions."""

    def __init__(self) -> None:
        self.motions = {
            "happy": "motion_cheer",
            "sad": "motion_sigh",
            "angry": "motion_pout",
            "default": "motion_idle"
        }

    def get_motion(self, emotion: str) -> str:
        return self.motions.get(emotion.lower(), "motion_idle")


# Global singleton
motion_registry = MotionRegistry()
