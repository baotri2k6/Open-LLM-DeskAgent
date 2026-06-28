"""High-level screen context understanding."""

from __future__ import annotations

import logging
from tools.screen_reader import ocr_screenshot

logger = logging.getLogger("ai-companion.vision.understander")


class ScreenUnderstander:
    """High-level screen context understanding."""

    def __init__(self) -> None:
        pass

    def analyze_screen(self) -> dict:
        """Capture screenshot and summarize current active screen elements."""
        res = ocr_screenshot()
        if not res.get("success"):
            return {"success": False, "summary": "Failed to OCR screen"}
            
        text = res.get("text", "")
        # Simple analysis
        summary = "Active dashboard"
        if "code" in text.lower() or "def " in text:
            summary = "Developer Workspace (IDE)"
        elif "youtube" in text.lower():
            summary = "Video streaming platform"
            
        return {
            "success": True,
            "summary": summary,
            "size": res.get("size")
        }


# Global singleton
screen_understander = ScreenUnderstander()
