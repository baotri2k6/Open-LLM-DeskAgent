"""Vision service — delegate to VisionAgent."""

from __future__ import annotations

from agents.vision.vision_agent import VisionAgent


class VisionService:
    def __init__(self) -> None:
        self.agent = VisionAgent()

    async def describe_screen(self) -> dict:
        """Delegate screen description to the specialized VisionAgent."""
        return await self.agent.describe_screen()


# Global singleton
vision_service = VisionService()