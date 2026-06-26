"""System service wrapping safe desktop actions."""

from __future__ import annotations

import platform

from agents.desktop.desktop_agent import DesktopAgent


class SystemService:
    def __init__(self) -> None:
        self.desktop = DesktopAgent()

    async def open_app(self, app_name: str) -> dict:
        return await self.desktop.open_application(app_name)

    async def system_info(self) -> dict:
        try:
            import psutil

            memory = psutil.virtual_memory()
            return {
                "success": True,
                "os": platform.system(),
                "osVersion": platform.version(),
                "cpuPercent": psutil.cpu_percent(interval=0.1),
                "memoryPercent": memory.percent,
            }
        except Exception:
            return {
                "success": True,
                "os": platform.system(),
                "osVersion": platform.version(),
            }
