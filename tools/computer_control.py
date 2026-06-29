"""Computer control tools — mouse, keyboard, and shell execution."""

from __future__ import annotations

import os
import sys
import subprocess
import pyautogui
import logging

# Tắt chế độ fail-safe của pyautogui để tránh crash khi rê chuột sát góc màn hình
pyautogui.FAILSAFE = False
logger = logging.getLogger("ai-companion.tools.computer_control")


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


async def click_element_by_vision(description: str, action_type: str = "click") -> dict:
    """
    Sử dụng thị giác máy tính (VLM) để định vị và tương tác với một phần tử trên màn hình dựa trên mô tả.
    Mô tả (description) ví dụ: 'Nút Đăng nhập màu xanh', 'Biểu tượng Google Chrome trên Desktop'.
    Hành động (action_type) có thể là: 'click' (click chuột trái), 'double_click' (click đúp), 'move' (di chuột đến).
    """
    try:
        # 1. Gọi bộ máy phân tích/hiểu màn hình (ScreenUnderstander) trước để lấy context và danh sách phần tử
        from vision.screen_understanding.screen_understander import screen_understander
        analysis = await screen_understander.analyze_screen(query=description)
        logger.info("Screen understanding summary: %s", analysis.get("summary", ""))

        # 2. Sử dụng GroundingEngine để tìm tọa độ dựa trên OCR/VLM
        from vision.grounding.grounding_engine import grounding_engine
        coords = await grounding_engine.ground(description)
        if not coords:
            return {
                "success": False,
                "error": f"Không tìm thấy tọa độ cho phần tử mô tả: '{description}' qua GroundingEngine."
            }

        real_x, real_y = coords

        # 3. Thực thi hành động chuột bằng pyautogui
        pyautogui.moveTo(real_x, real_y, duration=0.5)
        if action_type == "double_click":
            pyautogui.doubleClick()
        elif action_type == "move":
            pass
        else:
            pyautogui.click()

        return {
            "success": True,
            "message": f"Đã định vị thành công '{description}' tại tọa độ thực tế ({real_x}, {real_y}) và thực hiện '{action_type}'.",
            "coords": {"x": real_x, "y": real_y},
            "screen_analysis": analysis
        }

    except Exception as e:
        return {"success": False, "error": f"Lỗi định vị thị giác: {str(e)}"}
