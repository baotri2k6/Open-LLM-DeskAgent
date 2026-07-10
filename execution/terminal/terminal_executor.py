"""TerminalExecutor — thực thi các lệnh shell hệ thống an toàn.

Tất cả các lệnh thực thi đều được kiểm duyệt qua PermissionManager.
Yêu cầu sự phê duyệt từ người dùng (Human-in-the-loop) nếu là lệnh nguy hại.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from execution.approval.approval_registry import PermissionManager, wait_for_approval
from execution.sandbox.sandbox_runner import sandbox_runner

logger = logging.getLogger("ai-companion.execution.terminal")


class TerminalExecutor:
    """Thực thi shell command có kiểm soát phê duyệt an toàn."""

    def __init__(self) -> None:
        pass

    async def execute(self, command: str, timeout: float = 60.0, cwd: str = "") -> Dict[str, Any]:
        """Thực thi câu lệnh command line.

        Args:
            command: Câu lệnh shell (ví dụ: 'npm run test').
            timeout: Thời gian tối đa chờ lệnh hoàn thành.
        """
        command = command.strip()
        if not command:
            return {"success": False, "error": "Empty command"}

        inspection = sandbox_runner.inspect(command)
        if not inspection.get("success"):
            return {"success": False, "error": inspection.get("error", "Command blocked"), "blocked": True}

        # 1. Kiểm tra phân quyền, whitelist sandbox và phê duyệt qua PermissionManager
        args = {"command": command}
        needs_approval = (
            PermissionManager.requires_approval("execute_command", args)
            or bool(inspection.get("requires_approval"))
        )
        approved_unlisted = False
        if needs_approval:
            req_id = f"cmd_{uuid.uuid4().hex[:8]}"
            logger.info("Command '%s' requires human approval (req_id: %s)", command, req_id)
            
            # Gửi tín hiệu yêu cầu phê duyệt thông qua EventBus
            try:
                from runtime.events.event_types import EventType
                from runtime.events.base_event import BaseEvent
                from runtime.eventbus.event_bus import event_bus
                event_bus.publish(BaseEvent.create(
                    event_type=EventType.APPROVAL_REQUESTED,
                    source="terminal_executor",
                    payload={"req_id": req_id, "action": f"Execute Command: {command}"}
                ))
            except Exception:
                pass

            # Chờ quyết định của user (bất đồng bộ)
            approved = await wait_for_approval(req_id, timeout=120.0)
            
            if not approved:
                logger.warning("Execution DENIED by user for command: '%s'", command)
                
                try:
                    event_bus.publish(BaseEvent.create(
                        event_type=EventType.APPROVAL_DENIED,
                        source="terminal_executor",
                        payload={"req_id": req_id}
                    ))
                except Exception:
                    pass
                    
                return {
                    "success": False,
                    "error": "Permission denied by user (Human-in-the-loop rejection)"
                }
            
            approved_unlisted = bool(inspection.get("requires_approval"))
            logger.info("Execution GRANTED by user for command: '%s'", command)
            try:
                event_bus.publish(BaseEvent.create(
                    event_type=EventType.APPROVAL_GRANTED,
                    source="terminal_executor",
                    payload={"req_id": req_id}
                ))
            except Exception:
                pass

        # 2. Thực thi qua sandbox, không dùng shell=True.
        logger.info("Executing sandboxed command: '%s'", command)
        return await sandbox_runner.run(
            command,
            cwd=cwd or None,
            timeout=timeout,
            allow_unlisted=approved_unlisted,
        )


# Global singleton
terminal_executor = TerminalExecutor()
