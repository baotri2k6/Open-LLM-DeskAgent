"""RiskAssessment — đánh giá mức độ rủi ro của các hành động.

Phân loại rủi ro (Low, Medium, High) cho từng loại cuộc gọi công cụ.
Giúp quyết định có cần yêu cầu phê duyệt trực tiếp của người dùng không.
"""

from __future__ import annotations

import logging
from typing import Dict, Union

logger = logging.getLogger("ai-companion.decision.risk")


class RiskAssessment:
    """Đánh giá mức độ rủi ro của các tác vụ."""

    def __init__(self) -> None:
        pass

    def assess(self, tool_name: str, arguments: dict) -> Dict[str, Union[str, bool]]:
        """Đánh giá rủi ro của tool call cụ thể.

        Returns:
            dict chứa risk_level ('low', 'medium', 'high') và is_dangerous.
        """
        # 1. Rủi ro cao (High Risk): Thực thi shell command hoặc thay đổi file hệ thống quan trọng
        if tool_name == "execute_command":
            cmd = arguments.get("command", "").lower().strip()
            # Lệnh xóa tệp hoặc format ổ đĩa
            if any(k in cmd for k in ["rm ", "del ", "format", "shutdown", "mkfs"]):
                return {"risk_level": "high", "is_dangerous": True, "reason": "Destructive shell command"}
            return {"risk_level": "high", "is_dangerous": False, "reason": "Shell execution"}

        # 2. Rủi ro trung bình (Medium Risk): Ghi tệp tin hoặc đổi cấu hình
        if tool_name in ("write_to_file", "skill_manage"):
            return {"risk_level": "medium", "is_dangerous": False, "reason": "Modifying files or skills"}

        # 3. Rủi ro thấp (Low Risk): Đọc thông tin, tra cứu google, chụp màn hình
        return {"risk_level": "low", "is_dangerous": False, "reason": "Information retrieval or read-only action"}


# Global singleton
risk_assessment = RiskAssessment()
