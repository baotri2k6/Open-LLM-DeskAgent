"""AgentCoordinator — điều phối và định tuyến các tác vụ đến các agent phù hợp.

Sử dụng AgentRegistry để biết agent nào có khả năng xử lý tác vụ tương ứng.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

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
            if hasattr(agent, "execute_task"):
                # Gói payload thích hợp cho các tác vụ chuyên dụng
                payload = {"query": task_text, "text": task_text, "snippets": [task_text]}
                result = await agent.execute_task(capability, payload)
                return {"success": True, "result": result}
            elif hasattr(agent, "handle_message"):
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
        """Điều phối chạy song song các subtask sử dụng subagent_service với timeout và cách ly lỗi."""
        logger.info("Executing parallel workflow with %d subtasks", len(subtasks))
        
        import asyncio
        from agents.subagent_service import run_subagent
        
        coros = []
        for idx, t in enumerate(subtasks):
            task_text = t.get("task", "")
            focus_files = t.get("focus_files", [])
            
            timeout = t.get("timeout")
            if timeout is None:
                task_lower = task_text.lower()
                if any(k in task_lower for k in ["vision", "screen", "ocr", "ground", "image"]):
                    timeout = 15.0
                elif any(k in task_lower for k in ["code", "coding", "compile", "pytest", "test"]):
                    timeout = 120.0
                else:
                    timeout = 60.0
            
            async def run_with_timeout(tk=task_text, ff=focus_files, to=timeout, s_idx=idx):
                try:
                    return await asyncio.wait_for(run_subagent(tk, ff), timeout=to)
                except asyncio.TimeoutError:
                    logger.error("Subtask %d timed out after %.1fs: %s", s_idx, to, tk)
                    return {"success": False, "error": f"Subtask timed out after {to}s"}
                except Exception as ex:
                    logger.error("Subtask %d failed with exception: %s", s_idx, ex)
                    return {"success": False, "error": str(ex)}
            
            coros.append(run_with_timeout())
            
        results = await asyncio.gather(*coros, return_exceptions=True)
        
        processed_results = []
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error("Subtask %d crashed: %s", idx, res)
                processed_results.append({"success": False, "error": str(res)})
            else:
                processed_results.append(res)
                
        return processed_results


# Global singleton
agent_coordinator = AgentCoordinator()
