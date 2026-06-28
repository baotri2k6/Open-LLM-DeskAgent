"""ReflectionEngine — phân tích và phản tỉnh (Reflection) nâng cao sau thực thi.

Không chỉ ghi lại kết quả mà còn suy luận ra các niềm tin (Beliefs) mới từ trải nghiệm.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from learning.experience.experience_store import experience_store
from belief.belief_store import belief_store


logger = logging.getLogger("ai-companion.learning.reflection")


class ReflectionEngine:
    """Điều khiển quy trình tự phản tỉnh để sinh niềm tin từ trải nghiệm."""

    def __init__(self) -> None:
        pass

    def reflect_on_goal(self, goal_id: str, goal_desc: str, task_graph: Any) -> dict:
        """Thực hiện phản tỉnh sau khi một goal kết thúc.

        Ghi nhận trải nghiệm vào ExperienceStore và suy luận niềm tin mới.
        """
        is_successful = task_graph.is_completed()
        
        # 1. Tạo tóm tắt bài học kinh nghiệm
        failed_tasks = [t for t in task_graph._tasks.values() if t.status == "FAILED"]
        lessons = []
        if is_successful:
            lessons.append(f"Goal '{goal_desc}' completed successfully.")
        else:
            lessons.append(f"Goal '{goal_desc}' failed.")
            for ft in failed_tasks:
                lessons.append(f"Task '{ft.id}' failed with error: {ft.error}")

        lessons_str = "\n".join(lessons)

        # 2. Lưu vào ExperienceStore
        experience_store.record_experience(
            goal_id=goal_id,
            goal_desc=goal_desc,
            is_successful=is_successful,
            lessons_learned=lessons_str
        )

        # 3. Suy luận niềm tin (Deduction of Beliefs)
        # Ví dụ: Nếu một tool cụ thể liên tục lỗi, tạo niềm tin là môi trường lỗi
        if not is_successful and failed_tasks:
            primary_fail = failed_tasks[0]
            if "not found" in primary_fail.error.lower() or "denied" in primary_fail.error.lower():
                belief_key = f"env.tool_broken.{primary_fail.tool_name}"
                belief_store.set_belief(
                    key=belief_key,
                    value="true",
                    confidence=0.7,
                    source="deduction"
                )

        return {
            "goal_id": goal_id,
            "success": is_successful,
            "lessons": lessons_str
        }


# Global singleton
reflection_engine = ReflectionEngine()
