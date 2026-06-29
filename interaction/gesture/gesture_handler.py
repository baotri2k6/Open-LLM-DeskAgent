"""Gesture and touch interaction adapter (future)."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.interaction.gesture")


class GestureHandler:
    """Processes user clicks or touch coordinates on the companion avatar to trigger gestures."""

    def __init__(self) -> None:
        pass

    def handle_tap(self, area: str) -> dict:
        """Process avatar tap event (e.g., head, body, face) and return reaction details.
        
        Args:
            area: Patched area tapped by the user ('head', 'body', 'face', 'hand').
            
        Returns:
            Dict containing recommended emotion and motion to emit to Electron renderer.
        """
        logger.info("GestureHandler: Received tap on area '%s'", area)
        
        if area == "head":
            return {
                "emotion": "smile",
                "motion": "nod",
                "speech_hint": "Cảm ơn bạn đã xoa đầu tớ nhé!"
            }
        elif area == "face":
            return {
                "emotion": "blush",
                "motion": "head_shake",
                "speech_hint": "Nhột quá à nha!"
            }
        elif area == "body":
            return {
                "emotion": "surprised",
                "motion": "backstep",
                "speech_hint": "Này, đừng chọc ghẹo tớ chứ!"
            }
        
        return {
            "emotion": "neutral",
            "motion": "idle",
            "speech_hint": ""
        }


# Global singleton
gesture_handler = GestureHandler()
