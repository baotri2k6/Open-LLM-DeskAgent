"""High-level screen context understanding."""

from __future__ import annotations

import logging
from tools.screen_reader import ocr_screenshot

logger = logging.getLogger("ai-companion.vision.understander")


class ScreenUnderstander:
    """High-level screen context understanding."""

    def __init__(self) -> None:
        pass

    def analyze_screen(self, query: str | None = None) -> dict:
        """Captures screen and sends to VLM (using the companion's default LLM/VLM service)
        to return a detailed summary of what is on screen and where key elements might be.
        """
        # 1. Chụp màn hình
        from tools.screen_reader import capture_screenshot
        shot = capture_screenshot()
        if not shot.get("success"):
            return {"success": False, "summary": "Failed to capture screenshot"}

        # 2. Phân tích nội dung qua LLMService/VLM
        try:
            from llm.manager import llm_service
            prompt = (
                "Bạn là một hệ thống phân tích giao diện màn hình máy tính (Screen Understander).\n"
                "Hãy phân tích ảnh chụp màn hình này và trả về kết quả dưới dạng JSON có cấu trúc sau:\n"
                "{\n"
                "  \"app_in_focus\": \"Tên ứng dụng đang hoạt động ở trung tâm\",\n"
                "  \"summary\": \"Tóm tắt những gì đang hiển thị trên màn hình\",\n"
                "  \"interactive_elements\": [\"danh sách các phần tử có thể nhấp chuột như nút bấm, ô nhập, menu\"]\n"
                "}"
            )
            if query:
                prompt += f"\nHướng dẫn phân tích đặc biệt: Hãy chú ý tìm kiếm phần tử '{query}'."

            reply = llm_service.chat(prompt, context={"image_base64": shot["png_base64"]})
            
            import json
            import re
            json_match = re.search(r"\{.*\}", reply, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {
                    "success": True,
                    "app_in_focus": data.get("app_in_focus", "unknown"),
                    "summary": data.get("summary", reply),
                    "interactive_elements": data.get("interactive_elements", []),
                }
            return {
                "success": True,
                "app_in_focus": "unknown",
                "summary": reply,
                "interactive_elements": []
            }
        except Exception as e:
            logger.error("ScreenUnderstander: Failed to analyze screen via VLM: %s", e)
            # Fallback to simple OCR text check
            from tools.screen_reader import ocr_screenshot
            ocr_res = ocr_screenshot()
            
            summary = "Active dashboard"
            text = ocr_res.get("text", "")
            if "code" in text.lower() or "def " in text:
                summary = "Developer Workspace (IDE)"
            elif "youtube" in text.lower():
                summary = "Video streaming platform"
                
            return {
                "success": True,
                "app_in_focus": "unknown",
                "summary": f"OCR Fallback: {summary}. Content: {text[:200]}",
                "interactive_elements": []
            }


# Global singleton
screen_understander = ScreenUnderstander()
