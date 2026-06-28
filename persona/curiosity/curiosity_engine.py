"""Drives companion curiosity and proactive questions."""

from __future__ import annotations

import logging
import random
from typing import Any, List

logger = logging.getLogger("ai-companion.persona.curiosity")


class CuriosityEngine:
    """Decides what the companion is currently curious about to trigger dialogue."""

    def __init__(self) -> None:
        self._curious_topics = [
            "AI technology", "indie game dev", "Live2D animation",
            "Python programming", "ui design", "desktop companion development"
        ]

    def get_proactive_topic(self, context: Any) -> str:
        """Suggest a topic based on user activity or preferences."""
        activity = context.last_user_activity
        
        # 1. Activity-specific curiosity
        if activity == "coding":
            return random.choice([
                "Hỏi người dùng xem họ đang dùng framework nào để code thế.",
                "Tò mò hỏi về kiến trúc dự án người dùng đang triển khai.",
                "Hỏi xem họ có đang viết unit test cho chức năng mới không."
            ])
        elif activity == "gaming":
            return random.choice([
                "Hỏi người dùng xem tựa game này có gì hay và hấp dẫn.",
                "Tò mò hỏi xem họ chơi game này lâu chưa.",
                "Hỏi xem game này có cốt truyện sâu sắc không."
            ])
            
        # 2. General curiosity fallback
        topic = random.choice(self._curious_topics)
        return f"Chủ động chia sẻ và tò mò hỏi về chủ đề '{topic}'."


# Global singleton
curiosity_engine = CuriosityEngine()
