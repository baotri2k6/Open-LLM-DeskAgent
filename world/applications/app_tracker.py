"""AppTracker — theo dõi danh sách các ứng dụng đang chạy chạy ngầm.

Sử dụng psutil để quét nhanh các tiến trình chạy trên hệ thống mà không gây nghẽn CPU.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger("ai-companion.world.applications")


class AppTracker:
    """Theo dõi danh sách các ứng dụng lập trình/văn phòng đang chạy."""

    # Chỉ quét các tiến trình phổ biến để tránh làm chậm hệ thống
    POPULAR_APPS = {
        "code.exe":       "VS Code",
        "chrome.exe":     "Chrome",
        "msedge.exe":     "Edge",
        "discord.exe":    "Discord",
        "spotify.exe":    "Spotify",
        "slack.exe":      "Slack",
        "pycharm64.exe":  "PyCharm",
        "idea64.exe":     "IntelliJ IDEA",
        "docker desktop.exe": "Docker",
        "notion.exe":     "Notion",
    }

    def __init__(self) -> None:
        self._running_apps: List[str] = []

    def get_running_apps(self) -> List[str]:
        """Quét các tiến trình đang chạy và trả về tên các app phát hiện được."""
        try:
            import psutil
            detected = set()
            for proc in psutil.process_iter(attrs=["name"]):
                try:
                    name = proc.info["name"]
                    if name:
                        name_lower = name.lower()
                        if name_lower in self.POPULAR_APPS:
                            detected.add(self.POPULAR_APPS[name_lower])
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            self._running_apps = sorted(list(detected))
        except Exception as e:
            logger.debug("Failed to scan processes via psutil: %s", e)

        return self._running_apps


# Global singleton
app_tracker = AppTracker()
