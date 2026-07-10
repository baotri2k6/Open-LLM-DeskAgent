"""IdleAnimator — điều khiển idle animations cho Live2D avatar.

Khi companion không làm gì, avatar cần trông 'sống động' chứ không đứng hình.
IdleAnimator chọn và schedule các idle animation dựa trên:
- Thời gian idle
- Mood hiện tại
- Energy level
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import Optional, Callable

logger = logging.getLogger("ai-companion.persona.behavior.idle")


@dataclass
class IdleAnimation:
    """Một idle animation entry."""
    name:     str
    priority: int   = 1   # Cao hơn = ưu tiên hơn
    weight:   float = 1.0  # Xác suất chọn (relative)
    mood_fit: list[str] = None  # Mood phù hợp. None = fit tất cả

    def __post_init__(self):
        if self.mood_fit is None:
            self.mood_fit = []


class IdleAnimator:
    """Quản lý idle animation sequence cho Live2D avatar.

    Gửi animation commands đến renderer qua WebSocket callback.
    """

    # Thư viện idle animations
    IDLE_LIBRARY: list[IdleAnimation] = [
        IdleAnimation("idle_breathe",     priority=1, weight=3.0),     # Thở bình thường — phổ biến nhất
        IdleAnimation("idle_blink",       priority=1, weight=2.5),     # Chớp mắt
        IdleAnimation("idle_look_around", priority=2, weight=1.5),     # Nhìn xung quanh
        IdleAnimation("idle_hair_touch",  priority=2, weight=1.0),     # Chạm tóc
        IdleAnimation("idle_stretch",     priority=3, weight=0.5),     # Vươn vai (ít thường xuyên)
        IdleAnimation("idle_yawn",        priority=3, weight=0.3,
                      mood_fit=["buồn ngủ", "mệt"]),                   # Ngáp khi mệt
        IdleAnimation("idle_excited",     priority=2, weight=1.2,
                      mood_fit=["vui vẻ", "phấn khích"]),              # Hứng khởi khi vui
        IdleAnimation("idle_thinking",    priority=2, weight=0.8,
                      mood_fit=["tập trung", "tò mò"]),                # Suy nghĩ
    ]

    # Interval giữa các animation (giây)
    MIN_INTERVAL = 5.0
    MAX_INTERVAL = 15.0

    def __init__(self) -> None:
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._send_command: Optional[Callable] = None   # Callback gửi đến WS
        self._current_mood = "vui vẻ"

    def set_send_callback(self, callback: Callable) -> None:
        """Đặt callback function để gửi animation command."""
        self._send_command = callback

    def update_mood(self, mood: str) -> None:
        """Cập nhật mood để chọn animation phù hợp."""
        self._current_mood = mood

    async def start(self) -> None:
        """Start idle animation loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("IdleAnimator: started")

    def stop(self) -> None:
        """Stop idle animation loop."""
        self._running = False
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        """Main animation loop."""
        while self._running:
            try:
                anim = self._pick_animation()
                await self._play(anim)
                interval = random.uniform(self.MIN_INTERVAL, self.MAX_INTERVAL)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("IdleAnimator error: %s", e)
                await asyncio.sleep(5.0)

    def _pick_animation(self) -> IdleAnimation:
        """Chọn animation theo weight và mood."""
        candidates = []
        weights = []
        for anim in self.IDLE_LIBRARY:
            if not anim.mood_fit or self._current_mood in anim.mood_fit:
                candidates.append(anim)
                weights.append(anim.weight)

        if not candidates:
            return self.IDLE_LIBRARY[0]  # fallback: breathe

        return random.choices(candidates, weights=weights, k=1)[0]

    async def _play(self, anim: IdleAnimation) -> None:
        """Phát animation bằng cách gửi command qua callback."""
        command = {
            "type":     "motion",
            "name":     anim.name,
            "priority": anim.priority,
            "source":   "idle_animator",
        }
        logger.debug("Idle animation: %s", anim.name)
        if self._send_command:
            try:
                if asyncio.iscoroutinefunction(self._send_command):
                    await self._send_command(command)
                else:
                    self._send_command(command)
            except Exception as e:
                logger.debug("Animation send error: %s", e)

    def trigger_now(self, animation_name: str) -> None:
        """Trigger một animation cụ thể ngay lập tức (bất đồng bộ)."""
        asyncio.create_task(self._play(IdleAnimation(animation_name, priority=5)))


# Global singleton
idle_animator = IdleAnimator()
