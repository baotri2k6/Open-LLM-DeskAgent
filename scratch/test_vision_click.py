import asyncio
import sys
from pathlib import Path

# Add python-services directory to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "python-services"))

from tools.computer_control import click_element_by_vision

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing click_element_by_vision (UI-TARS Grounding) ===")
    
    # We will test locating the Windows Taskbar/Start button or a browser window
    # By running in 'move' mode first (so we don't click anything randomly)
    description = "nút Start của Windows ở góc dưới cùng bên trái màn hình"
    
    print(f"Attempting to locate: '{description}' in 'move' mode...")
    
    # Run the vision tool to move mouse to coordinates
    result = click_element_by_vision(description, action_type="move")
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
