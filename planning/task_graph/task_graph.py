"""TaskGraph — đồ thị phụ thuộc của các tác vụ (DAG - Directed Acyclic Graph).

Cho phép mô hình hóa một chuỗi các công việc cần thực hiện để đạt được goal lớn.
Mỗi node là một Task, mỗi cạnh đại diện cho sự phụ thuộc (task A phải xong trước task B).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger("ai-companion.planning.task_graph")


@dataclass
class Task:
    """Một nút tác vụ trong TaskGraph."""
    id:           str
    description:  str
    dependencies: Set[str] = field(default_factory=set)  # Danh sách ID các task phải xong trước
    status:       str = "PENDING"  # PENDING | READY | RUNNING | COMPLETED | FAILED
    tool_name:    str = ""         # Tên công cụ sẽ chạy (nếu có)
    arguments:    dict = field(default_factory=dict)
    result:       dict = field(default_factory=dict)
    error:        str = ""


class TaskGraph:
    """Quản lý cấu trúc đồ thị tác vụ phụ thuộc DAG."""

    def __init__(self, goal_id: str = "") -> None:
        self.goal_id = goal_id
        self._tasks: Dict[str, Task] = {}

    def add_task(
        self,
        task_id: str,
        description: str,
        dependencies: List[str] | Set[str] | None = None,
        tool_name: str = "",
        arguments: dict | None = None
    ) -> Task:
        """Thêm một task vào đồ thị."""
        dep_set = set(dependencies) if dependencies else set()
        task = Task(
            id=task_id,
            description=description,
            dependencies=dep_set,
            tool_name=tool_name,
            arguments=arguments or {}
        )
        self._tasks[task_id] = task
        logger.debug("Task added to graph: %s (depends on: %s)", task_id, dep_set)
        
        # Cập nhật trạng thái READY nếu không có dependency
        if not dep_set:
            task.status = "READY"
            
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Lấy thông tin task theo ID."""
        return self._tasks.get(task_id)

    def get_ready_tasks(self) -> List[Task]:
        """Lấy danh sách các task đã sẵn sàng thực thi.

        Task READY là task có trạng thái READY hoặc PENDING nhưng
        tất cả các task phụ thuộc đã ở trạng thái COMPLETED.
        """
        ready = []
        for task in self._tasks.values():
            if task.status == "READY":
                ready.append(task)
            elif task.status == "PENDING":
                # Kiểm tra xem toàn bộ các task phụ thuộc đã COMPLETED chưa
                deps_met = True
                for dep_id in task.dependencies:
                    dep_task = self._tasks.get(dep_id)
                    if not dep_task or dep_task.status != "COMPLETED":
                        deps_met = False
                        break
                
                if deps_met:
                    task.status = "READY"
                    ready.append(task)
        return ready

    def mark_completed(self, task_id: str, result: dict | None = None) -> None:
        """Đánh dấu task đã hoàn thành thành công."""
        task = self.get_task(task_id)
        if task:
            task.status = "COMPLETED"
            task.result = result or {}
            logger.info("Task COMPLETED: %s", task_id)
            
            # Cập nhật các task con phụ thuộc vào nó
            self._update_dependent_tasks()

    def mark_failed(self, task_id: str, error: str) -> None:
        """Đánh dấu task thất bại."""
        task = self.get_task(task_id)
        if task:
            task.status = "FAILED"
            task.error = error
            logger.error("Task FAILED: %s (Error: %s)", task_id, error)

    def _update_dependent_tasks(self) -> None:
        """Cập nhật các task PENDING thành READY nếu mọi dependency đã xong."""
        for task in self._tasks.values():
            if task.status == "PENDING":
                deps_met = True
                for dep_id in task.dependencies:
                    dep_task = self._tasks.get(dep_id)
                    if not dep_task or dep_task.status != "COMPLETED":
                        deps_met = False
                        break
                if deps_met:
                    task.status = "READY"

    def is_completed(self) -> bool:
        """Kiểm tra toàn bộ đồ thị đã hoàn thành chưa."""
        if not self._tasks:
            return False
        return all(t.status == "COMPLETED" for t in self._tasks.values())

    def is_failed(self) -> bool:
        """Kiểm tra xem có task nào bị FAILED mà làm tắc nghẽn luồng không."""
        return any(t.status == "FAILED" for t in self._tasks.values())

    def get_progress(self) -> float:
        """Trả về tiến độ hoàn thành (từ 0.0 đến 1.0)."""
        if not self._tasks:
            return 0.0
        completed = sum(1 for t in self._tasks.values() if t.status == "COMPLETED")
        return completed / len(self._tasks)

    def __repr__(self) -> str:
        return f"TaskGraph(goal_id={self.goal_id}, tasks={len(self._tasks)})"
