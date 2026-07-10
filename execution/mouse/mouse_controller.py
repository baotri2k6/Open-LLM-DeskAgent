"""MouseController — mô phỏng các thao tác di chuyển và click chuột.

Cung cấp lớp bọc an toàn xung quanh pyautogui để điều khiển chuột.
"""

from __future__ import annotations

import logging
from typing import Dict, Union, Any

logger = logging.getLogger("ai-companion.execution.mouse")


class MouseController:
    """Điều khiển chuột hệ thống có kiểm soát an toàn."""

    def __init__(self) -> None:
        self._screen_width = None
        self._screen_height = None

    @property
    def screen_width(self) -> int:
        if self._screen_width is None:
            self._init_screen_size()
        return self._screen_width

    @property
    def screen_height(self) -> int:
        if self._screen_height is None:
            self._init_screen_size()
        return self._screen_height

    def _init_screen_size(self):
        try:
            import pyautogui
            w, h = pyautogui.size()
            self._screen_width = w
            self._screen_height = h
            logger.info("MouseController screen size resolved: %dx%d", w, h)
        except Exception:
            # Fallback to standard Full HD if headless/no display
            self._screen_width = 1920
            self._screen_height = 1080
            logger.info("MouseController fallback screen size: 1920x1080")

    def validate_coordinates(self, x: Union[int, str], y: Union[int, str]) -> tuple[int, int]:
        """Kiểm tra và chuẩn hóa tọa độ chuột nằm trong màn hình.

        Hỗ trợ chuyển đổi chuỗi số sang số nguyên.
        """
        try:
            val_x = int(x)
            val_y = int(y)
        except (ValueError, TypeError):
            logger.warning("Invalid coordinate types: x=%s, y=%s. Fallback to center.", x, y)
            val_x = self.screen_width // 2
            val_y = self.screen_height // 2

        # Giới hạn tọa độ trong màn hình tránh lỗi di chuyển
        val_x = max(0, min(self.screen_width - 1, val_x))
        val_y = max(0, min(self.screen_height - 1, val_y))
        
        return val_x, val_y

    def click(self, x: Union[int, str], y: Union[int, str], button: str = "left", double_click: bool = False) -> Dict[str, Any]:
        """Click chuột tại vị trí (x, y)."""
        val_x, val_y = self.validate_coordinates(x, y)
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.moveTo(val_x, val_y, duration=0.3)
            if double_click:
                pyautogui.doubleClick(button=button)
            else:
                pyautogui.click(button=button)
            logger.info("Mouse click %s at (%d, %d)", button, val_x, val_y)
            return {"success": True, "message": f"Clicked {button} at ({val_x}, {val_y})"}
        except Exception as e:
            logger.error("Failed to click mouse: %s", e)
            return {"success": False, "error": str(e)}

    def move_to(self, x: Union[int, str], y: Union[int, str]) -> Dict[str, Any]:
        """Rê chuột đến vị trí (x, y)."""
        val_x, val_y = self.validate_coordinates(x, y)
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.moveTo(val_x, val_y, duration=0.3)
            logger.debug("Mouse moved to (%d, %d)", val_x, val_y)
            return {"success": True, "message": f"Moved mouse to ({val_x}, {val_y})"}
        except Exception as e:
            logger.error("Failed to move mouse: %s", e)
            return {"success": False, "error": str(e)}

    def drag_to(self, x: Union[int, str], y: Union[int, str], button: str = "left", duration: float = 0.5) -> Dict[str, Any]:
        """Kéo thả chuột đến vị trí (x, y)."""
        val_x, val_y = self.validate_coordinates(x, y)
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.dragTo(val_x, val_y, duration=duration, button=button)
            logger.info("Mouse drag %s to (%d, %d)", button, val_x, val_y)
            return {"success": True, "message": f"Dragged mouse to ({val_x}, {val_y})"}
        except Exception as e:
            logger.error("Failed to drag mouse: %s", e)
            return {"success": False, "error": str(e)}


# Global singleton
mouse_controller = MouseController()
