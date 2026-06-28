"""WorldModel — mô hình hóa thế giới xung quanh của companion.

Tổng hợp thông tin từ tất cả các trackers (cửa sổ đang mở, ứng dụng đang chạy, hoạt động người dùng)
để tạo ra một cái nhìn toàn diện về ngữ cảnh hiện tại.
"""

from __future__ import annotations

import logging
from typing import Dict

from world.windows.window_tracker import window_tracker
from world.applications.app_tracker import app_tracker
from world.activity.activity_tracker import activity_tracker

logger = logging.getLogger("ai-companion.world.model")


class WorldModel:
    """Mô hình thế giới xung quanh của companion."""

    def __init__(self) -> None:
        pass

    def get_summary(self) -> str:
        """Tạo chuỗi mô tả tóm tắt ngữ cảnh thế giới hiện tại cho PromptBuilder.

        Ví dụ:
          "User đang viết code trên VS Code (cửa sổ: server.py - Code).
           Các ứng dụng đang mở rộng: Chrome, Discord."
        """
        try:
            act_info = activity_tracker.get_current_activity()
            running = app_tracker.get_running_apps()
            
            # Lọc bỏ app hiện tại khỏi danh sách app chạy ngầm để không trùng lặp
            other_apps = [a for a in running if a != act_info["app"]]
            
            summary = f"Hoạt động: {act_info['details']} trên {act_info['app']}"
            if act_info["window"] and act_info["window"] != act_info["app"]:
                summary += f" (Cửa sổ: {act_info['window']})"
                
            if other_apps:
                summary += f"\nỨng dụng chạy ngầm: {', '.join(other_apps)}"
                
            return summary
        except Exception as e:
            logger.error("Failed to build world model summary: %s", e)
            return "Hoạt động: Chưa rõ"

    def get_state_snapshot(self) -> Dict:
        """Lấy snapshot đầy đủ trạng thái thế giới cho API."""
        try:
            return {
                "activity": activity_tracker.get_current_activity(),
                "running_apps": app_tracker.get_running_apps(),
                "active_window": window_tracker.get_active_window()
            }
        except Exception:
            return {}


# Global singleton
world_model = WorldModel()
