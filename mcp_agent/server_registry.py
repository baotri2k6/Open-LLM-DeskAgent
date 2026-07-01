import json
import os
import shutil
from pathlib import Path
from typing import Dict, Optional
from config.config import WRITABLE_ROOT, PROJECT_ROOT
from runtime.logger import get_logger
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

            raw_command = server_details["command"]
            args = list(server_details.get("args", []))
            if isinstance(raw_command, list):
                if not raw_command:
                    logger.warning(f"MCPSR: Empty command list for server '{server_name}'. Skipping.")
                    continue
                command = str(raw_command[0])
                args = [str(arg) for arg in raw_command[1:]] + args
            else:
                command = str(raw_command)
            if command == "npx" and not self.npx_available:
                logger.warning(f"MCPSR: npx not available. Skipping server '{server_name}'.")
                continue
            if command == "uvx" and not self.uvx_available:
                logger.warning(f"MCPSR: uvx not available. Skipping server '{server_name}'.")
                continue
            if command == "node" and not self.node_available:
                logger.warning(f"MCPSR: node not available. Skipping server '{server_name}'.")
                continue

            env = self._build_env(command, server_details.get("env", None))

            self.servers[server_name] = MCPServer(
                name=server_name,
                command=command,
                args=args,
                env=env,
                cwd=server_details.get("cwd", None),
            )
            logger.info(f"MCPSR: Loaded config for server: '{server_name}'")

    def _build_env(self, command: str, configured_env: Optional[dict[str, str]]) -> dict[str, str] | None:
        """Return subprocess env overrides for MCP servers."""
        env = dict(configured_env or {})
        if command == "uvx":
            cache_dir = WRITABLE_ROOT / "cache" / "uv"
            tool_dir = WRITABLE_ROOT / "tools" / "uv"
            cache_dir.mkdir(parents=True, exist_ok=True)
            tool_dir.mkdir(parents=True, exist_ok=True)
            env.setdefault("UV_CACHE_DIR", str(cache_dir))
            env.setdefault("UV_TOOL_DIR", str(tool_dir))
            env.setdefault("UV_LINK_MODE", "copy")

        if not env:
            return configured_env

        merged = os.environ.copy()
        merged.update(env)
        return merged
