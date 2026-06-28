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


# Global singleton
action_verifier = ActionVerifier()
