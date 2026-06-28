"""KeyboardController — mô phỏng các thao tác gõ phím và phím tắt.

Cung cấp lớp bọc an toàn xung quanh pyautogui để mô phỏng nhập liệu bàn phím.
"""

from __future__ import annotations

import logging
from typing import Dict

import pyautogui

logger = logging.getLogger("ai-companion.execution.keyboard")


class KeyboardController:
    """Mô phỏng nhập liệu từ bàn phím hệ thống."""

    def __init__(self) -> None:
        pass

    def type_text(self, text: str) -> Dict[str, Any]:
        """Gõ chuỗi văn bản."""
        if not text:
            return {"success": False, "error": "Empty text"}
        try:
            # interval = thời gian nghỉ giữa các phím tạo cảm giác gõ thật
            pyautogui.write(text, interval=0.01)
            logger.info("Keyboard typed text: '%s'", text[:50] + "..." if len(text) > 50 else text)
            return {"success": True, "message": f"Typed {len(text)} characters"}
        except Exception as e:
            logger.error("Failed to type text: %s", e)
            return {"success": False, "error": str(e)}

    def press_key(self, keys: str) -> Dict[str, Any]:
        """Bấm một phím hoặc tổ hợp phím tắt (ví dụ: 'ctrl+c', 'enter', 'tab')."""
        if not keys:
            return {"success": False, "error": "Empty key combination"}
        
        try:
            keys_lower = keys.lower().strip()
            # Nếu là tổ hợp phím tắt dạng kết hợp bởi dấu '+' hoặc '-'
            if "+" in keys_lower or "-" in keys_lower:
                separator = "+" if "+" in keys_lower else "-"
                parts = [p.strip() for p in keys_lower.split(separator)]
                
                # Bấm giữ các phím bổ trợ (ctrl, alt, shift) rồi nhấn phím chính
                pyautogui.hotkey(*parts)
                logger.info("Keyboard pressed shortcut: %s", keys_lower)
            else:
                pyautogui.press(keys_lower)
                logger.debug("Keyboard pressed key: %s", keys_lower)

            return {"success": True, "message": f"Pressed key(s): {keys_lower}"}
        except Exception as e:
            logger.error("Failed to press key %s: %s", keys, e)
            return {"success": False, "error": str(e)}


# Global singleton
keyboard_controller = KeyboardController()
