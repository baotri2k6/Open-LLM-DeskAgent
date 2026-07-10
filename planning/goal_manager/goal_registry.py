"""GoalRegistry — quản lý danh sách mục tiêu cấp cao (High-Level Goals).

Cho phép đăng ký, cập nhật và truy vấn trạng thái các mục tiêu của companion.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4

logger = logging.getLogger("ai-companion.planning.goal_registry")


@dataclass
class Goal:
    """Định nghĩa một mục tiêu cấp cao."""
    id:          UUID = field(default_factory=uuid4)
    description: str = ""
    priority:    int = 3  # 1 = Critical, 5 = Low
    status:      str = "PENDING"  # PENDING | RUNNING | COMPLETED | FAILED
    created_at:  float = field(default_factory=time.time)
    updated_at:  float = field(default_factory=time.time)
    metadata:    dict = field(default_factory=dict)


class GoalRegistry:
    """Đăng ký và lưu trữ trạng thái các mục tiêu."""

    def __init__(self) -> None:
        self._goals: dict[UUID, Goal] = {}

    def register_goal(self, description: str, priority: int = 3, metadata: dict | None = None) -> Goal:
        """Đăng ký một mục tiêu mới."""
        goal = Goal(
            description=description,
            priority=priority,
            metadata=metadata or {}
        )
        self._goals[goal.id] = goal
        logger.info("Goal registered: %s (Priority=%d, ID=%s)", description, priority, str(goal.id)[:8])
        return goal

    def get_goal(self, goal_id: UUID) -> Goal | None:
        """Lấy mục tiêu theo ID."""
        return self._goals.get(goal_id)

    def update_status(self, goal_id: UUID, status: str) -> bool:
        """Cập nhật trạng thái của mục tiêu."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False
        
        goal.status = status
        goal.updated_at = time.time()
        logger.info("Goal %s status updated to: %s", str(goal_id)[:8], status)
        
        # Trigger event nếu hoàn thành
        if status == "COMPLETED":
            try:
                from runtime.events.event_types import EventType
                from runtime.events.base_event import BaseEvent
                from runtime.eventbus.event_bus import event_bus
                event_bus.publish(BaseEvent.create(
                    event_type=EventType.GOAL_COMPLETED,
                    source="goal_registry",
                    payload={"goal_id": str(goal_id), "description": goal.description}
                ))
            except Exception:
                pass
                
        return True

    def get_active_goals(self) -> list[Goal]:
        """Lấy danh sách các mục tiêu chưa hoàn thành."""
        return [g for g in self._goals.values() if g.status in ("PENDING", "RUNNING")]

    def list_all_goals(self) -> list[Goal]:
        """Liệt kê tất cả mục tiêu."""
        return list(self._goals.values())


# Global singleton
goal_registry = GoalRegistry()
