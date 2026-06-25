import asyncio
import sys
import json
from pathlib import Path

# Add python-services directory to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "python-services"))

from services.llm_service import LLMService

class MockLLMService(LLMService):
    def __init__(self):
        super().__init__()

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing Self-Correction Loop ===")
    
    # We will manually simulate the agent loop fails logic
    recent_failures = {}
    t_name = "execute_command"
    t_args = {"command": "invalid_command_xyz"}
    
    args_str = json.dumps(t_args, sort_keys=True)
    fail_key = f"{t_name}:{args_str}"
    
    for i in range(1, 4):
        fail_count = recent_failures.get(fail_key, 0)
        
        # Simulate execute_tool failing
        t_output = {"success": False, "error": "Command not found", "exit_code": 1}
        
        if not t_output.get("success"):
            recent_failures[fail_key] = fail_count + 1
            if recent_failures[fail_key] >= 2:
                t_output["system_warning"] = (
                    f"CẢNH BÁO HỆ THỐNG: Công cụ '{t_name}' đã thất bại {recent_failures[fail_key]} lần liên tiếp với cùng tham số! "
                    f"Vui lòng KHÔNG chạy lại y hệt. Hãy phân tích thông báo lỗi, kiểm tra cú pháp "
                    f"hoặc sử dụng một phương pháp khác thay thế."
                )
                
        print(f"Failure {i}: recent_failures[{fail_key}] = {recent_failures[fail_key]}")
        if "system_warning" in t_output:
            print(f"-> System warning injected: {t_output['system_warning']}")
        else:
            print("-> No system warning yet.")

if __name__ == "__main__":
    asyncio.run(main())
