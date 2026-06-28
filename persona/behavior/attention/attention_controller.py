"""AttentionController — điều khiển hướng nhìn mắt/đầu dựa trên hoạt động người dùng.

Tạo cảm giác companion đang thực sự chú ý đến những gì người dùng đang làm hoặc di chuyển chuột.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Tuple

logger = logging.getLogger("ai-companion.persona.behavior.attention")


class AttentionController:
    """Điều khiển hướng quay đầu và hướng nhìn mắt của Live2D avatar.

    Tính toán các tham số góc xoay đầu (Angle X, Y, Z) và vị trí nhãn cầu (EyeBall X, Y)
    dựa trên toạ độ chuột hoặc tiêu điểm chú ý trên màn hình.
    """

    def __init__(self) -> None:
        self._send_command: Optional[Callable] = None
        self._target_x: float = 0.0  # -1.0 (trái) đến 1.0 (phải)
        self._target_y: float = 0.0  # -1.0 (dưới) đến 1.0 (trên)
        self._attention_mode: str = "mouse"  # mouse | screen_center | fixed | idle

    def set_send_callback(self, callback: Callable) -> None:
        """Đăng ký callback gửi command đến WebSocket client."""
        self._send_command = callback

    def update_target(self, x: float, y: float) -> None:
        """Cập nhật toạ độ điểm chú ý.

        Toạ độ chuẩn hóa trong khoảng [-1.0, 1.0].
        """
        self._target_x = max(-1.0, min(1.0, x))
        self._target_y = max(-1.0, min(1.0, y))
        
        if self._attention_mode != "idle":
            self.apply_attention()

    def set_mode(self, mode: str) -> None:
        """Đặt chế độ chú ý: mouse, screen_center, fixed, idle."""
        if mode in ["mouse", "screen_center", "fixed", "idle"]:
            self._attention_mode = mode
            logger.debug("Attention mode changed to: %s", mode)
            if mode == "idle":
                self.reset_attention()
            elif mode == "screen_center":
                self.update_target(0.0, 0.0)

    def apply_attention(self) -> dict:
        """Tính toán các tham số Live2D và gửi lệnh xoay đầu/mắt.

        Returns:
            dict chứa Live2D parameters.
        """
        # Ánh xạ toạ độ target vào Live2D Parameter limits
        # Góc đầu di chuyển ít hơn mắt để tự nhiên
        head_x = self._target_x * 30.0  # ParamAngleX thường từ -30 đến 30
        head_y = self._target_y * 30.0  # ParamAngleY từ -30 đến 30
        head_z = self._target_x * self._target_y * -10.0 # Nghiêng đầu nhẹ
        
        eye_x = self._target_x * 1.0    # ParamEyeBallX từ -1.0 đến 1.0
        eye_y = self._target_y * 1.0    # ParamEyeBallY từ -1.0 đến 1.0

        params = {
            "ParamAngleX": round(head_x, 2),
            "ParamAngleY": round(head_y, 2),
            "ParamAngleZ": round(head_z, 2),
            "ParamEyeBallX": round(eye_x, 2),
            "ParamEyeBallY": round(eye_y, 2),
        }

        command = {
            "type": "attention",
            "mode": self._attention_mode,
            "params": params,
            "source": "attention_controller"
        }

        self._dispatch(command)
        return params

    def reset_attention(self) -> None:
        """Reset hướng nhìn về chính giữa."""
        self._target_x = 0.0
        self._target_y = 0.0
        params = {
            "ParamAngleX": 0.0,
            "ParamAngleY": 0.0,
            "ParamAngleZ": 0.0,
            "ParamEyeBallX": 0.0,
            "ParamEyeBallY": 0.0,
        }
        command = {
            "type": "attention",
            "mode": "reset",
            "params": params,
            "source": "attention_controller"
        }
        self._dispatch(command)

    def _dispatch(self, command: dict) -> None:
        if self._send_command:
            try:
                self._send_command(command)
            except Exception as e:
                logger.debug("Attention dispatch error: %s", e)


# Global singleton
attention_controller = AttentionController()
