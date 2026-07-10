"""SkillExtractor — trích xuất các quy trình (recipes) thành công từ lịch sử tác vụ.

Phân tích TaskGraph đã hoàn thành để tìm ra chuỗi các cuộc gọi công cụ thành công.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("ai-companion.learning.skill_extraction")


class SkillExtractor:
    """Trích xuất chuỗi hành động thành công làm công thức kỹ năng."""

    def __init__(self) -> None:
        pass

    def extract_recipe(self, task_graph: Any) -> List[Dict[str, Any]]:
        """Trích xuất chuỗi các cuộc gọi công cụ thành công từ TaskGraph.

        Args:
            task_graph: Đối tượng TaskGraph từ planning.task_graph.

        Returns:
            Danh sách các bước thành công gồm tool_name và inputs.
        """
        recipe = []
        try:
            # Lấy toàn bộ task và lọc ra các task ở trạng thái COMPLETED
            tasks = list(task_graph._tasks.values())
            completed_tasks = [t for t in tasks if t.status == "COMPLETED"]

            
            for t in completed_tasks:
                if hasattr(t, "tool_name") and t.tool_name:
                    recipe.append({
                        "step_id": t.id,
                        "tool_name": t.tool_name,
                        "arguments": getattr(t, "arguments", {})
                    })
            
            logger.info("Extracted recipe with %d steps from graph '%s'", len(recipe), task_graph.goal_id)
        except Exception as e:
            logger.error("Failed to extract recipe from task graph: %s", e)
            
        return recipe


# Global singleton
skill_extractor = SkillExtractor()
