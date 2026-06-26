"""Skills Manager — Auto-loads and manages local skills from skills/ directory."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from config.config import PROJECT_ROOT
from runtime.logger import get_logger

logger = get_logger("ai-companion.skills")

class SkillsManager:
    _instance: SkillsManager | None = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SkillsManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        # Prevent re-initialization
        if hasattr(self, "_initialized") and self._initialized:
            return
        
        self.skills_dir = PROJECT_ROOT / "skills"
        try:
            self.skills_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create skills directory: {e}")
            
        self._initialized = True

    def list_skills(self) -> list[dict]:
        """Quét thư mục skills và trả về danh sách metadata của các kỹ năng tìm thấy."""
        if not self.skills_dir.exists():
            return []

        skills_list = []
        try:
            for item in self.skills_dir.iterdir():
                if item.is_dir():
                    skill_md_path = item / "SKILL.md"
                    if skill_md_path.exists():
                        try:
                            content = skill_md_path.read_text(encoding="utf-8")
                            meta = self._parse_yaml_frontmatter(content)
                            meta.setdefault("name", item.name)
                            meta.setdefault("description", "Không có mô tả.")
                            skills_list.append(meta)
                        except Exception as e:
                            logger.error(f"Failed to read skill {item.name}: {e}")
        except Exception as e:
            logger.error(f"Error scanning skills directory: {e}")
            
        return skills_list

    def read_skill_content(self, name: str) -> dict:
        """Đọc toàn bộ nội dung tệp SKILL.md của kỹ năng có tên tương ứng."""
        # Sanitization
        name = name.strip().replace("..", "").replace("/", "").replace("\\", "")
        skill_file = self.skills_dir / name / "SKILL.md"
        
        if not skill_file.exists():
            return {"success": False, "error": f"Không tìm thấy kỹ năng '{name}'."}

        try:
            content = skill_file.read_text(encoding="utf-8")
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": f"Lỗi khi đọc tệp kỹ năng: {e}"}

    def manage_skill(self, action: str, name: str, content: str = "", description: str = "") -> dict:
        """Quản lý (tạo mới, cập nhật, xóa) kỹ năng cục bộ."""
        action = action.lower().strip()
        name = name.strip().replace("..", "").replace("/", "").replace("\\", "")
        
        if not name:
            return {"success": False, "error": "Tên kỹ năng không được để trống."}
            
        skill_folder = self.skills_dir / name
        skill_file = skill_folder / "SKILL.md"

        if action == "create":
            if skill_file.exists():
                return {"success": False, "error": f"Kỹ năng '{name}' đã tồn tại. Hãy sử dụng action 'update'."}
                
            try:
                skill_folder.mkdir(parents=True, exist_ok=True)
                
                # Tạo frontmatter cơ bản
                frontmatter = f"---\nname: {name}\ndescription: \"{description or 'Không có mô tả.'}\"\nversion: 1.0.0\nauthor: \"DeskAgent Autonomous\"\n---\n\n"
                full_content = frontmatter + content
                
                skill_file.write_text(full_content, encoding="utf-8")
                return {"success": True, "message": f"Đã tạo kỹ năng mới '{name}' thành công."}
            except Exception as e:
                return {"success": False, "error": f"Không thể tạo kỹ năng: {e}"}

        elif action == "update":
            if not skill_file.exists():
                return {"success": False, "error": f"Kỹ năng '{name}' không tồn tại để cập nhật."}
                
            try:
                # Đọc frontmatter hiện tại để giữ lại nếu content không cung cấp frontmatter mới
                orig_content = skill_file.read_text(encoding="utf-8")
                frontmatter_match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n", orig_content)
                
                if content.startswith("---"):
                    full_content = content
                else:
                    orig_frontmatter = frontmatter_match.group(0) if frontmatter_match else ""
                    full_content = orig_frontmatter + content
                    
                skill_file.write_text(full_content, encoding="utf-8")
                return {"success": True, "message": f"Đã cập nhật kỹ năng '{name}' thành công."}
            except Exception as e:
                return {"success": False, "error": f"Không thể cập nhật kỹ năng: {e}"}

        elif action == "delete":
            if not skill_folder.exists():
                return {"success": False, "error": f"Kỹ năng '{name}' không tồn tại."}
                
            try:
                shutil.rmtree(skill_folder)
                return {"success": True, "message": f"Đã xóa kỹ năng '{name}' thành công."}
            except Exception as e:
                return {"success": False, "error": f"Không thể xóa thư mục kỹ năng: {e}"}
                
        else:
            return {"success": False, "error": f"Hành động '{action}' không hợp lệ. Chỉ chấp nhận: 'create', 'update', 'delete'."}

    def _parse_yaml_frontmatter(self, content: str) -> dict:
        """Phân tách khối YAML frontmatter giữa cặp dấu ---."""
        match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n", content)
        meta = {}
        if match:
            yaml_block = match.group(1)
            for line in yaml_block.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    key, val = line.split(":", 1)
                    key = key.strip().lower()
                    val = val.strip().strip('"').strip("'")
                    meta[key] = val
        return meta
