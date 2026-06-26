"""Vision agent — chụp màn hình, OCR, mô tả nội dung."""

from __future__ import annotations

from tools.screen_reader import capture_screenshot, ocr_screenshot


class VisionAgent:
    async def describe_screen(self) -> dict:
        """Chụp màn hình và mô tả nội dung bằng mô hình đa phương thức (nếu có) hoặc OCR."""
        from tools.screen_reader import capture_screenshot
        shot = capture_screenshot()
        if not shot.get("success"):
            return {"success": False, "message": f"Không chụp được màn hình: {shot.get('error')}"}
            
        b64_data = shot.get("png_base64")
        
        # Kiểm tra xem mô hình hiện tại có hỗ trợ đa phương thức không
        from llm.manager import LLMService, _get_llm_credentials, _is_multimodal_model
        try:
            provider, api_key, model, base_url = _get_llm_credentials()
            if _is_multimodal_model(provider, model):
                llm = LLMService()
                prompt = [
                    {
                        "type": "text", 
                        "text": "Hãy nhìn vào bức ảnh chụp màn hình này và mô tả ngắn gọn, súc tích bằng tiếng Việt những gì đang hiển thị trên màn hình của người dùng (ví dụ: đang mở ứng dụng gì, có nội dung/cửa sổ nào nổi bật)."
                    },
                    {
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/png;base64,{b64_data}"}
                    }
                ]
                response = await llm.chat(prompt)
                if response and response.strip():
                    return {
                        "success": True,
                        "message": f"Trên màn hình mình thấy:\n{response.strip()}",
                        "screenshot_available": True
                    }
        except Exception as e:
            # Fallback to OCR if multimodal call fails
            pass
            
        # Chạy OCR làm fallback
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