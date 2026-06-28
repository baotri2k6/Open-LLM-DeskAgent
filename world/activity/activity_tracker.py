"""ActivityTracker — theo dõi và suy luận hoạt động thời gian thực của người dùng.

Companion phân tích cửa sổ đang hoạt động để biết người dùng đang code, lướt web, nghe nhạc hay làm việc.
"""

from __future__ import annotations

import logging
from typing import Dict

from world.windows.window_tracker import window_tracker

logger = logging.getLogger("ai-companion.world.activity")


class ActivityTracker:
    """Suy luận hoạt động của người dùng dựa trên active window."""

    def __init__(self) -> None:
        self._current_activity: str = "unknown"

    def get_current_activity(self) -> Dict[str, str]:
        """Lấy hoạt động hiện tại và trả về nhãn hoạt động."""
        win_info = window_tracker.get_active_window()
        title = win_info["title"].lower()
        app = win_info["app"]

        activity = "unknown"
        details = f"Đang mở {app}"

        if app == "VS Code" or "code" in title or "pycharm" in title:
            activity = "coding"
            details = "Đang viết code"
        elif "youtube" in title:
            activity = "watching_youtube"
            details = "Đang xem YouTube"
        elif app in ("Google Chrome", "Microsoft Edge"):
            activity = "browsing"
            details = "Đang duyệt web"
        elif app in ("Discord", "Slack"):
            activity = "chatting"
            details = "Đang trò chuyện"
        elif app == "Terminal":
            activity = "terminal_work"
            details = "Đang thao tác dòng lệnh"
        elif "spotify" in title or app == "Spotify":
            activity = "listening_music"
            details = "Đang nghe nhạc trên Spotify"
        elif app == "Explorer" or "thư mục" in title:
            activity = "file_management"
            details = "Đang xem thư mục tập tin"
        elif win_info["title"] == "Desktop / Idle":
            activity = "idle"
            details = "Đang ở màn hình Desktop"

        self._current_activity = activity
        
        return {
            "activity": activity,
            "details":  details,
            "app":      app,
            "window":   win_info["title"]
        }


# Global singleton
activity_tracker = ActivityTracker()
