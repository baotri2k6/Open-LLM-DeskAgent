import sys
import asyncio
from pathlib import Path

# Set console output to UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python-services"))

from core.plugin_manager import PluginManager

async def test_plugins():
    print("=== TEST PLUGIN MANAGER ===")
    pm = PluginManager()
    
    print("\n--- Loaded Plugins ---")
    for name, plg in pm.plugins.items():
        print(f"Plugin: {name}")
        print(f"  Manifest: {plg['manifest']}")
        
    print("\n--- Registered Tools ---")
    for tool_name, (plugin_name, func) in pm.tools_registry.items():
        print(f"Tool: {tool_name} (from {plugin_name}) -> {func}")
        
    print("\n--- Tool Schemas ---")
    schemas = pm.get_tool_schemas()
    for s in schemas:
        print(f"Schema for {s['name']}: {s.get('description')}")
        
    print("\n--- Executing Chess Tool ---")
    res = await pm.execute_tool("chess_start_game", {})
    print(f"chess_start_game result: {res}")
    
    print("\n--- Executing HomeAssistant Tool ---")
    res = await pm.execute_tool("homeassistant_get_devices", {})
    print(f"homeassistant_get_devices result: {res}")
    
    print("\n--- Executing WebReader Tool ---")
    res = await pm.execute_tool("web_reader_parse", {"url": "https://en.wikipedia.org/wiki/Main_Page"})
    print(f"web_reader_parse result (trimmed): {str(res)[:1000]}...")

if __name__ == "__main__":
    asyncio.run(test_plugins())
