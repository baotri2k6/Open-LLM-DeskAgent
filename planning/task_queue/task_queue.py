"""TaskQueue — hàng đợi ưu tiên của các tác vụ sẵn sàng chạy (Priority Queue).

Quản lý các task đang ở trạng thái READY và chờ thực thi.
Sắp xếp theo độ ưu tiên: CRITICAL (1) -> IDLE (5).
"""

from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ai-companion.planning.task_queue")


@dataclass(order=True)
class QueueItem:
    """Đối tượng lưu trữ trong hàng đợi ưu tiên."""
    priority: int
    task_id:  str = field(compare=False)
    task:     Any = field(compare=False)


class TaskQueue:
    """Hàng đợi tác vụ ưu tiên dựa trên Min-Heap."""

    def __init__(self) -> None:
        self._queue: list[QueueItem] = []
        self._task_ids: set[str] = set()

    def push(self, task: Any, priority: int = 3) -> bool:
        """Thêm tác vụ vào hàng đợi.

        Args:
            task: Đối tượng Task cần đưa vào.
            priority: Độ ưu tiên (1 = Cao nhất, 5 = Thấp nhất).

        Returns:
            True nếu thêm thành công, False nếu task đã tồn tại trong hàng đợi.
        """
        if task.id in self._task_ids:
            return False

        item = QueueItem(priority=priority, task_id=task.id, task=task)
        heapq.heappush(self._queue, item)
        self._task_ids.add(task.id)
        
        logger.debug("Task pushed to queue: %s (Priority=%d)", task.id, priority)
        return True

    def pop(self) -> Any | None:
        """Lấy tác vụ có độ ưu tiên cao nhất ra khỏi hàng đợi."""
        if not self._queue:
            return None

        item = heapq.heappop(self._queue)
        self._task_ids.remove(item.task_id)
        
        logger.debug("Task popped from queue: %s", item.task_id)
        return item.task

    def peek(self) -> Any | None:
        """Xem tác vụ đầu tiên không lấy ra."""
        if not self._queue:
            return None
        return self._queue[0].task

    def remove(self, task_id: str) -> bool:
        """Xóa một task khỏi hàng đợi."""
        if task_id not in self._task_ids:
            return False

        self._queue = [item for item in self._queue if item.task_id != task_id]
        heapq.heapify(self._queue)
        self._task_ids.remove(task_id)
        return True

    @property
    def size(self) -> int:
        """Kích thước hàng đợi."""
        return len(self._queue)

    def is_empty(self) -> bool:
        """Hàng đợi rỗng?"""
        return len(self._queue) == 0

    def clear(self) -> None:
        """Xóa sạch hàng đợi."""
        self._queue.clear()
        self._task_ids.clear()
