"""Vision service — delegate to VisionAgent."""

from __future__ import annotations


class VisionService:
    async def describe_screen(self) -> dict:
        from tools.screen_reader import ocr_screenshot, capture_screenshot
        result = ocr_screenshot()
        if not result.get("success"):
            shot = capture_screenshot()
            if shot.get("success"):
                return {"success": True, "message": "Da chup man hinh nhung OCR chua san sang."}
            return {"success": False, "message": f"Loi: {result.get('error')}"}
        text = result.get("text", "").strip()
        if not text:
            return {"success": True, "message": "Man hinh khong co chu nao."}
        return {"success": True, "message": f"Tren man hinh:\n{text[:500]}"}