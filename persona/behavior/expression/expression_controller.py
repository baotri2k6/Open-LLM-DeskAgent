"""ExpressionController — map emotion state thành Live2D parameters.

Bridge giữa EmotionEngine (abstract) và Live2D renderer (concrete parameters).
Companion cần 'mặt' phản ánh cảm xúc thực sự.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("ai-companion.persona.behavior.expression")


# Mapping emotion → Live2D expression parameters
EMOTION_EXPRESSION_MAP: dict[str, dict[str, Any]] = {
    "vui vẻ": {
        "expression": "happy",
        "param_EyeOpen": 1.0,
        "param_MouthForm": 0.8,
        "param_BrowY": 0.3,
        "param_CheekFlush": 0.4,
    },
    "phấn khích": {
        "expression": "excited",
        "param_EyeOpen": 1.2,
        "param_MouthForm": 1.0,
        "param_BrowY": 0.5,
        "param_CheekFlush": 0.7,
    },
    "buồn": {
        "expression": "sad",
        "param_EyeOpen": 0.6,
        "param_MouthForm": -0.5,
        "param_BrowY": -0.3,
        "param_CheekFlush": 0.0,
    },
    "tức giận": {
        "expression": "angry",
        "param_EyeOpen": 0.8,
        "param_MouthForm": -0.2,
        "param_BrowY": -0.7,
        "param_BrowAngle": -0.5,
    },
    "ngạc nhiên": {
        "expression": "surprised",
        "param_EyeOpen": 1.5,
        "param_MouthForm": 0.3,
        "param_BrowY": 0.8,
    },
    "tập trung": {
        "expression": "focused",
        "param_EyeOpen": 0.9,
        "param_MouthForm": 0.0,
        "param_BrowY": -0.1,
    },
    "mệt": {
        "expression": "tired",
        "param_EyeOpen": 0.4,
        "param_MouthForm": -0.1,
        "param_BrowY": -0.1,
    },
    "neutral": {
        "expression": "neutral",
        "param_EyeOpen": 0.8,
        "param_MouthForm": 0.1,
        "param_BrowY": 0.0,
    },
}

# Aliases
EMOTION_ALIASES: dict[str, str] = {
    "happy":     "vui vẻ",
    "excited":   "phấn khích",
    "sad":       "buồn",
    "angry":     "tức giận",
    "surprised": "ngạc nhiên",
    "focused":   "tập trung",
    "tired":     "mệt",
    "frustrated": "tức giận",  # frustrated → angry expression
    "anxious":   "tập trung",
}


class ExpressionController:
    """Controls Live2D expression parameters based on companion emotion state.

    Subscribes to EmotionEngine state changes and pushes parameter
    updates to the renderer via WebSocket callback.
    """

    def __init__(self) -> None:
        self._send_callback: Optional[Callable] = None
        self._current_expression: str = "neutral"

    def set_send_callback(self, callback: Callable) -> None:
        """Set WebSocket send callback."""
        self._send_callback = callback

    def apply_emotion(self, emotion: str, intensity: float = 0.7) -> dict:
        """Convert emotion string to Live2D parameters and send.

        Args:
            emotion: Emotion label từ EmotionEngine.
            intensity: Cường độ cảm xúc (0.0 → 1.0).

        Returns:
            Parameter dict đã gửi.
        """
        # Resolve alias
        resolved = EMOTION_ALIASES.get(emotion, emotion)
        params = EMOTION_EXPRESSION_MAP.get(resolved, EMOTION_EXPRESSION_MAP["neutral"]).copy()

        # Scale parameters by intensity
        for key, val in params.items():
            if key.startswith("param_") and isinstance(val, float):
                params[key] = val * intensity

        params["intensity"] = intensity
        self._current_expression = params.get("expression", "neutral")

        command = {
            "type":       "expression",
            "expression": self._current_expression,
            "params":     params,
            "source":     "expression_controller",
        }

        self._dispatch(command)
        logger.debug("Expression: %s (intensity=%.2f)", self._current_expression, intensity)
        return params

    def blend_transition(self, from_emotion: str, to_emotion: str,
                         steps: int = 5, duration: float = 0.5) -> None:
        """Schedule a smooth blend transition between two expressions.

        Creates asyncio task for async rendering (fire-and-forget).
        """
        import asyncio

        async def _blend():
            import asyncio as _asyncio
            step_time = duration / steps
            from_params = EMOTION_EXPRESSION_MAP.get(
                EMOTION_ALIASES.get(from_emotion, from_emotion),
                EMOTION_EXPRESSION_MAP["neutral"]
            )
            to_params = EMOTION_EXPRESSION_MAP.get(
                EMOTION_ALIASES.get(to_emotion, to_emotion),
                EMOTION_EXPRESSION_MAP["neutral"]
            )

            for i in range(steps + 1):
                t = i / steps
                blended = {}
                for key in set(from_params) | set(to_params):
                    a = from_params.get(key, 0)
                    b = to_params.get(key, 0)
                    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                        blended[key] = a + (b - a) * t
                    else:
                        blended[key] = b if t > 0.5 else a
                self._dispatch({"type": "expression_blend", "params": blended, "t": t})
                await _asyncio.sleep(step_time)

        try:
            asyncio.create_task(_blend())
        except RuntimeError:
            pass  # No event loop — silent fail

    def _dispatch(self, command: dict) -> None:
        """Send command via callback if available."""
        if self._send_callback:
            try:
                self._send_callback(command)
            except Exception as e:
                logger.debug("Expression dispatch error: %s", e)

    @property
    def current_expression(self) -> str:
        return self._current_expression


# Global singleton
expression_controller = ExpressionController()
