"""BoredomDetector — phát hiện khi companion đang nhàm chán.

Khi user idle quá lâu mà companion không làm gì,
BoredomDetector tăng dần boredom level và trigger proactive behavior.

Đây là engine đằng sau "Đôi khi sự hiện diện mà không làm phiền còn có
giá trị hơn bất kỳ câu trả lời nào" — Silence Engine sẽ quyết định
có nên nói không, nhưng BoredomDetector là cái nhận ra rằng đã đủ lâu.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("ai-companion.motivation.boredom")


@dataclass
class BoredomState:
    """Trạng thái nhàm chán hiện tại."""
    level:          float   # 0.0 (không chán) → 1.0 (chán cực độ)
    idle_minutes:   float   # Số phút idle
    triggers:       int     # Số lần đã trigger proactive behavior


class BoredomDetector:
    """Phát hiện và quản lý trạng thái nhàm chán của companion.

    Level tăng dần theo thời gian idle.
    Khi vượt ngưỡng, emit BoredomTriggered event để Life Loop xử lý.
    Sau khi trigger, giảm level (không spam user).
    """

    # Các ngưỡng boredom (phút idle)
    MILD_THRESHOLD      = 5.0    # Hơi buồn
    MODERATE_THRESHOLD  = 15.0   # Muốn nói chuyện
    STRONG_THRESHOLD    = 30.0   # Rõ ràng nhàm chán
    INTENSE_THRESHOLD   = 60.0   # Rất cần tương tác

    # Cooldown sau khi trigger (phút) — tránh spam
    TRIGGER_COOLDOWN = 10.0

    def __init__(self) -> None:
        self._idle_start: float | None = None      # Khi nào bắt đầu idle
        self._last_trigger_time: float = 0.0       # Khi nào trigger cuối
        self._trigger_count: int = 0
        self._boredom_level: float = 0.0
        self._last_activity: float = time.time()

    def on_activity(self) -> None:
        """Gọi khi có hoạt động (user nói, conversation, task...).
        Reset boredom về 0.
        """
        self._last_activity = time.time()
        self._idle_start = None
        self._boredom_level = 0.0
        logger.debug("Boredom reset — activity detected")

    def tick(self) -> BoredomState:
        """Gọi mỗi life cycle để update boredom level.

        Returns:
            BoredomState hiện tại.
        """
        now = time.time()
        idle_seconds = now - self._last_activity
        idle_minutes = idle_seconds / 60.0

        # Tính boredom level dựa trên idle time (logarithmic)
        if idle_minutes < 1.0:
            self._boredom_level = 0.0
        elif idle_minutes < self.MILD_THRESHOLD:
            self._boredom_level = 0.1 * (idle_minutes / self.MILD_THRESHOLD)
        elif idle_minutes < self.MODERATE_THRESHOLD:
            self._boredom_level = 0.1 + 0.3 * ((idle_minutes - self.MILD_THRESHOLD) / (self.MODERATE_THRESHOLD - self.MILD_THRESHOLD))
        elif idle_minutes < self.STRONG_THRESHOLD:
            self._boredom_level = 0.4 + 0.3 * ((idle_minutes - self.MODERATE_THRESHOLD) / (self.STRONG_THRESHOLD - self.MODERATE_THRESHOLD))
        elif idle_minutes < self.INTENSE_THRESHOLD:
            self._boredom_level = 0.7 + 0.2 * ((idle_minutes - self.STRONG_THRESHOLD) / (self.INTENSE_THRESHOLD - self.STRONG_THRESHOLD))
        else:
            self._boredom_level = min(1.0, 0.9 + 0.1 * (idle_minutes / self.INTENSE_THRESHOLD))

        return BoredomState(
            level=self._boredom_level,
            idle_minutes=idle_minutes,
            triggers=self._trigger_count,
        )

    def should_trigger(self) -> bool:
        """Có nên trigger proactive behavior không?

        True khi:
        - Boredom level > 0.4 (moderate threshold)
        - Đã qua cooldown kể từ lần trigger cuối
        """
        now = time.time()
        cooldown_passed = (now - self._last_trigger_time) > (self.TRIGGER_COOLDOWN * 60)

        if self._boredom_level >= 0.4 and cooldown_passed:
            return True
        return False

    def mark_triggered(self) -> None:
        """Đánh dấu đã trigger — reset cooldown, giảm boredom."""
        self._last_trigger_time = time.time()
        self._trigger_count += 1
        self._boredom_level = max(0.0, self._boredom_level - 0.3)
        logger.info("Boredom triggered (count=%d)", self._trigger_count)

    def get_intensity_label(self) -> str:
        """Nhãn dễ đọc cho mức độ nhàm chán."""
        if self._boredom_level < 0.2:   return "none"
        if self._boredom_level < 0.4:   return "mild"
        if self._boredom_level < 0.6:   return "moderate"
        if self._boredom_level < 0.8:   return "strong"
        return "intense"


# Global singleton
boredom_detector = BoredomDetector()
