"""WindowTracker — theo dõi cửa sổ ứng dụng đang active trên hệ điều hành Windows.

Giúp companion biết người dùng đang mở ứng dụng nào (VS Code, Chrome, Discord...).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger("ai-companion.world.windows")


class WindowTracker:
    """Theo dõi cửa sổ đang active."""

    def __init__(self) -> None:
        self._active_window_title: str = "unknown"
        self._active_app: str = "unknown"

    def get_active_window(self) -> Dict[str, str]:
        """Lấy thông tin cửa sổ đang active thực tế từ hệ thống."""
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win and win.title:
                self._active_window_title = win.title
                self._active_app = self._detect_app_name(win.title)
            else:
                self._active_window_title = "Desktop / Idle"
                self._active_app = "Explorer"
        except Exception as e:
            logger.debug("Failed to get active window via pygetwindow: %s", e)
            # Giữ trạng thái cũ nếu lỗi

        return {
            "title": self._active_window_title,
            "app":   self._active_app
        }

    def _detect_app_name(self, title: str) -> str:
        """Suy luận tên ứng dụng từ tiêu đề cửa sổ."""
        title_lower = title.lower()
        if "visual studio code" in title_lower or "vscode" in title_lower or " - code" in title_lower:
            return "VS Code"
        if "chrome" in title_lower:
            return "Google Chrome"
        if "edge" in title_lower:
            return "Microsoft Edge"
        if "discord" in title_lower:
            return "Discord"
        if "command prompt" in title_lower or "cmd" in title_lower or "powershell" in title_lower or "terminal" in title_lower:
            return "Terminal"
        if "youtube" in title_lower:
            return "YouTube"
        if "spotify" in title_lower:
            return "Spotify"
        
        # Tách phần cuối tiêu đề (thường là tên app: e.g. "document - Notepad")
        parts = title.split(" - ")
        if len(parts) > 1:
            return parts[-1].strip()
            
        return "Unknown App"


# Global singleton
window_tracker = WindowTracker()
