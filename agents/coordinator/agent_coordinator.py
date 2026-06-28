"""AgentCoordinator — điều phối và định tuyến các tác vụ đến các agent phù hợp.

Sử dụng AgentRegistry để biết agent nào có khả năng xử lý tác vụ tương ứng.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from agents.registry.agent_registry import agent_registry

logger = logging.getLogger("ai-companion.agents.coordinator")


class AgentCoordinator:
    """Điều phối và ủy quyền công việc cho các agent chuyên môn."""

    def __init__(self) -> None:
        self._registry = agent_registry

    async def route_task(self, capability: str, task_text: str, context: Optional[dict] = None) -> dict:
        """Định tuyến tác vụ đến agent phù hợp nhất.

        Args:
            capability: Khả năng yêu cầu (ví dụ: "open_app", "web_search", "read_file").
            task_text: Nội dung yêu cầu chi tiết.
            context: Ngữ cảnh phụ kèm theo.

        Returns:
            dict chứa kết quả thực thi của agent.
        """
        logger.info("Routing task with capability '%s'", capability)
        
        # 1. Tìm các agent phù hợp
        matching_agents = self._registry.find_agents_by_capability(capability)
        if not matching_agents:
            logger.warning("No registered agent found for capability: %s", capability)
            return {"success": False, "error": f"No agent handles capability: {capability}"}

        # 2. Chọn agent đầu tiên khớp
        agent_name = matching_agents[0]
        agent = self._registry.get_agent(agent_name)
        
        logger.info("Delegating task to agent: %s", agent_name)

        try:
            # 3. Gọi method xử lý của agent tùy thuộc vào interface của nó
            if hasattr(agent, "handle_message"):
                result = await agent.handle_message(task_text, context)
                return {"success": True, "result": result}
            elif hasattr(agent, "execute"):
                result = await agent.execute(task_text, context)
                return {"success": True, "result": result}
            else:
                # Fallback gọi trực tiếp method tương ứng tên capability
                method = getattr(agent, capability, None)
                if method:
                    # Kiểm tra async
                    import inspect
                    if inspect.iscoroutinefunction(method):
                        result = await method(task_text)
                    else:
                        result = method(task_text)
                    return {"success": True, "result": result}
                
                return {"success": False, "error": f"Agent {agent_name} lacks executable interface"}

        except Exception as e:
            logger.error("Error executing delegated task on agent %s: %s", agent_name, e)
            return {"success": False, "error": str(e)}

    async def execute_parallel_workflow(self, subtasks: List[dict]) -> List[dict]:
        """Điều phối chạy song song các subtask sử dụng subagent_service."""
        logger.info("Executing parallel workflow with %d subtasks", len(subtasks))
        
        from agents.subagent_service import run_parallel_subagents
        
        tasks_text = [t.get("task", "") for t in subtasks]
        focus_files_list = [t.get("focus_files", []) for t in subtasks]
        
        return await run_parallel_subagents(tasks_text, focus_files_list)


# Global singleton
agent_coordinator = AgentCoordinator()

