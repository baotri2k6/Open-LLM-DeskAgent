"""Vision agent — chụp màn hình, OCR, mô tả nội dung."""

from __future__ import annotations

from tools.screen_reader import capture_screenshot, ocr_screenshot


class VisionAgent:
    async def describe_screen(self) -> dict:
        """Chụp màn hình và mô tả nội dung bằng mô hình đa phương thức (nếu có) hoặc OCR."""
        try:
            from vision.screen_understanding.screen_understander import screen_understander
            res = await screen_understander.analyze_screen()
            if res.get("success"):
                return {
                    "success": True,
                    "message": res.get("summary", ""),
                    "app_in_focus": res.get("app_in_focus", "unknown"),
                    "interactive_elements": res.get("interactive_elements", []),
                    "screenshot_available": True
                }
        except Exception:
            pass
            
        # Fallback to old OCR if screen_understander fails
        from tools.screen_reader import ocr_screenshot
        result = ocr_screenshot()
        if not result.get("success"):
            return {
                "success": True,
                "message": "Đã chụp màn hình nhưng chưa mô tả được nội dung (OCR chưa được thiết lập và mô hình không hỗ trợ đa phương thức).",
                "screenshot_available": True,
            }

        text = result.get("text", "").strip()
        if not text:
            return {"success": True, "message": "Màn hình không có chữ nào (hoặc là hình ảnh thuần túy)."}

        # tóm gọn nếu quá dài
        preview = text[:500] + ("..." if len(text) > 500 else "")
        return {
            "success": True,
            "message": f"Trên màn hình mình thấy (qua OCR):\n{preview}",
            "full_text": text,
        }

    async def capture(self) -> dict:
        from tools.screen_reader import capture_screenshot
        return capture_screenshot()