"""ActionVerifier — xác minh kết quả thực thi các tác vụ hệ thống.

Cung cấp các cơ chế kiểm chứng tự động (verification) để xem hành động của agent có đạt kết quả mong muốn không.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Union

logger = logging.getLogger("ai-companion.execution.verifier")


class ActionVerifier:
    """Xác minh kết quả của các hành động."""

    def __init__(self) -> None:
        pass

    def verify_file_write(self, filepath: str, min_size_bytes: int = 1) -> Dict[str, Union[bool, str]]:
        """Xác minh file đã được ghi thành công và không bị rỗng."""
        try:
            if not os.path.exists(filepath):
                return {"verified": False, "error": f"File does not exist: {filepath}"}
            
            size = os.path.getsize(filepath)
            if size < min_size_bytes:
                return {"verified": False, "error": f"File is empty or too small: {size} bytes"}
                
            return {"verified": True, "message": f"File verified successfully: {size} bytes"}
        except Exception as e:
            return {"verified": False, "error": str(e)}

    def verify_command_success(self, exec_result: dict) -> Dict[str, Union[bool, str]]:
        """Xác minh kết quả thực thi shell command thành công."""
        if not exec_result:
            return {"verified": False, "error": "Execution result is empty"}
            
        success = exec_result.get("success", False)
        ret_code = exec_result.get("returncode", -1)
        
        if success and ret_code == 0:
            return {"verified": True, "message": "Command completed successfully with exit code 0"}
            
        err = exec_result.get("stderr") or exec_result.get("error") or "Unknown execution error"
        return {
            "verified": False,
            "error": f"Command failed (Exit code: {ret_code}). Error: {err}"
        }

    def get_auto_verify_command(self, project_root: str, changed_files: list[str]) -> str:
        """Tự động phát hiện lệnh kiểm thử hoặc kiểm tra cú pháp phù hợp dựa trên các file đã sửa."""
        if not changed_files:
            return ""

        from pathlib import Path
        import json
        
        proj_path = Path(project_root).resolve()
        has_python = any(f.endswith(".py") for f in changed_files)
        has_js = any(f.endswith(".js") for f in changed_files)
        has_ts = any(f.endswith(".ts") for f in changed_files)

        # 1. Ưu tiên kiểm thử Python
        if has_python:
            # Tìm xem có thư mục tests hoặc file test nào không
            has_tests = (proj_path / "tests").exists() or any(
                p.name.startswith("test_") or p.name.endswith("_test.py")
                for p in proj_path.glob("**/test_*.py")
            )
            if has_tests:
                # Sử dụng python -m pytest để chạy test suite
                return "python -m pytest"
            else:
                # Fallback: kiểm tra cú pháp
                py_files = [f for f in changed_files if f.endswith(".py")]
                files_str = " ".join(py_files)
                return f"python -m py_compile {files_str}"

        # 2. Ưu tiên JS/TS
        if has_js or has_ts:
            package_json_path = proj_path / "package.json"
            has_pnpm = (proj_path / "pnpm-lock.yaml").exists()
            
            if package_json_path.exists():
                try:
                    with open(package_json_path, "r", encoding="utf-8") as f:
                        pkg = json.load(f)
                    scripts = pkg.get("scripts", {})
                    if "test" in scripts:
                        return "pnpm test" if has_pnpm else "npm test"
                    if has_ts and "build-ts" in scripts:
                        return "pnpm run build-ts" if has_pnpm else "npm run build-ts"
                except Exception:
                    pass

            if has_ts:
                if (proj_path / "tsconfig.json").exists():
                    return "npx tsc --noEmit"
            
            js_files = [f for f in changed_files if f.endswith((".js", ".ts"))]
            if js_files:
                files_str = " ".join(js_files)
                return f"node --check {files_str}"

        return ""


# Global singleton
action_verifier = ActionVerifier()
