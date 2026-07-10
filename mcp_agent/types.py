from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional, Any

@dataclass
class MCPServer:
    """Class representing an MCP Server configuration."""
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: Optional[dict[str, str]] = None
    cwd: Optional[str] = None
    timeout: Optional[timedelta] = field(default_factory=lambda: timedelta(seconds=30))
    description: str = "No description available."
