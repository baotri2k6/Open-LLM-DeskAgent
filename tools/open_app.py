"""open_app tool — wrapper mỏng trên DesktopAgent."""

from __future__ import annotations


async def open_application(app_name: str) -> dict:
    from agents.desktop.desktop_agent import DesktopAgent
    agent = DesktopAgent()
    return await agent.open_application(app_name)