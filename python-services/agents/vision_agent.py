"""Vision agent — chụp màn hình, OCR, mô tả nội dung."""

from __future__ import annotations

from tools.screen_reader import capture_screenshot, ocr_screenshot


class VisionAgent:
    async def describe_screen(self) -> dict:
        """Chụp màn hình và OCR để mô tả nội dung."""
        result = ocr_screenshot()
        if not result.get("success"):
            err = result.get("error", "unknown")
            # thử chỉ chụp (không OCR) nếu pytesseract chưa cài
            shot = capture_screenshot()
            if shot.get("success"):
                return {
                    "success": True,
                    "message": "Da chup man hinh nhung OCR chua san sang. Cai pytesseract de doc chu tren man hinh.",
                    "screenshot_available": True,
                }
            return {"success": False, "message": f"Khong chup duoc man hinh: {err}"}

        text = result.get("text", "").strip()
        if not text:
            return {"success": True, "message": "Man hinh khong co chu nao (hoac la hinh anh thuan tuy)."}

        # tóm gọn nếu quá dài
        preview = text[:500] + ("..." if len(text) > 500 else "")
        return {
            "success": True,
            "message": f"Tren man hinh minh thay:\n{preview}",
            "full_text": text,
        }

    async def capture(self) -> dict:
        return capture_screenshot()