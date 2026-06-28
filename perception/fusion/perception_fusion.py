"""PerceptionFusion — Module gom tất cả các tín hiệu đầu vào của AI Companion thành một ContextPacket thống nhất."""

from __future__ import annotations

import logging
from datetime import datetime
import time
from tools.screen_reader import ocr_screenshot

logger = logging.getLogger("ai-companion.perception.fusion")


class PerceptionFusion:
    @staticmethod
    def fuse(
        user_message: str | None = None,
        screen_text: str | None = None,
        last_interaction_time: float | None = None,
        activity: str | None = None
    ) -> dict:
        """Gom tất cả các tín hiệu (Văn bản, OCR màn hình, thời gian idle) thành ContextPacket."""
        now = time.time()
        idle_time_seconds = 0.0
        if last_interaction_time:
            idle_time_seconds = now - last_interaction_time

        # Nếu không truyền screen_text, tự động chụp màn hình và ocr
        if not screen_text:
            try:
                res = ocr_screenshot()
                if res.get("success"):
                    screen_text = res.get("text", "")
            except Exception as e:
                logger.warning("Failed to auto-OCR screen during fusion: %s", e)

        # Trả về ContextPacket dưới dạng cấu trúc dictionary
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "idle_time_seconds": idle_time_seconds,
            "user_message": user_message or "",
            "screen_text": screen_text or "",
            "activity": activity or "unknown"
        }
