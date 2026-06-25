import asyncio
from datetime import timedelta
from contextlib import AsyncExitStack
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from core.logger import get_logger
from .server_registry import ServerRegistry

logger = get_logger("ai-companion.mcp")
DEFAULT_TIMEOUT = timedelta(seconds=30)

class MCPClientManager:
    """Manages spawning, maintaining, and calling stdio-based MCP servers."""

    def __init__(self, registry: ServerRegistry) -> None:
        self.registry = registry
        self.exit_stack = AsyncExitStack()
        self.active_sessions: Dict[str, ClientSession] = {}
        self.tool_to_server: Dict[str, str] = {}  # maps prefixed_tool_name -> server_name
        self.original_tool_names: Dict[str, str] = {}  # maps prefixed_tool_name -> original_tool_name

    async def _ensure_session(self, server_name: str) -> Optional[ClientSession]:
        """Ensure the server is running and return its session."""
        if server_name in self.active_sessions:
            return self.active_sessions[server_name]

        server = self.registry.servers.get(server_name)
        if not server:
            logger.error(f"MCP: Server '{server_name}' not configured in registry.")
            return None

        logger.info(f"MCP: Starting server '{server_name}' using command '{server.command}'...")
        server_params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=server.env,
            cwd=server.cwd
        )

        try:
            # Spawn the stdio sub-process
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            # Establish the MCP client session
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write, read_timeout_seconds=DEFAULT_TIMEOUT)
            )
            await session.initialize()
            self.active_sessions[server_name] = session
            logger.info(f"MCP: Session successfully established for server '{server_name}'")
            return session
        except Exception as e:
            logger.error(f"MCP: Failed to spawn and initialize server '{server_name}': {e}")
            return None

    async def get_all_tools(self) -> List[dict]:
        """Fetch all tools from active servers, registering them under prefixed names."""
        openai_tools = []
        # Attempt to connect to all configured servers
        for server_name in list(self.registry.servers.keys()):
            session = await self._ensure_session(server_name)
            if not session:
                continue

            try:
                response = await session.list_tools()
                for tool in response.tools:
                    prefixed_name = f"mcp__{server_name}__{tool.name}"
                    self.tool_to_server[prefixed_name] = server_name
                    self.original_tool_names[prefixed_name] = tool.name

                    openai_tools.append({
                        "name": prefixed_name,
                        "description": f"[MCP: {server_name}] {tool.description}",
                        "parameters": {
                            "type": "object",
                            "properties": tool.inputSchema.get("properties", {}),
                            "required": tool.inputSchema.get("required", [])
                        }
                    })
                    logger.info(f"MCP: Registered tool '{prefixed_name}' from server '{server_name}'")
            except Exception as e:
                logger.error(f"MCP: Error listing tools for server '{server_name}': {e}")

        return openai_tools

    async def call_tool(self, prefixed_tool_name: str, arguments: Dict[str, Any]) -> dict:
        """Forward a tool call request to the correct MCP server."""
        server_name = self.tool_to_server.get(prefixed_tool_name)
        orig_name = self.original_tool_names.get(prefixed_tool_name)

        if not server_name or not orig_name:
            return {"success": False, "error": f"MCP tool '{prefixed_tool_name}' not found."}

        session = await self._ensure_session(server_name)
        if not session:
            return {"success": False, "error": f"MCP server '{server_name}' is not running."}

        try:
            logger.info(f"MCP: Running tool '{orig_name}' on server '{server_name}' with args: {arguments}")
            response = await session.call_tool(orig_name, arguments)
            if response.isError:
                err_text = response.content[0].text if response.content else "Server error"
                return {"success": False, "error": err_text}

            # Parse content response
            parts = []
            if response.content:
                for item in response.content:
                    if hasattr(item, "text") and item.text:
                        parts.append(item.text)

            result_text = "\n".join(parts)
            return {"success": True, "result": result_text}
        except Exception as e:
            logger.error(f"MCP: Error invoking tool '{orig_name}' on server '{server_name}': {e}")
            return {"success": False, "error": str(e)}

    async def aclose(self) -> None:
        """Close all active servers."""
        logger.info("MCP: Shutting down all active sessions...")
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            logger.error(f"MCP: Error during exit stack shutdown: {e}")
        self.active_sessions.clear()
        self.tool_to_server.clear()
        self.original_tool_names.clear()
        logger.info("MCP: All sessions terminated.")
