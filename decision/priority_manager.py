"""PriorityManager — quản lý độ ưu tiên của các tác vụ và ý định.

Giúp companion xếp loại các hành động từ khẩn cấp (Critical) đến rỗi rãi (Idle) để xử lý đúng thứ tự.
"""

from __future__ import annotations

import logging
from typing import Dict

logger = logging.getLogger("ai-companion.decision.priority")


class PriorityManager:
    """Quản lý và giải quyết độ ưu tiên."""

    # Độ ưu tiên chuẩn hóa
    PRIORITIES = {
        "CRITICAL": 1,
        "HIGH":     2,
        "MEDIUM":   3,
        "LOW":      4,
        "IDLE":     5,
    }

    def __init__(self) -> None:
        pass

    def get_priority_val(self, priority_label: str) -> int:
        """Chuyển đổi nhãn ưu tiên thành số nguyên."""
        return self.PRIORITIES.get(priority_label.upper(), 3)

    def resolve_priority(self, action_name: str, base_priority: int = 3) -> int:
        """Tính toán lại độ ưu tiên thực tế dựa trên loại hành động.

        Ví dụ: Lệnh sửa lỗi có độ ưu tiên cao hơn lệnh chat giải trí.
        """
        action_lower = action_name.lower()
        
        # Các hành động nguy cấp hoặc sửa lỗi
        if any(k in action_lower for k in ["fix", "error", "critical", "shutdown"]):
            return 1  # Critical
            
        # Lập trình / làm việc
        if any(k in action_lower for k in ["code", "write", "compile", "build"]):
            return 2  # High
            
        # Tương tác và giải trí
        if any(k in action_lower for k in ["chat", "joke", "curiosity", "music"]):
            return 4  # Low
            
        return base_priority


# Global singleton
priority_manager = PriorityManager()
