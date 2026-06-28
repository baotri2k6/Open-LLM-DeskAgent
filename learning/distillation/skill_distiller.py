"""SkillDistiller — chưng cất trải nghiệm thành tệp kỹ năng Markdown tái sử dụng.

Tự động sinh cấu trúc Markdown Skill (Skill DSL) và lưu vào thư mục skills/.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from skills.skills_manager import SkillsManager

logger = logging.getLogger("ai-companion.learning.distillation")


class SkillDistiller:
    """Chưng cất chuỗi tác vụ thành file kỹ năng Markdown."""

    def __init__(self) -> None:
        self.skills_manager = SkillsManager()

    def distill_to_skill(self, skill_name: str, description: str, recipe: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Tạo tệp SKILL.md từ công thức hành động đã trích xuất.

        Args:
            skill_name: Tên kỹ năng (dạng snake_case, ví dụ: 'auto_git_push').
            description: Mô tả mục đích.
            recipe: Chuỗi các bước đã trích xuất từ SkillExtractor.
        """
        if not recipe:
            return {"success": False, "error": "Recipe is empty, cannot distill"}

        # 1. Sinh nội dung Markdown theo định dạng Skill DSL
        steps_md = []
        for idx, step in enumerate(recipe, start=1):
            tool = step.get("tool_name", "unknown")
            args = step.get("arguments", {})
            steps_md.append(
                f"## Bước {idx}: Gọi công cụ `{tool}`\n"
                f"Sử dụng công cụ `{tool}` với các tham số:\n"
                f"```json\n"
                f"{args}\n"
                f"```\n"
            )
            
        markdown_body = "\n".join(steps_md)
        
        # 2. Sử dụng SkillsManager để tạo/lưu file kỹ năng cục bộ
        # manage_skill tự động tạo frontmatter YAML và ghi file
        res = self.skills_manager.manage_skill(
            action="create",
            name=skill_name,
            content=markdown_body,
            description=description
        )
        
        if res.get("success"):
            logger.info("Distilled skill '%s' successfully saved to skills directory", skill_name)
        else:
            logger.error("Failed to distill skill '%s': %s", skill_name, res.get("error"))
            
        return res


# Global singleton
skill_distiller = SkillDistiller()
