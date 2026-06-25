import json
import shutil
from pathlib import Path
from typing import Dict, Optional
from core.config import WRITABLE_ROOT, PROJECT_ROOT
from core.logger import get_logger
from .types import MCPServer

logger = get_logger("ai-companion.mcp")

class ServerRegistry:
    """Manages reading and parsing the mcp_servers.json configuration file."""

    def __init__(self, config_path: str | Path = None) -> None:
        if config_path is None:
            # Try WRITABLE_ROOT first (user configuration)
            config_path = WRITABLE_ROOT / "config" / "mcp_servers.json"
            if not config_path.exists():
                # Fallback to PROJECT_ROOT
                config_path = PROJECT_ROOT / "config" / "mcp_servers.json"

        self.config_path = Path(config_path)
        self.servers: Dict[str, MCPServer] = {}

        self.npx_available = self._detect_runtime("npx")
        self.uvx_available = self._detect_runtime("uvx")
        self.node_available = self._detect_runtime("node")

        self.load_servers()

    def _detect_runtime(self, target: str) -> bool:
        """Check if a runtime is available in system PATH."""
        return shutil.which(target) is not None

    def load_servers(self) -> None:
        """Load servers from config file."""
        if not self.config_path.exists():
            logger.warning(f"MCPSR: Config file not found at {self.config_path}")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            logger.error(f"MCPSR: Failed to read config file: {e}")
            return

        servers_config = config_data.get("mcp_servers", {})
        if not servers_config:
            logger.warning("MCPSR: No servers declared in config file.")
            return

        for server_name, server_details in servers_config.items():
            if "command" not in server_details:
                logger.warning(f"MCPSR: Missing 'command' for server '{server_name}'. Skipping.")
                continue

            command = server_details["command"]
            if command == "npx" and not self.npx_available:
                logger.warning(f"MCPSR: npx not available. Skipping server '{server_name}'.")
                continue
            if command == "uvx" and not self.uvx_available:
                logger.warning(f"MCPSR: uvx not available. Skipping server '{server_name}'.")
                continue
            if command == "node" and not self.node_available:
                logger.warning(f"MCPSR: node not available. Skipping server '{server_name}'.")
                continue

            self.servers[server_name] = MCPServer(
                name=server_name,
                command=command,
                args=server_details.get("args", []),
                env=server_details.get("env", None),
                cwd=server_details.get("cwd", None),
            )
            logger.info(f"MCPSR: Loaded config for server: '{server_name}'")
