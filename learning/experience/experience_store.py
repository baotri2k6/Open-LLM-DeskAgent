"""ExperienceStore — lưu trữ lịch sử trải nghiệm (Experiences) của companion.

Lưu lại kết quả thực thi các kế hoạch (Plan) và cuộc gọi công cụ.
Giúp companion tự phản tỉnh và học hỏi từ các sai lầm trong quá khứ.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger("ai-companion.learning.experience")


@dataclass
class Experience:
    """Định nghĩa một trải nghiệm hoạt động."""
    goal_id:        str
    goal_desc:      str
    is_successful:  bool
    lessons_learned: str
    timestamp:      float = field(default_factory=time.time)
    metadata:       dict = field(default_factory=dict)


class ExperienceStore:
    """Lưu trữ lịch sử thực tế của các hoạt động lập kế hoạch và sửa lỗi."""

    def __init__(self) -> None:
        self._experiences: List[Experience] = []

    def record_experience(
        self,
        goal_id: str,
        goal_desc: str,
        is_successful: bool,
        lessons_learned: str,
        metadata: dict | None = None
    ) -> Experience:
        """Ghi nhận một trải nghiệm mới."""
        exp = Experience(
            goal_id=goal_id,
            goal_desc=goal_desc,
            is_successful=is_successful,
            lessons_learned=lessons_learned,
            metadata=metadata or {}
        )
        self._experiences.append(exp)
        logger.info("Experience recorded: '%s' (Success: %s)", goal_desc, is_successful)
        return exp

    def get_recent_experiences(self, limit: int = 5) -> List[Experience]:
        """Lấy danh sách các trải nghiệm gần đây."""
        return self._experiences[-limit:]

    def get_failures(self) -> List[Experience]:
        """Lấy toàn bộ các trải nghiệm thất bại để học tập."""
        return [e for e in self._experiences if not e.is_successful]


# Global singleton
experience_store = ExperienceStore()
