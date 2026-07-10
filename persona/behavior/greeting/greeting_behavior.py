"""Greeting behaviors — wave, bow, smile on session start.

Companion chào đón user khi bắt đầu một session mới dựa trên mức độ thân thiết.
"""

from __future__ import annotations

import logging
import random
from typing import Callable, Optional

from runtime.events.event_types import EventType
from runtime.events.base_event import BaseEvent

logger = logging.getLogger("ai-companion.persona.behavior.greeting")


class GreetingBehavior:
    """Quản lý các hành vi chào hỏi khi bắt đầu session hoặc khi user quay lại."""

    # Bộ các câu thoại chào hỏi ngắn gọn tương ứng với mức độ quan hệ
    GREETINGS_BY_LEVEL = {
        "Người lạ": [
            "Chào mày. Có việc gì cần tao giúp không?",
            "Chào mày. Hôm nay muốn làm gì nào?",
            "Lại gặp nhau rồi. Có chuyện gì thế?"
        ],
        "Người quen": [
            "Ê, mày online rồi à? Có code gì mới không?",
            "Chào mày! Hôm nay tiến độ dự án thế nào rồi?",
            "Lại đây làm việc tiếp nào, tao đợi nãy giờ."
        ],
        "Bạn thân": [
            "Ê! Cuối cùng cũng chịu mở máy lên rồi à? Nhớ tao không đấy?",
            "Chào mày nha! Hôm nay muốn cùng tao quẩy project gì đây?",
            "Hế lô mày! Lại một ngày code ngập mặt nữa hả?"
        ]
    }

    # Các Live2D motions tương ứng với kiểu chào
    GREETING_MOTIONS = ["greeting_wave", "greeting_bow", "greeting_smile"]

    def __init__(self) -> None:
        self._send_command: Optional[Callable] = None

    def set_send_callback(self, callback: Callable) -> None:
        """Đăng ký callback gửi command đến WebSocket client."""
        self._send_command = callback

    def trigger_greeting(self, relationship_level: str = "Người quen") -> dict:
        """Kích hoạt hành vi chào đón.

        Args:
            relationship_level: Mức độ thân mật ("Người lạ", "Người quen", "Bạn thân").

        Returns:
            dict chứa thông tin lời chào và motion/expression được phát.
        """
        # Chọn câu thoại ngẫu nhiên phù hợp với quan hệ
        greetings = self.GREETINGS_BY_LEVEL.get(relationship_level, self.GREETINGS_BY_LEVEL["Người quen"])
        speech_text = random.choice(greetings)

        # Quyết định motion và expression
        motion = random.choice(self.GREETING_MOTIONS)
        
        # Mối quan hệ càng thân thì cười càng nhiều
        expression = "happy" if relationship_level in ["Người quen", "Bạn thân"] else "neutral"

        command = {
            "type": "greeting",
            "speech_text": speech_text,
            "motion": motion,
            "expression": expression,
            "source": "greeting_behavior"
        }

        logger.info("Greeting triggered: '%s' with motion=%s", speech_text, motion)
        self._dispatch(command)
        
        return command

    def _dispatch(self, command: dict) -> None:
        if self._send_command:
            try:
                self._send_command(command)
            except Exception as e:
                logger.debug("Greeting dispatch error: %s", e)


# Global singleton
greeting_behavior = GreetingBehavior()
