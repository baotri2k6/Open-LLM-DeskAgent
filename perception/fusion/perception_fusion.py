"""PerceptionFusion — Module gom tất cả các tín hiệu đầu vào của AI Companion thành một ContextPacket thống nhất."""

from __future__ import annotations

import logging
import time
from tools.screen_reader import ocr_screenshot
from runtime.context.context_packet import ContextPacket

logger = logging.getLogger("ai-companion.perception.fusion")


class PerceptionFusion:
    @staticmethod
    def fuse(
        user_message: str | None = None,
        screen_text: str | None = None,
        last_interaction_time: float | None = None,
        activity: str | None = None
    ) -> ContextPacket:
        """Gom tất cả các tín hiệu (Văn bản, OCR màn hình, thời gian idle) thành một ContextPacket."""
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

        # Trả về ContextPacket dataclass instance
        return ContextPacket(
            user_message=user_message or "",
            ocr_text=screen_text or "",
            idle_seconds=idle_time_seconds,
            activity=activity or "unknown"
        )
