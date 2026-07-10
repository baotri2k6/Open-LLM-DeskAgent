"""TaskScheduler — bộ điều phối và lập lịch tác vụ.

Quản lý việc lấy các task sẵn sàng từ TaskQueue và chạy chúng
thông qua WorkflowRunner, kiểm soát concurrency limits (số task chạy đồng thời).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Dict, Optional

logger = logging.getLogger("ai-companion.planning.task_scheduler")


class TaskScheduler:
    """Điều phối lập lịch và chạy các task."""

    def __init__(self, max_concurrency: int = 1) -> None:
        self.max_concurrency = max_concurrency
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def schedule(
        self,
        task_queue: Any,
        runner_fn: Callable[[Any], Coroutine[Any, Any, None]]
    ) -> None:
        """Lập lịch và thực thi các task sẵn sàng trong hàng đợi.

        Lấy các task từ queue cho đến khi đạt max concurrency.
        """
        while len(self._active_tasks) < self.max_concurrency and not task_queue.is_empty():
            task = task_queue.pop()
            if not task:
                break
                
            logger.info("Scheduling task: %s (%s)", task.id, task.description)
            
            # Đánh dấu đang chạy
            task.status = "RUNNING"
            
            # Chạy async task
            async_task = asyncio.create_task(self._run_task_wrapper(task, runner_fn))
            self._active_tasks[task.id] = async_task

    async def _run_task_wrapper(self, task: Any, runner_fn: Callable) -> None:
        """Wrapper chạy task và dọn dẹp sau khi xong."""
        try:
            await runner_fn(task)
        except Exception as e:
            logger.error("Error executing task %s in scheduler: %s", task.id, e)
            task.status = "FAILED"
            task.error = str(e)
        finally:
            # Xóa khỏi active list khi chạy xong (thành công hoặc lỗi)
            if task.id in self._active_tasks:
                del self._active_tasks[task.id]
                logger.debug("Task removed from active scheduler registry: %s", task.id)

    def cancel_task(self, task_id: str) -> bool:
        """Hủy một task đang chạy."""
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()
            del self._active_tasks[task_id]
            logger.info("Cancelled running task: %s", task_id)
            return True
        return False

    def has_running_tasks(self) -> bool:
        """Có task nào đang chạy không?"""
        return len(self._active_tasks) > 0

    async def wait_all(self) -> None:
        """Chờ tất cả các task đang chạy hoàn thành."""
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
            self._active_tasks.clear()
