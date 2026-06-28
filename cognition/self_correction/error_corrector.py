"""ErrorCorrector — phát hiện lỗi thực thi hoặc chất lượng kém và sinh prompt tự sửa lỗi (Self-Correction).

Giúp agent tự sửa chữa hành vi khi một tool bị lỗi hoặc đầu ra không đạt chất lượng.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger("ai-companion.cognition.self_correction")


class ErrorCorrector:
    """Tự động phát hiện lỗi và xây dựng prompt điều chỉnh hành vi."""

    def __init__(self) -> None:
        self._retry_counts: Dict[str, int] = {}
        self.max_retries = 2

    def get_retry_count(self, action_name: str) -> int:
        """Lấy số lần đã thử lại của action."""
        return self._retry_counts.get(action_name, 0)

    def should_retry(self, action_name: str) -> bool:
        """Kiểm tra có nên tiếp tục thử lại không."""
        return self.get_retry_count(action_name) < self.max_retries

    def increment_retry(self, action_name: str) -> int:
        """Tăng số lần thử lại."""
        self._retry_counts[action_name] = self.get_retry_count(action_name) + 1
        return self._retry_counts[action_name]

    def reset(self, action_name: str) -> None:
        """Reset bộ đếm thử lại."""
        if action_name in self._retry_counts:
            del self._retry_counts[action_name]

    def build_correction_prompt(self, failed_tool: str, error_msg: str) -> str:
        """Tạo prompt chỉ thị LLM tự sửa lỗi sau khi gọi tool thất bại.

        Args:
            failed_tool: Tên công cụ bị lỗi.
            error_msg: Thông điệp lỗi hệ thống trả về.
        """
        logger.info("Building error correction prompt for tool: %s", failed_tool)
        
        prompt = (
            f"[HỆ THỐNG] Cuộc gọi công cụ `{failed_tool}` đã thất bại với lỗi sau:\n"
            f"Error: {error_msg}\n\n"
            f"Vui lòng phân tích lỗi này. Bạn có thể:\n"
            f"1. Điều chỉnh tham số đầu vào và thử lại nếu do tham số sai.\n"
            f"2. Sử dụng một công cụ thay thế khác phù hợp hơn.\n"
            f"3. Báo cáo lại cho người dùng lý do thất bại nếu lỗi do môi trường và không thể tự sửa."
        )
        return prompt


# Global singleton
error_corrector = ErrorCorrector()
