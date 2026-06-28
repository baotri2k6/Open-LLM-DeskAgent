"""PlanningManager — điều phối lập kế hoạch và thực thi chuỗi công việc.

Quản lý chu trình: Đăng ký Goal -> Tạo TaskGraph (DAG) -> Lập lịch chạy qua TaskQueue & Scheduler.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID

from runtime.state.state_store import state_store, CompanionState
from planning.goal_manager.goal_registry import goal_registry, Goal
from planning.task_graph.task_graph import TaskGraph, Task
from planning.task_queue.task_queue import TaskQueue
from planning.scheduler.task_scheduler import TaskScheduler
from planning.workflow.workflow_runner import workflow_runner

logger = logging.getLogger("ai-companion.planning.manager")


class PlanningManager:
    """Điều phối cấp cao cho toàn bộ hệ thống lập kế hoạch và thực thi của agent."""

    def __init__(self) -> None:
        self._graphs: Dict[UUID, TaskGraph] = {}
        self._queue = TaskQueue()
        self._scheduler = TaskScheduler(max_concurrency=1)

    def create_plan(self, goal_description: str, priority: int = 3) -> Goal:
        """Tạo mục tiêu mới và khởi tạo đồ thị phụ thuộc rỗng."""
        goal = goal_registry.register_goal(goal_description, priority)
        
        # Khởi tạo đồ thị phụ thuộc
        graph = TaskGraph(goal_id=str(goal.id))
        self._graphs[goal.id] = graph
        
        return goal

    def get_task_graph(self, goal_id: UUID) -> TaskGraph | None:
        """Lấy đồ thị phụ thuộc của mục tiêu."""
        return self._graphs.get(goal_id)

    def add_task_to_plan(
        self,
        goal_id: UUID,
        task_id: str,
        description: str,
        dependencies: List[str] | None = None,
        tool_name: str = "",
        arguments: dict | None = None
    ) -> Task | None:
        """Thêm một task vào đồ thị của plan."""
        graph = self.get_task_graph(goal_id)
        if not graph:
            logger.warning("Failed to add task: Goal ID %s not found", goal_id)
            return None
        return graph.add_task(task_id, description, dependencies, tool_name, arguments)

    async def execute_plan(self, goal_id: UUID) -> bool:
        """Thực thi toàn bộ kế hoạch (plan) bất đồng bộ.

        Vòng lặp: Tìm task READY -> Đưa vào Queue -> Scheduler chạy -> Cập nhật trạng thái đồ thị.
        """
        graph = self.get_task_graph(goal_id)
        if not graph:
            return False

        goal = goal_registry.get_goal(goal_id)
        if goal:
            goal_registry.update_status(goal_id, "RUNNING")

        await state_store.transition(CompanionState.PLANNING)
        logger.info("Starting execution of plan: %s", goal.description if goal else str(goal_id))

        try:
            while not graph.is_completed() and not graph.is_failed():
                # 1. Tìm các task sẵn sàng từ đồ thị
                ready_tasks = graph.get_ready_tasks()
                
                # 2. Đưa các task READY chưa chạy vào Queue
                for task in ready_tasks:
                    if task.status == "READY":
                        # Push theo độ ưu tiên của Goal
                        priority = goal.priority if goal else 3
                        self._queue.push(task, priority)

                # 3. Kích hoạt Scheduler lập lịch chạy
                await self._scheduler.schedule(self._queue, workflow_runner.execute_task)

                # Chờ các task đang chạy hoàn thành
                await asyncio.sleep(0.5)

            # Chờ dọn dẹp các task chạy ngầm cuối cùng
            await self._scheduler.wait_all()

            # 4. Cập nhật kết quả cuối cùng của Goal
            if graph.is_completed():
                if goal:
                    goal_registry.update_status(goal_id, "COMPLETED")
                logger.info("Plan execution COMPLETED successfully for goal_id: %s", goal_id)
                await state_store.transition(CompanionState.IDLE)
                return True
            else:
                if goal:
                    goal_registry.update_status(goal_id, "FAILED")
                logger.error("Plan execution FAILED for goal_id: %s", goal_id)
                await state_store.transition(CompanionState.ERROR)
                return False

        except Exception as e:
            logger.error("Error during plan execution: %s", e)
            if goal:
                goal_registry.update_status(goal_id, "FAILED")
            await state_store.transition(CompanionState.ERROR)
            return False


# Global singleton
planning_manager = PlanningManager()
