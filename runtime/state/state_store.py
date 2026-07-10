"""CompanionState — state machine cho AI companion.

Companion luôn ở trong một trạng thái xác định.
Mọi transition đều phát StateChanged event.
"""

from __future__ import annotations

import asyncio
import logging
from enum import Enum, auto
from typing import Callable, Optional

logger = logging.getLogger("ai-companion.runtime.state")


class CompanionState(Enum):
    """Các trạng thái của companion."""
    IDLE        = auto()   # Đang chờ, Life Loop chạy ngầm
    LISTENING   = auto()   # VAD / STT đang active
    THINKING    = auto()   # LLM đang stream response
    PLANNING    = auto()   # Đang tạo task graph
    EXECUTING   = auto()   # Đang dùng tool / computer use
    REFLECTING  = auto()   # Đang self-evaluate
    SPEAKING    = auto()   # TTS + lipsync đang phát
    SLEEPING    = auto()   # Idle quá lâu — Life Loop throttled
    ERROR       = auto()   # Đang xử lý lỗi


# Các transition hợp lệ: state → set of next states
VALID_TRANSITIONS: dict[CompanionState, set[CompanionState]] = {
    CompanionState.IDLE:       {CompanionState.LISTENING, CompanionState.THINKING, CompanionState.SLEEPING},
    CompanionState.LISTENING:  {CompanionState.THINKING, CompanionState.IDLE},
    CompanionState.THINKING:   {CompanionState.PLANNING, CompanionState.SPEAKING, CompanionState.IDLE, CompanionState.ERROR},
    CompanionState.PLANNING:   {CompanionState.EXECUTING, CompanionState.SPEAKING, CompanionState.ERROR},
    CompanionState.EXECUTING:  {CompanionState.REFLECTING, CompanionState.SPEAKING, CompanionState.ERROR},
    CompanionState.REFLECTING: {CompanionState.SPEAKING, CompanionState.EXECUTING, CompanionState.IDLE},
    CompanionState.SPEAKING:   {CompanionState.IDLE, CompanionState.SLEEPING},
    CompanionState.SLEEPING:   {CompanionState.IDLE, CompanionState.LISTENING},
    CompanionState.ERROR:      {CompanionState.IDLE, CompanionState.SPEAKING},
}


class StateStore:
    """Quản lý trạng thái hiện tại của companion và phát StateChanged events.

    Sử dụng pattern singleton — dùng state_store global instance.
    """

    def __init__(self) -> None:
        self._state: CompanionState = CompanionState.IDLE
        self._previous: CompanionState = CompanionState.IDLE
        self._listeners: list[Callable] = []
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CompanionState:
        """Trạng thái hiện tại."""
        return self._state

    @property
    def previous(self) -> CompanionState:
        """Trạng thái trước đó."""
        return self._previous

    @property
    def state_name(self) -> str:
        return self._state.name

    def on_change(self, callback: Callable) -> None:
        """Đăng ký callback sẽ được gọi khi state thay đổi.

        Callback signature: callback(from_state, to_state)
        """
        self._listeners.append(callback)

    async def transition(
        self,
        new_state: CompanionState,
        force: bool = False,
    ) -> bool:
        """Thực hiện state transition.

        Args:
            new_state: Trạng thái muốn chuyển sang.
            force: Bỏ qua validation (dùng cho emergency reset).

        Returns:
            True nếu transition thành công, False nếu invalid.
        """
        async with self._lock:
            if not force and new_state not in VALID_TRANSITIONS.get(self._state, set()):
                logger.warning(
                    "Invalid state transition: %s -> %s",
                    self._state.name, new_state.name
                )
                return False

            if self._state == new_state:
                return True

            old_state = self._state
            self._previous = old_state
            self._state = new_state

            logger.info("State: %s -> %s", old_state.name, new_state.name)

            # Notify listeners
            for cb in self._listeners:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        asyncio.create_task(cb(old_state, new_state))
                    else:
                        cb(old_state, new_state)
                except Exception as e:
                    logger.error("State listener error: %s", e)

            return True

    async def reset(self) -> None:
        """Reset về IDLE — dùng khi có lỗi nghiêm trọng."""
        await self.transition(CompanionState.IDLE, force=True)

    def is_busy(self) -> bool:
        """Companion có đang làm gì không (không phải IDLE/SLEEPING/ERROR)."""
        return self._state in {
            CompanionState.LISTENING,
            CompanionState.THINKING,
            CompanionState.PLANNING,
            CompanionState.EXECUTING,
            CompanionState.REFLECTING,
            CompanionState.SPEAKING,
        }

    def __repr__(self) -> str:
        return f"StateStore(state={self._state.name})"


# Global singleton
state_store = StateStore()
