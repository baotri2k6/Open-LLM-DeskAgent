"""SessionManager — quản lý vòng đời của một conversation session.

Một session = từ lúc user bắt đầu tương tác đến lúc idle > N phút.
SessionManager track context, gọi on_session_start/end cho các modules.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4

logger = logging.getLogger("ai-companion.runtime.session")


@dataclass
class Session:
    """Dữ liệu của một session."""
    id:            UUID  = field(default_factory=uuid4)
    started_at:    float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    turn_count:    int   = 0
    is_active:     bool  = True

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.started_at

    @property
    def idle_seconds(self) -> float:
        return time.time() - self.last_activity


class SessionManager:
    """Quản lý session lifecycle.

    - Tạo session mới khi user bắt đầu tương tác
    - Notify các modules khi session start/end
    - Tự động end session sau khi idle > threshold
    """

    SESSION_TIMEOUT_MINUTES = 30    # Auto-end session sau 30 phút idle

    def __init__(self) -> None:
        self._current: Session | None = None
        self._history: list[Session] = []

    @property
    def current(self) -> Session | None:
        return self._current

    @property
    def is_active(self) -> bool:
        return self._current is not None and self._current.is_active

    def start_session(self) -> Session:
        """Bắt đầu session mới và notify các modules."""
        if self._current and self._current.is_active:
            # Đã có session active — chỉ update last_activity
            self._current.last_activity = time.time()
            return self._current

        session = Session()
        self._current = session
        logger.info("Session started: %s", str(session.id)[:8])

        # Notify modules
        self._notify_start()
        return session

    def on_user_activity(self) -> None:
        """Gọi mỗi khi user có activity (message, voice, click...)."""
        if self._current is None:
            self.start_session()
        else:
            self._current.last_activity = time.time()
            self._current.turn_count += 1

    def end_session(self, summary: str = "") -> None:
        """Kết thúc session hiện tại."""
        if self._current is None:
            return
        self._current.is_active = False
        self._history.append(self._current)
        logger.info(
            "Session ended: %s (%.0fs, %d turns)",
            str(self._current.id)[:8],
            self._current.duration_seconds,
            self._current.turn_count,
        )
        self._notify_end(summary)
        self._current = None

    def check_timeout(self) -> bool:
        """Kiểm tra session có timeout không. True = đã end."""
        if self._current is None or not self._current.is_active:
            return False
        timeout = self.SESSION_TIMEOUT_MINUTES * 60
        if self._current.idle_seconds > timeout:
            self.end_session(summary="Session auto-ended due to inactivity")
            return True
        return False

    def _notify_start(self) -> None:
        try:
            from memory.memory_manager import memory_manager
            memory_manager.on_session_start()
        except Exception as e:
            logger.debug("Notify session start failed: %s", e)

        try:
            from social.conversation.conversation_manager import conversation_manager
            conversation_manager.reset()
        except Exception as e:
            logger.debug("Conversation reset failed: %s", e)

        try:
            from motivation.motivation_manager import motivation_manager
            motivation_manager.on_conversation()
        except Exception as e:
            logger.debug("Motivation notify failed: %s", e)

    def _notify_end(self, summary: str) -> None:
        try:
            from memory.memory_manager import memory_manager
            memory_manager.on_session_end(summary)
        except Exception as e:
            logger.debug("Notify session end failed: %s", e)

    def get_state_snapshot(self) -> dict:
        if self._current:
            return {
                "session_id":    str(self._current.id)[:8],
                "duration_s":    int(self._current.duration_seconds),
                "idle_s":        int(self._current.idle_seconds),
                "turn_count":    self._current.turn_count,
                "is_active":     self._current.is_active,
            }
        return {"is_active": False}


# Global singleton
session_manager = SessionManager()
