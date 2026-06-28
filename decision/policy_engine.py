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

    def check_silence_policy(self, user_activity: str, idle_seconds: float) -> bool:
        """Kiểm tra xem có được phép tự động lên tiếng (proactive speak) hay không.

        Quy tắc:
        - Nếu user đang coding hoặc thao tác terminal -> STAY SILENT (trả về False).
        - Nếu user đang rảnh rỗi (idle > 300s) -> ALLOWED (trả về True).
        """
        # Nếu đang tập trung code hoặc gõ lệnh
        if user_activity in ("coding", "terminal_work"):
            if idle_seconds < 600:  # Dưới 10 phút im lặng kể từ lần gõ phím cuối
                logger.debug("Silence Policy: User is busy (%s). Staying silent.", user_activity)
                return False
                
        return True

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
