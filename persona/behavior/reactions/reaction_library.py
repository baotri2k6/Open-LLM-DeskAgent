"""ReactionLibrary — thư viện vi phản ứng (micro-reactions) cho Live2D avatar.

Các phản ứng nhanh như gật đầu, nghiêng đầu, chớp mắt kép, cười mỉm, dỗi.
Các phản ứng này có thể tự động kích hoạt bởi cảm xúc hoặc kết quả thực thi công cụ.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("ai-companion.persona.behavior.reactions")


@dataclass
class MicroReaction:
    """Định nghĩa một vi phản ứng."""
    name:        str
    motion:      str
    expression:  str
    duration_ms: int = 1000
    description: str = ""


class ReactionLibrary:
    """Quản lý và kích hoạt các vi phản ứng nhanh của companion."""

    REACTIONS = {
        "nod": MicroReaction(
            name="nod",
            motion="react_nod",
            expression="happy",
            duration_ms=800,
            description="Gật đầu đồng ý/hiểu bài"
        ),
        "shake_head": MicroReaction(
            name="shake_head",
            motion="react_shake",
            expression="sad",
            duration_ms=1000,
            description="Lắc đầu không đồng ý hoặc tiếc nuối"
        ),
        "tilt_head": MicroReaction(
            name="tilt_head",
            motion="react_tilt",
            expression="focused",
            duration_ms=1200,
            description="Nghiêng đầu tò mò/thắc mắc"
        ),
        "blink_double": MicroReaction(
            name="blink_double",
            motion="react_blink_twice",
            expression="surprised",
            duration_ms=600,
            description="Chớp mắt ngạc nhiên"
        ),
        "giggle": MicroReaction(
            name="giggle",
            motion="react_giggle",
            expression="excited",
            duration_ms=1500,
            description="Cười khúc khích"
        ),
        "pout": MicroReaction(
            name="pout",
            motion="react_pout",
            expression="angry",
            duration_ms=1200,
            description="Dỗi/phồng má giận dỗi"
        ),
        "sigh": MicroReaction(
            name="sigh",
            motion="react_sigh",
            expression="tired",
            duration_ms=1800,
            description="Thở dài ngán ngẩm/mệt mỏi"
        )
    }

    def __init__(self) -> None:
        self._send_command: Optional[Callable] = None

    def set_send_callback(self, callback: Callable) -> None:
        """Đăng ký callback gửi command đến WebSocket client."""
        self._send_command = callback

    def trigger(self, reaction_name: str) -> bool:
        """Kích hoạt một phản ứng nhanh bằng tên.

        Returns:
            True nếu phản ứng tồn tại và đã kích hoạt.
        """
        reaction = self.REACTIONS.get(reaction_name)
        if not reaction:
            logger.warning("Micro-reaction not found in library: %s", reaction_name)
            return False

        command = {
            "type": "reaction",
            "name": reaction.name,
            "motion": reaction.motion,
            "expression": reaction.expression,
            "duration_ms": reaction.duration_ms,
            "source": "reaction_library"
        }

        logger.info("Micro-reaction triggered: %s (%s)", reaction.name, reaction.description)
        self._dispatch(command)
        return True

    def trigger_random_positive(self) -> str:
        """Trigger một phản ứng tích cực ngẫu nhiên (nod, giggle, smile)."""
        positives = ["nod", "giggle"]
        chosen = random.choice(positives)
        self.trigger(chosen)
        return chosen

    def trigger_random_negative(self) -> str:
        """Trigger một phản ứng tiêu cực/phân vân ngẫu nhiên (shake_head, tilt_head, pout, sigh)."""
        negatives = ["shake_head", "tilt_head", "pout", "sigh"]
        chosen = random.choice(negatives)
        self.trigger(chosen)
        return chosen

    def _dispatch(self, command: dict) -> None:
        if self._send_command:
            try:
                self._send_command(command)
            except Exception as e:
                logger.debug("Reaction dispatch error: %s", e)


# Global singleton
reaction_library = ReactionLibrary()
