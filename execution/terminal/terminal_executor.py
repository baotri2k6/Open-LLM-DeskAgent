"""TerminalExecutor — thực thi các lệnh shell hệ thống an toàn.

Tất cả các lệnh thực thi đều được kiểm duyệt qua PermissionManager.
Yêu cầu sự phê duyệt từ người dùng (Human-in-the-loop) nếu là lệnh nguy hại.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import uuid
from typing import Dict

from execution.approval.approval_registry import PermissionManager, wait_for_approval

logger = logging.getLogger("ai-companion.execution.terminal")


class TerminalExecutor:
    """Thực thi shell command có kiểm soát phê duyệt an toàn."""

    def __init__(self) -> None:
        pass

    async def execute(self, command: str, timeout: float = 60.0) -> Dict[str, Any]:
        """Thực thi câu lệnh command line.

        Args:
            command: Câu lệnh shell (ví dụ: 'npm run test').
            timeout: Thời gian tối đa chờ lệnh hoàn thành.
        """
        command = command.strip()
        if not command:
            return {"success": False, "error": "Empty command"}

        # 1. Kiểm tra phân quyền và phê duyệt qua PermissionManager
        args = {"command": command}
        if PermissionManager.requires_approval("execute_command", args):
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
            
            logger.info("Execution GRANTED by user for command: '%s'", command)
            try:
                event_bus.publish(BaseEvent.create(
                    event_type=EventType.APPROVAL_GRANTED,
                    source="terminal_executor",
                    payload={"req_id": req_id}
                ))
            except Exception:
                pass

        # 2. Thực thi lệnh thực tế
        try:
            logger.info("Executing system shell command: '%s'", command)
            
            # Xác định shell phù hợp tùy OS
            shell = True
            if sys.platform == "win32":
                # PowerShell hoặc cmd
                shell = "powershell" if sys.executable else True

            # Chạy subprocess đồng bộ trong executor để tránh blocking loop
            import asyncio
            loop = asyncio.get_event_loop()
            
            def _run():
                return subprocess.run(
                    command,
                    shell=shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=timeout
                )
                
            proc = await loop.run_in_executor(None, _run)
            
            success = proc.returncode == 0
            stdout = proc.stdout
            stderr = proc.stderr
            
            return {
                "success": success,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
        except subprocess.TimeoutExpired:
            logger.error("Command timed out: '%s'", command)
            return {"success": False, "error": f"Command timed out after {timeout} seconds"}
        except Exception as e:
            logger.error("Failed to execute command: %s", e)
            return {"success": False, "error": str(e)}


# Global singleton
terminal_executor = TerminalExecutor()
