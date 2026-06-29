"""WorkflowRunner — thực thi các tác vụ (Tasks) bằng cách gọi công cụ thích hợp.

Đóng vai trò là executor của từng node trong TaskGraph.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from runtime.events.event_types import EventType
from runtime.events.base_event import BaseEvent, uuid4
from runtime.eventbus.event_bus import event_bus
from runtime.state.state_store import state_store, CompanionState
from tools.registry import dispatch_tool

logger = logging.getLogger("ai-companion.planning.workflow")


class WorkflowRunner:
    """Thực thi các task trong TaskGraph thông qua Dispatch Tool."""

    def __init__(self, mcp_manager: Optional[Any] = None) -> None:
        self.mcp_manager = mcp_manager

    async def execute_task(self, task: Any) -> dict:
        """Thực thi một task cụ thể.

        Args:
            task: Đối tượng Task cần thực thi (phải có tool_name và arguments).

        Returns:
            dict kết quả thực thi công cụ.
        """
        correlation_id = uuid4()
        
        # 1. Chuyển trạng thái sang EXECUTING
        await state_store.transition(CompanionState.EXECUTING)

        # 2. Phát event bắt đầu chạy tool
        event_bus.publish(BaseEvent.create(
            event_type=EventType.TOOL_STARTED,
            source="workflow_runner",
            payload={"tool_name": task.tool_name, "arguments": task.arguments},
            correlation_id=correlation_id
        ))

        logger.info("Executing tool: %s with args: %s", task.tool_name, task.arguments)
        
        result = {}
        try:
            # 3. Thực thi tool thông qua registry
            result = await dispatch_tool(
                name=task.tool_name,
                args=task.arguments,
                mcp_manager=self.mcp_manager
            )
            
            success = result.get("success", True)
            if success:
                # 4. Thành công
                task.status = "COMPLETED"
                task.result = result
                
                event_bus.publish(BaseEvent.create(
                    event_type=EventType.TOOL_FINISHED,
                    source="workflow_runner",
                    payload={"tool_name": task.tool_name, "result": result, "success": True},
                    correlation_id=correlation_id
                ))
            else:
                # Thất bại
                error_msg = result.get("error", "Unknown error returned from tool")
                task.status = "FAILED"
                task.error = error_msg
                
                event_bus.publish(BaseEvent.create(
                    event_type=EventType.TOOL_FAILED,
                    source="workflow_runner",
                    payload={"tool_name": task.tool_name, "error": error_msg, "retry_count": 0},
                    correlation_id=correlation_id
                ))
                
            # Trigger learning_manager on task completion
            try:
                from learning.learning_manager import learning_manager
                learning_manager.process_task_outcome(
                    task_id=task.id,
                    success=success,
                    feedback=result.get("error") or "Task completed successfully"
                )
            except Exception as le:
                logger.warning("WorkflowRunner failed to trigger learning_manager: %s", le)
                
        except Exception as e:
            # 5. Exception xảy ra
            logger.error("Exception executing tool %s: %s", task.tool_name, e)
            task.status = "FAILED"
            task.error = str(e)
            result = {"success": False, "error": str(e)}

            event_bus.publish(BaseEvent.create(
                event_type=EventType.TOOL_FAILED,
                source="workflow_runner",
                payload={"tool_name": task.tool_name, "error": str(e), "retry_count": 0},
                correlation_id=correlation_id
            ))
            
            # Trigger learning_manager on exception failure
            try:
                from learning.learning_manager import learning_manager
                learning_manager.process_task_outcome(
                    task_id=task.id,
                    success=False,
                    feedback=str(e)
                )
            except Exception as le:
                logger.warning("WorkflowRunner failed to trigger learning_manager on error: %s", le)

        return result


# Global singleton
workflow_runner = WorkflowRunner()
