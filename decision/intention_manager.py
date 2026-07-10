"""IntentionManager — quản lý các ý định (Intentions) của companion.

Mô hình hóa ý đồ ngắn hạn và dài hạn của companion (ví dụ: 'giúp đỡ người dùng sửa lỗi', 'gợi chuyện giải trí').
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("ai-companion.decision.intention_manager")


@dataclass
class Intention:
    """Ý định hoạt động của companion."""
    name:        str
    category:    str   # proactive | task | relationship | entertainment
    priority:    int   = 3  # 1 = Critical, 5 = Low
    description: str   = ""


class IntentionManager:
    """Quản lý các ý định của companion."""

    def __init__(self) -> None:
        self._intentions: List[Intention] = []
        # Ý định mặc định: giữ kết nối casual
        self._intentions.append(Intention(
            name="casual_connection",
            category="relationship",
            priority=4,
            description="Duy trì kết nối tự nhiên và thân thiện với user"
        ))

    def set_active_intention(self, name: str, category: str, priority: int = 3, description: str = "") -> Intention:
        """Đăng ký một ý định active mới (thay thế hoặc thêm vào)."""
        # Tránh trùng lặp cùng tên
        self.clear_intention(name)
        
        intent = Intention(name=name, category=category, priority=priority, description=description)
        self._intentions.insert(0, intent)  # Cho lên đầu danh sách ưu tiên
        logger.info("Active Intention registered: %s (Category=%s, Priority=%d)", name, category, priority)
        return intent

    def get_highest_intention(self) -> Optional[Intention]:
        """Lấy ý định có độ ưu tiên cao nhất."""
        if not self._intentions:
            return None
        return min(self._intentions, key=lambda i: i.priority)

    def clear_intention(self, name: str) -> bool:
        """Xóa một ý định khi đã hoàn thành hoặc hết tác dụng."""
        original_len = len(self._intentions)
        self._intentions = [i for i in self._intentions if i.name != name]
        
        if len(self._intentions) < original_len:
            logger.info("Intention cleared: %s", name)
            return True
        return False

    def list_intentions(self) -> List[Intention]:
        """Liệt kê toàn bộ danh sách ý định hiện tại."""
        return self._intentions


# Global singleton
intention_manager = IntentionManager()
