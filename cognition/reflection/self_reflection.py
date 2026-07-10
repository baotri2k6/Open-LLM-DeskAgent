"""SelfReflection — tự soi chiếu (Self-Reflection) sau khi hoàn thành task hoặc kế hoạch.

Đánh giá xem kết quả đạt được có khớp với mục tiêu ban đầu không và rút ra bài học kinh nghiệm.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger("ai-companion.cognition.reflection")


@dataclass
class ReflectionResult:
    """Kết quả tự soi chiếu."""
    goal_id:       str
    is_successful: bool
    lessons_learned: str = ""
    duration_s:    float = 0.0
    timestamp:     float = field(default_factory=time.time)


class SelfReflection:
    """Thực hiện đánh giá hiệu quả hoạt động của agent sau mỗi chuỗi hành động."""

    def __init__(self) -> None:
        self._reflections: list[ReflectionResult] = []

    def reflect(self, goal_id: str, goal_description: str, task_graph: Any) -> ReflectionResult:
        """Thực hiện soi chiếu đánh giá kết quả của TaskGraph.

        Args:
            goal_id: ID của mục tiêu.
            goal_description: Mô tả mục tiêu.
            task_graph: Đồ thị TaskGraph đã chạy.
        """
        logger.info("Starting self-reflection for goal: %s", goal_description)

        is_successful = task_graph.is_completed()
        
        # Thống kê nhanh các lỗi gặp phải
        failed_tasks = [t for t in task_graph._tasks.values() if t.status == "FAILED"]
        
        lessons = []
        if is_successful:
            lessons.append(f"Kế hoạch '{goal_description}' đã hoàn thành tốt.")
            lessons.append(f"Đã chạy thành công {len(task_graph._tasks)} tác vụ.")
        else:
            lessons.append(f"Kế hoạch '{goal_description}' thất bại.")
            for ft in failed_tasks:
                lessons.append(f"Task `{ft.id}` thất bại với lỗi: {ft.error}")
            lessons.append("Bài học: Cần kiểm tra kỹ môi trường hoặc đổi phương pháp sửa lỗi.")

        result = ReflectionResult(
            goal_id=goal_id,
            is_successful=is_successful,
            lessons_learned="\n".join(lessons),
        )
        
        self._reflections.append(result)
        
        # Trigger event ghi lại trải nghiệm học tập nếu có lỗi
        if not is_successful:
            try:
                from motivation.motivation_manager import motivation_manager
                motivation_manager.on_learned_something(f"fix_error_{goal_id[:8]}")
            except Exception:
                pass
                
        return result

    def get_reflection_history(self) -> list[ReflectionResult]:
        """Lấy lịch sử tự soi chiếu."""
        return self._reflections


# Global singleton
self_reflection = SelfReflection()
