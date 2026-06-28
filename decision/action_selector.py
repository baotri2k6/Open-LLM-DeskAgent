"""ActionSelector — lựa chọn hành vi tối ưu cho companion.

Phối hợp giữa Intention, Priority, Risk và Policy để đưa ra quyết định hành động cuối cùng.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from decision.intention_manager import intention_manager
from decision.priority_manager import priority_manager
from decision.risk_assessment import risk_assessment
from decision.policy_engine import policy_engine

logger = logging.getLogger("ai-companion.decision.action_selector")


class ActionSelector:
    """Lựa chọn hành vi thực thi tối ưu."""

    def __init__(self) -> None:
        pass

    def evaluate_action(self, tool_name: str, arguments: dict, user_activity: str, idle_seconds: float) -> Dict[str, Any]:
        """Đánh giá xem có nên thực thi một cuộc gọi công cụ (action) không.

        Args:
            tool_name: Tên công cụ.
            arguments: Tham số.
            user_activity: Hoạt động hiện tại của user.
            idle_seconds: Thời gian user không hoạt động.

        Returns:
            dict chứa quyết định 'allow' (bool) và 'requires_approval' (bool).
        """
        # 1. Đánh giá rủi ro
        risk_info = risk_assessment.assess(tool_name, arguments)
        risk_level = risk_info["risk_level"]

        # 2. Kiểm tra chính sách im lặng nếu định tự động lên tiếng
        if tool_name == "proactive_nudge":
            allowed = policy_engine.check_silence_policy(user_activity, idle_seconds)
            return {
                "allow":             allowed,
                "requires_approval": False,
                "reason":            "Silence Policy evaluation"
            }

        # 3. Phân tích phân quyền
        requires_approval = False
        if risk_level == "high":
            requires_approval = True
        elif risk_level == "medium":
            # Tùy thuộc vào việc ghi file có thuộc workspace tin cậy không
            requires_approval = True

        return {
            "allow":             True,
            "requires_approval": requires_approval,
            "risk_level":        risk_level,
            "reason":            f"Risk level evaluated as {risk_level}"
        }


# Global singleton
action_selector = ActionSelector()
