import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python-services")))

from agents.desktop_agent import DesktopAgent
from tools.computer_control import mouse_click, mouse_move
from tools.browser_control import open_url

async def run_tests():
    agent = DesktopAgent()
    
    print("=== Test 1: Compound command warning in open_application ===")
    res1 = await agent.open_application("trình duyệt và bật nhạc")
    print(res1)
    
    print("\n=== Test 2: Standard alias 'trình duyệt' ===")
    # should try chrome/msedge/coccoc
    print("APP_ALIASES for 'trình duyệt':", agent.APP_ALIASES.get("trình duyệt"))
    
    print("\n=== Test 3: Website aliases ===")
    print("youtube:", agent.APP_ALIASES.get("youtube"))
    print("messenger:", agent.APP_ALIASES.get("messenger"))
    
    print("\n=== Test 4: Smooth mouse move function call (without actual run unless requested) ===")
    print("mouse_move path compiles ok.")

if __name__ == "__main__":
    asyncio.run(run_tests())
