"""Vision service — delegate to VisionAgent."""

from __future__ import annotations


class VisionService:
    async def describe_screen(self) -> dict:
        from tools.screen_reader import ocr_screenshot, capture_screenshot
        result = ocr_screenshot()
        if not result.get("success"):
            shot = capture_screenshot()
            if shot.get("success"):
                return {"success": True, "message": "Đã chụp màn hình nhưng OCR chưa sẵn sàng. Cài pytesseract để đọc chữ trên màn hình.", "screenshot_available": True}
            return {"success": False, "message": f"Loi: {result.get('error')}"}
        text = result.get("text", "").strip()
        if not text:
            return {"success": True, "message": "Màn hình không có chữ nào."}
        return {"success": True, "message": f"Trên màn hình:\n{text[:500]}"}