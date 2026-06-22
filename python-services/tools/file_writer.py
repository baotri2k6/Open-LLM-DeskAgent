"""File writer tool."""

from __future__ import annotations

import os
from pathlib import Path


def write_to_file(path: str, content: str, overwrite: bool = True) -> dict:
    """Ghi nội dung vào file tại path, hỗ trợ ghi đè."""
    try:
        p = Path(path).expanduser().resolve()
        
        # Kiểm tra nếu file đã tồn tại và không cho phép ghi đè
        if p.exists() and not overwrite:
            return {"success": False, "error": f"File đã tồn tại và config overwrite=False: {path}"}
            
        # Tạo thư mục cha nếu chưa có
        p.parent.mkdir(parents=True, exist_ok=True)
        
        # Ghi nội dung
        p.write_text(content, encoding="utf-8")
        
        return {
            "success": True,
            "message": f"Đã ghi thành công {len(content)} ký tự vào file {path}",
            "path": str(p)
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
