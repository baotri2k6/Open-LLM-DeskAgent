"""PolicyEngine — quản lý và kiểm tra các chính sách hành vi (Policies).

Cung cấp luật kiểm tra (ví dụ: 'Chính sách im lặng - Silence Policy':
không được tự động ngắt quãng khi người dùng đang code tập trung).
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger("ai-companion.decision.policy")


class PolicyEngine:
    """Kiểm tra sự tuân thủ các chính sách hành vi của companion."""

    def __init__(self) -> None:
        pass

    def check_silence_policy(
        self,
        user_activity: str,
        idle_seconds: float,
        focus_index: float | None = None,
        active_window: str = "",
        screen_text: str = "",
    ) -> bool:
        """Kiểm tra xem có được phép tự động lên tiếng (proactive speak) hay không.

        Quy tắc:
        - Nếu focus index cao -> STAY SILENT (trả về False).
        - Nếu user đang coding hoặc thao tác terminal -> STAY SILENT.
        - Nếu user đang rảnh rỗi (idle > 300s) -> ALLOWED (trả về True).
        """
        if focus_index is None:
            focus_index = self.compute_focus_index(user_activity, idle_seconds, active_window, screen_text)

        if focus_index >= 0.65 and idle_seconds < 900:
            logger.debug("Silence Policy: focus_index=%.2f. Staying silent.", focus_index)
            return False

        if user_activity in ("coding", "terminal_work", "working_document") and idle_seconds < 600:
            logger.debug("Silence Policy: User is busy (%s). Staying silent.", user_activity)
            return False

        return True

    def compute_focus_index(
        self,
        user_activity: str,
        idle_seconds: float,
        active_window: str = "",
        screen_text: str = "",
    ) -> float:
        """Continuous focus score from activity, idle state, and screen context."""
        score = 0.0
        activity = (user_activity or "").lower()
        window = (active_window or "").lower()
        screen = (screen_text or "").lower()

        if activity in {"coding", "terminal_work", "working_document"}:
            score += 0.45
        elif activity in {"gaming", "watching_video"}:
            score += 0.2

        if any(token in window for token in ["code", "terminal", "powershell", "cmd", "pycharm", "intellij"]):
            score += 0.25
        if any(token in screen for token in ["traceback", "error:", "def ", "class ", "import ", "pytest", "npm run"]):
            score += 0.2

        if idle_seconds < 120:
            score += 0.1
        elif idle_seconds > 900:
            score -= 0.25

        return round(max(0.0, min(1.0, score)), 3)

    def check_safety_policy(self, tool_name: str, arguments: dict, user_approved: bool) -> bool:
        """Chính sách an toàn hệ thống."""
        # Nếu là tool ghi file hệ thống mà không được user duyệt -> Reject
        if tool_name == "execute_command" and not user_approved:
            # Kiểm tra xem có phải lệnh đọc thông tin an toàn không
            cmd = arguments.get("command", "").lower().strip()
            if cmd in ("dir", "ls", "git status"):
                return True
            return False
        return True


# Global singleton
policy_engine = PolicyEngine()
