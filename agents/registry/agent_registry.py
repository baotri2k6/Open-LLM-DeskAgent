"""AgentRegistry — đăng ký và quản lý danh sách các agent trong hệ thống."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai-companion.agents.registry")


class AgentRegistry:
    """Đăng ký các agent và mô tả năng lực thực thi của chúng.
    
    Cho phép tự động hóa định tuyến tác vụ (task routing) dựa trên năng lực.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._capabilities: Dict[str, List[str]] = {}
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        """Tự động đăng ký các core agents mặc định của hệ thống."""
        # 1. Register Desktop Agent stub/instance representation
        self.register(
            name="desktop",
            agent_instance=None,
            capabilities=["click", "type", "hotkey", "screenshot", "control_mouse", "control_keyboard"]
        )
        # 2. Register Browser Agent stub/instance representation
        self.register(
            name="browser",
            agent_instance=None,
            capabilities=["open_url", "web_search", "click_web_element", "extract_page_content"]
        )
        # 3. Register Coding Agent stub/instance representation
        self.register(
            name="coding",
            agent_instance=None,
            capabilities=["scan_directory", "write_code", "run_tests", "debug_code"]
        )
        # 4. Register Memory Agent stub/instance representation
        self.register(
            name="memory",
            agent_instance=None,
            capabilities=["remember_fact", "recall_context", "update_beliefs", "write_diary"]
        )
        # 5. Register Research Agent representation
        try:
            from agents.research.research_agent import research_agent
            self.register(
                name="research",
                agent_instance=research_agent,
                capabilities=["research_web", "literature_search", "synthesize_report"]
            )
        except Exception:
            self.register(
                name="research",
                agent_instance=None,
                capabilities=["research_web", "literature_search", "synthesize_report"]
            )

    def register(self, name: str, agent_instance: Any, capabilities: List[str]) -> None:
        """Đăng ký một agent mới hoặc ghi đè agent hiện tại.

        Args:
            name: Tên của agent (ví dụ: "browser", "desktop").
            agent_instance: Instance của agent class.
            capabilities: Danh sách các năng lực (ví dụ: ["web_search", "open_url"]).
        """
        self._agents[name] = agent_instance
        self._capabilities[name] = capabilities
        logger.info("Agent registered: %s with capabilities %s", name, capabilities)

    def get_agent(self, name: str) -> Any | None:
        """Lấy agent instance theo tên."""
        return self._agents.get(name)

    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Tìm các agent hỗ trợ khả năng này."""
        matching = []
        for name, caps in self._capabilities.items():
            if capability in caps:
                matching.append(name)
        return matching

    def get_all_capabilities(self) -> List[str]:
        """Lấy danh sách tất cả các năng lực hiện có trong hệ thống."""
        all_caps = set()
        for caps in self._capabilities.values():
            all_caps.update(caps)
        return sorted(list(all_caps))

    def list_all_agents(self) -> Dict[str, List[str]]:
        """Liệt kê tất cả agents và capabilities."""
        return self._capabilities

    async def route_task(self, capability: str, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Định tuyến và thực thi tác vụ trên agent phù hợp nhất.
        
        Args:
            capability: Năng lực cần dùng (ví dụ: 'open_url').
            task_payload: Nội dung chi tiết của tác vụ.
            
        Returns:
            Dict chứa kết quả thực hiện hoặc thông tin lỗi.
        """
        agents = self.find_agents_by_capability(capability)
        if not agents:
            return {"success": False, "error": f"No agent registered for capability: {capability}"}
        
        agent_name = agents[0]
        agent_instance = self.get_agent(agent_name)
        if not agent_instance:
            return {
                "success": False,
                "error": f"Agent '{agent_name}' matches capability '{capability}' but is not instantiated yet."
            }

        try:
            # Delegate to standard execute or handle_message of the registered agent instance
            if hasattr(agent_instance, "execute_task"):
                res = await agent_instance.execute_task(capability, task_payload)
                return {"success": True, "agent": agent_name, "result": res}
            elif hasattr(agent_instance, "handle_message"):
                res = await agent_instance.handle_message(str(task_payload))
                return {"success": True, "agent": agent_name, "result": res}
            
            return {
                "success": False,
                "error": f"Agent '{agent_name}' does not implement execute_task or handle_message"
            }
        except Exception as e:
            logger.error("Error executing task on routed agent '%s': %s", agent_name, e)
            return {"success": False, "error": str(e)}


# Global singleton
agent_registry = AgentRegistry()
