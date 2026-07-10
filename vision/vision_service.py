"""Vision service — delegate to VisionAgent and perform screen caching."""

from __future__ import annotations

import logging
from agents.vision.vision_agent import VisionAgent
from tools.screen_reader import capture_screenshot

logger = logging.getLogger("ai-companion.vision.service")


class VisionService:
    """Orchestrates screen capture caching, variance checks, and delegates queries to VisionAgent."""

    def __init__(self) -> None:
        self.agent = VisionAgent()
        self._last_screenshot_hash: int | None = None
        self._cached_description: dict | None = None

    async def describe_screen(self, force: bool = False) -> dict:
        """Describe the screen, utilizing cache if screen variance is low."""
        shot = capture_screenshot()
        if not shot.get("success"):
            return {"success": False, "message": "Failed to capture screenshot."}
            
        img_data = shot.get("png_base64", "")
        img_hash = hash(img_data)
        
        if not force and self._last_screenshot_hash == img_hash and self._cached_description:
            logger.info("VisionService: Screen unchanged. Returning cached description.")
            return self._cached_description

        # Delegate to agent
        desc = await self.agent.describe_screen()
        self._last_screenshot_hash = img_hash
        self._cached_description = desc
        return desc

    def describe_element_at(self, x: int, y: int) -> dict:
        """Find and describe UI element at specific screen coordinates."""
        from vision.detector.object_detector import object_detector
        detected = object_detector.detect()
        if not detected.get("success"):
            return {"success": False, "message": "Detector failed"}
            
        for el in detected.get("elements", []):
            bbox = el.get("bbox", {})
            left = bbox.get("x", 0)
            top = bbox.get("y", 0)
            width = bbox.get("width", 0)
            height = bbox.get("height", 0)
            
            if left <= x <= left + width and top <= y <= top + height:
                return {
                    "success": True,
                    "element": el,
                    "message": f"Found element: '{el.get('text')}' at ({x}, {y})"
                }
                
        return {"success": False, "message": f"No element found at ({x}, {y})"}


# Global singleton
vision_service = VisionService()