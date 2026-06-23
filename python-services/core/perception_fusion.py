"""PerceptionFusion — Module gom tất cả các tín hiệu đầu vào của AI Companion thành một ContextPacket thống nhất."""
from __future__ import annotations
from datetime import datetime
import time

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

        # Trả về ContextPacket dưới dạng cấu trúc dictionary
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "idle_time_seconds": idle_time_seconds,
            "user_message": user_message or "",
            "screen_text": screen_text or "",
            "activity": activity or "unknown"
        }
