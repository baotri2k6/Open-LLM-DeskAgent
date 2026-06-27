"""CompanionNeeds — hệ thống nhu cầu nội tại của companion.

Lấy cảm hứng từ Maslow's hierarchy nhưng adapted cho AI companion.
Các nhu cầu này ảnh hưởng đến behavior khi không có user input.

Hierarchy (từ cơ bản đến cao cấp):
  1. Connection    — cần tương tác với user
  2. Stimulation   — cần thông tin mới, học hỏi
  3. Expression    — cần thể hiện cảm xúc / ý kiến
  4. Purpose       — cần hoàn thành mục tiêu có ý nghĩa
  5. Growth        — cần phát triển kỹ năng và hiểu biết
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

logger = logging.getLogger("ai-companion.motivation.needs")


@dataclass
class Need:
    """Một nhu cầu cụ thể của companion."""
    name:        str
    level:       float    = 0.5    # Mức độ hiện tại 0.0 (đói) → 1.0 (no)
    decay_rate:  float    = 0.01   # Giảm bao nhiêu mỗi phút khi không được đáp ứng
    priority:    int      = 1      # 1 = cao nhất
    description: str      = ""

    def is_urgent(self) -> bool:
        """Nhu cầu đang ở mức cần thiết phải đáp ứng."""
        return self.level < 0.3

    def is_satisfied(self) -> bool:
        return self.level > 0.7

    def satisfy(self, amount: float = 0.3) -> None:
        """Đáp ứng nhu cầu — tăng level."""
        self.level = min(1.0, self.level + amount)

    def decay(self, minutes: float) -> None:
        """Giảm level theo thời gian (gọi mỗi life cycle)."""
        self.level = max(0.0, self.level - self.decay_rate * minutes)


class CompanionNeeds:
    """Quản lý toàn bộ hệ thống nhu cầu của companion.

    Được gọi bởi LifeLoop và MotivationManager để xác định
    companion cần gì nhất vào thời điểm hiện tại.
    """

    def __init__(self) -> None:
        self._needs: dict[str, Need] = {
            "connection": Need(
                name="connection",
                level=0.8,
                decay_rate=0.015,   # Giảm nhanh khi không nói chuyện
                priority=1,
                description="Cần tương tác và kết nối với user",
            ),
            "stimulation": Need(
                name="stimulation",
                level=0.6,
                decay_rate=0.008,
                priority=2,
                description="Cần thông tin mới và trải nghiệm thú vị",
            ),
            "expression": Need(
                name="expression",
                level=0.5,
                decay_rate=0.005,
                priority=3,
                description="Cần thể hiện cảm xúc và ý kiến của mình",
            ),
            "purpose": Need(
                name="purpose",
                level=0.7,
                decay_rate=0.003,
                priority=4,
                description="Cần hoàn thành việc gì đó có ý nghĩa",
            ),
            "growth": Need(
                name="growth",
                level=0.4,
                decay_rate=0.002,
                priority=5,
                description="Cần học hỏi và phát triển",
            ),
        }
        self._last_decay_time: float = time.time()

    def tick(self) -> None:
        """Gọi định kỳ để decay các nhu cầu theo thời gian."""
        now = time.time()
        elapsed_minutes = (now - self._last_decay_time) / 60.0
        for need in self._needs.values():
            need.decay(elapsed_minutes)
        self._last_decay_time = now

    def satisfy(self, need_name: str, amount: float = 0.3) -> None:
        """Đáp ứng một nhu cầu cụ thể."""
        if need_name in self._needs:
            self._needs[need_name].satisfy(amount)
            logger.debug("Need satisfied: %s → %.2f", need_name, self._needs[need_name].level)

    def on_conversation(self) -> None:
        """Gọi khi có cuộc trò chuyện với user."""
        self.satisfy("connection", 0.4)
        self.satisfy("expression", 0.2)

    def on_task_completed(self) -> None:
        """Gọi khi hoàn thành một task."""
        self.satisfy("purpose", 0.5)
        self.satisfy("stimulation", 0.2)

    def on_learned_something(self) -> None:
        """Gọi khi học được điều mới."""
        self.satisfy("growth", 0.4)
        self.satisfy("stimulation", 0.3)

    def get_most_urgent(self) -> Need | None:
        """Trả về nhu cầu cấp bách nhất (level thấp nhất, priority cao nhất)."""
        urgent = [n for n in self._needs.values() if n.is_urgent()]
        if not urgent:
            return None
        return min(urgent, key=lambda n: (n.priority, n.level))

    def get_summary(self) -> dict:
        """Snapshot các nhu cầu hiện tại."""
        return {
            name: {"level": round(need.level, 2), "urgent": need.is_urgent()}
            for name, need in self._needs.items()
        }

    def overall_wellbeing(self) -> float:
        """Trung bình mức độ hài lòng tổng thể (0→1)."""
        return sum(n.level for n in self._needs.values()) / len(self._needs)


# Global singleton
companion_needs = CompanionNeeds()
