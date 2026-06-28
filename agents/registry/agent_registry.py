"""AgentRegistry — đăng ký và quản lý danh sách các agent trong hệ thống.

Cho phép truy vấn các agent dựa trên tên hoặc khả năng (capabilities) của chúng.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai-companion.agents.registry")


class AgentRegistry:
    """Đăng ký các agent và mô tả năng lực thực thi của chúng."""

    def __init__(self) -> None:
        self._agents: Dict[str, Any] = {}
        self._capabilities: Dict[str, List[str]] = {}

    def register(self, name: str, agent_instance: Any, capabilities: List[str]) -> None:
        """Đăng ký một agent mới.

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

    def list_all_agents(self) -> Dict[str, List[str]]:
        """Liệt kê tất cả agents và capabilities."""
        return self._capabilities


# Global singleton
agent_registry = AgentRegistry()
