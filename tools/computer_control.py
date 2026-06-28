"""Computer control tools — mouse, keyboard, and shell execution."""

from __future__ import annotations

import os
import sys
import subprocess
import pyautogui

# Tắt chế độ fail-safe của pyautogui để tránh crash khi rê chuột sát góc màn hình
pyautogui.FAILSAFE = False


def mouse_click(x: int, y: int, button: str = "left", double_click: bool = False) -> dict:
    """Click chuột tại tọa độ x, y."""
    from execution.mouse.mouse_controller import mouse_controller
    return mouse_controller.click(x, y, button, double_click)


def mouse_move(x: int, y: int) -> dict:
    """Di chuyển chuột đến tọa độ x, y."""
    from execution.mouse.mouse_controller import mouse_controller
    return mouse_controller.move_to(x, y)


def mouse_scroll(clicks: int, direction: str = "down", x: int | None = None, y: int | None = None) -> dict:
    """Cuộn chuột lên hoặc xuống. direction: 'up' hoặc 'down'."""
    try:
        if x is not None and y is not None:
            from execution.mouse.mouse_controller import mouse_controller
            mouse_controller.move_to(x, y)
        
        amount = clicks if direction.lower() == "up" else -clicks
        pyautogui.scroll(amount)
        return {"success": True, "message": f"Scrolled {direction} by {clicks} clicks"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def mouse_drag(x: int, y: int, button: str = "left", duration: float = 0.5) -> dict:
    """Kéo thả chuột từ vị trí hiện tại đến tọa độ (x, y)."""
    from execution.mouse.mouse_controller import mouse_controller
    return mouse_controller.drag_to(x, y, button, duration)


def keyboard_type(text: str) -> dict:
    """Gõ chuỗi văn bản."""
    from execution.keyboard.keyboard_controller import keyboard_controller
    return keyboard_controller.type_text(text)


def keyboard_press(keys: str) -> dict:
    """Ấn một phím hoặc tổ hợp phím (ví dụ: 'ctrl+c', 'enter')."""
    from execution.keyboard.keyboard_controller import keyboard_controller
    return keyboard_controller.press_key(keys)


def execute_command(command: str) -> dict:
    """Chạy lệnh shell (cmd/powershell trên Windows, bash/sh trên Unix)."""
    try:
        # Sử dụng shell tương ứng của hệ điều hành
        use_shell = sys.platform == "win32"
        
        proc = subprocess.run(
            command,
            shell=use_shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        
        def decode_output(b: bytes) -> str:
            for enc in ("utf-8", "utf-16", "cp1252", "cp437", "ansi"):
                try:
                    return b.decode(enc)
                except UnicodeDecodeError:
                    continue
            return b.decode("utf-8", errors="replace")

        stdout = decode_output(proc.stdout)
        stderr = decode_output(proc.stderr)
        
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command execution timed out (60s)."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def click_element_by_vision(description: str, action_type: str = "click") -> dict:
    """
    Sử dụng thị giác máy tính (VLM) để định vị và tương tác với một phần tử trên màn hình dựa trên mô tả.
    Mô tả (description) ví dụ: 'Nút Đăng nhập màu xanh', 'Biểu tượng Google Chrome trên Desktop'.
    Hành động (action_type) có thể là: 'click' (click chuột trái), 'double_click' (click đúp), 'move' (di chuột đến).
    """
    import base64
    import io
    import json
    import re
    from PIL import Image
    
    try:
        # 1. Chụp ảnh màn hình hiện tại (sử dụng pyautogui với fallback mss)
        screenshot = None
        width, height = 0, 0
        try:
            screenshot = pyautogui.screenshot()
            width, height = screenshot.size
        except Exception:
            try:
                import mss
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    width, height = screenshot.size
            except Exception as e:
                return {"success": False, "error": f"Không thể chụp ảnh màn hình bằng cả pyautogui và mss. Lỗi: {str(e)}"}
        
        # Giảm kích thước ảnh nếu quá lớn để truyền nhận API nhanh hơn (max 1024px)
        max_size = 1024
        if max(width, height) > max_size:
            screenshot.thumbnail((max_size, max_size))
            
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # 2. Gọi VLM (Gemini hoặc OpenAI) để lấy tọa độ
        from llm.manager import LLMService
        from config.config import config
        
        llm_service = LLMService()
        provider = llm_service.provider
        api_key = llm_service.api_key
        model = llm_service.model
        base_url = llm_service.base_url
        
        vlm_provider = provider
        vlm_model = model
        vlm_api_key = api_key
        vlm_base_url = base_url
        
        # Fallback sang Gemini nếu mô hình hiện tại là local Ollama không hỗ trợ Vision
        if provider == "ollama":
            gemini_key = config.get("llm.gemini_api_key")
            if gemini_key:
                vlm_provider = "gemini"
                vlm_model = "gemini-2.5-flash"
                vlm_api_key = gemini_key
            else:
                return {
                    "success": False,
                    "error": "Tương tác thị giác (Vision Control) yêu cầu mô hình đa phương thức. Vui lòng cấu hình Gemini API Key."
                }
                
        prompt = (
            f"Bạn là một mô hình phân tích GUI thông minh.\n"
            f"Hãy phân tích ảnh chụp màn hình này và tìm vị trí chính xác của phần tử được mô tả: \"{description}\".\n"
            f"Hãy trả về kết quả dưới dạng JSON duy nhất có định dạng:\n"
            f'{{"x": <tọa độ X từ 0 đến 1000>, "y": <tọa độ Y từ 0 đến 1000>}}\n'
            f"Chú ý: 0,0 là góc trên bên trái, 1000,1000 là góc dưới bên phải màn hình. "
            f"Chỉ trả về đúng khối JSON, không viết lời giải thích nào khác."
        )
        
        # Chuẩn hóa tin nhắn
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }
        ]
        
        text_resp = ""
        try:
            provider_instance = None
            if vlm_provider == "gemini":
                from llm.providers.gemini import GeminiProvider
                provider_instance = GeminiProvider()
            elif vlm_provider in ["openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                from llm.providers.openai import OpenAIProvider
                provider_instance = OpenAIProvider()
            else:
                from llm.providers.ollama import OllamaProvider
                provider_instance = OllamaProvider()
            
            res = provider_instance.chat_with_tools(messages, vlm_api_key, vlm_model, vlm_base_url)
            text_resp = res.get("content", "") or ""
        except Exception as e:
            return {"success": False, "error": f"Failed to call VLM provider: {e}"}
            
        # Parse tọa độ
        m = re.search(r"(\{[\s\S]*?\})", text_resp)
        if m:
            coord = json.loads(m.group(1).strip())
            x_norm = float(coord.get("x", 500))
            y_norm = float(coord.get("y", 500))
            
            # Quy đổi tọa độ 0-1000 về độ phân giải thực của màn hình
            real_x = int((x_norm / 1000.0) * width)
            real_y = int((y_norm / 1000.0) * height)
            
            # Thực thi hành động chuột bằng pyautogui
            pyautogui.moveTo(real_x, real_y, duration=0.5)
            if action_type == "double_click":
                pyautogui.doubleClick()
            elif action_type == "move":
                pass
            else:
                pyautogui.click()
                
            return {
                "success": True,
                "message": f"Đã định vị thành công '{description}' tại tọa độ ({x_norm}, {y_norm}) -> Thực tế ({real_x}, {real_y}) và thực hiện '{action_type}'.",
                "coords": {"x": real_x, "y": real_y}
            }
        else:
            return {
                "success": False,
                "error": f"Không thể parse tọa độ JSON từ phản hồi của mô hình. Phản hồi: {text_resp}"
            }
            
    except Exception as e:
        return {"success": False, "error": f"Lỗi định vị thị giác: {str(e)}"}
