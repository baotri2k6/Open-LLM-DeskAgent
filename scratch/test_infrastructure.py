import asyncio
import sys
from pathlib import Path

# Add python-services directory to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "python-services"))

from utils.approval_registry import PermissionManager
from services.subagent_service import run_subagent

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing PermissionManager ===")
    # Test Auto_Safe mode
    args = {"command": "git status"}
    requires = PermissionManager.requires_approval("execute_command", args)
    print(f"git status in default mode requires approval: {requires} (Expected: True)")

    # Test safe tool
    requires_safe = PermissionManager.requires_approval("read_file", {"path": "test.txt"})
    print(f"read_file requires approval: {requires_safe} (Expected: False)")

    print("\n=== Testing Subagent Service (mock run) ===")
    # Try calling subagent
    res = await run_subagent("Trả về câu chào ngắn gọn 'Hello World'", focus_files=[])
    print(f"Subagent result: {res}")

if __name__ == "__main__":
    asyncio.run(main())
