"""Registry of Live2D facial expressions."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.persona.expressions")


class ExpressionRegistry:
    """Registry of Live2D facial expressions."""

    def __init__(self) -> None:
        # Default expression maps
        self.expressions = {
            "vui vẻ": "exp_happy",
            "buồn": "exp_sad",
            "hơi dỗi": "exp_angry",
            "suy nghĩ": "exp_thinking",
            "neutral": "exp_default"
        }

    def get_expression(self, emotion: str) -> str:
        return self.expressions.get(emotion.lower(), "exp_default")


# Global singleton
expression_registry = ExpressionRegistry()
