import os
import json
import asyncio
import importlib.util
from typing import Any, Callable, Dict, List, Tuple
from pathlib import Path
from core.logger import get_logger
from core.config import PROJECT_ROOT

logger = get_logger("ai-companion.plugin_manager")

class PluginManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.plugins_dir = PROJECT_ROOT / "plugins"
        self.plugins: Dict[str, dict] = {}
        self.tools_registry: Dict[str, Tuple[str, Callable]] = {}
        self.load_plugins()

    def load_plugins(self):
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return

        for path in self.plugins_dir.iterdir():
            if path.is_dir():
                manifest_path = path / "manifest.json"
                main_py_path = path / "main.py"
                if manifest_path.exists() and main_py_path.exists():
                    try:
                        with manifest_path.open("r", encoding="utf-8") as f:
                            manifest = json.load(f)
                        
                        plugin_name = manifest.get("name")
                        if not plugin_name:
                            continue

                        spec = importlib.util.spec_from_file_location(
                            f"plugins.{plugin_name}", str(main_py_path)
                        )
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)

                            self.plugins[plugin_name] = {
                                "manifest": manifest,
                                "module": module
                            }

                            for tool_info in manifest.get("tools", []):
                                tool_name = tool_info.get("name")
                                func = getattr(module, tool_name, None)
                                if func:
                                    self.tools_registry[tool_name] = (plugin_name, func)
                                    logger.info(f"Registered tool '{tool_name}' from plugin '{plugin_name}'")
                                else:
                                    logger.warning(f"Tool '{tool_name}' listed in manifest but not found in main.py")
                            
                            logger.info(f"Successfully loaded plugin: {plugin_name}")
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {path}: {e}")

    def get_tool_schemas(self) -> List[dict]:
        schemas = []
        for name, (plugin_name, _) in self.tools_registry.items():
            plugin = self.plugins.get(plugin_name)
            if plugin:
                for tool in plugin["manifest"].get("tools", []):
                    if tool.get("name") == name:
                        # Ensure formatting matches target parameter schema
                        schemas.append(tool)
        return schemas

    async def execute_tool(self, tool_name: str, args: dict) -> Any:
        if tool_name in self.tools_registry:
            _, func = self.tools_registry[tool_name]
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(**args)
                return func(**args)
            except Exception as e:
                logger.error(f"Error executing plugin tool '{tool_name}': {e}")
                return f"Error executing tool: {str(e)}"
        return None
