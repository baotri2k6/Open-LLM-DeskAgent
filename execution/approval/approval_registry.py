"""Shared registry for human-in-the-loop approvals."""

from __future__ import annotations

import time
import asyncio
from typing import Dict, Optional
from pathlib import Path

# Dict to store pending approvals: { req_id: approved_bool }
# None means pending, True/False means approved/denied.
pending_approvals: Dict[str, Optional[bool]] = {}


class PermissionManager:
    @staticmethod
    def requires_approval(tool_name: str, args: dict) -> bool:
        """
        Kiểm tra xem việc thực thi công cụ có cần sự phê duyệt của người dùng hay không.
        Sử dụng cấu hình từ companion.config.json.
        """
        from config.config import config
        
        # Nếu bật autoMode toàn cục (hoặc autoMode = True) thì không cần phê duyệt
        if config.get("agent.autoMode", False):
            return False
            
        # Lấy chế độ phân quyền từ config
        perm_mode = config.get("agent.permissions.mode", "auto_safe")
        
        if perm_mode == "allow_all":
            return False
        if perm_mode == "ask_all":
            return True
            
        # Mặc định các công cụ đọc/truy vấn thông tin không nguy hại (như read_file, search_google, ...) không cần duyệt
        if tool_name not in ["execute_command", "write_to_file"]:
            return False
            
        # Chế độ trust_workspace: tự động duyệt nếu tác động nằm trong phạm vi an toàn
        if perm_mode == "trust_workspace":
            if tool_name == "write_to_file":
                path_str = args.get("path", "")
                if path_str:
                    from config.config import PROJECT_ROOT, WRITABLE_ROOT
                    try:
                        p = Path(path_str).resolve()
                        is_in_project = PROJECT_ROOT.resolve() in p.parents or PROJECT_ROOT.resolve() == p
                        is_in_writable = WRITABLE_ROOT.resolve() in p.parents or WRITABLE_ROOT.resolve() == p
                        if is_in_project or is_in_writable:
                            return False  # Thao tác ghi file trong dự án là an toàn
                    except Exception:
                        pass
                        
            elif tool_name == "execute_command":
                cmd = (args.get("command", "")).strip()
                if cmd:
                    whitelist = [
                        "git status", "git diff", "git log", "git branch",
                        "npm run build", "npm test", "npm run dev",
                        "python -m unittest", "pytest", "python -m pytest", "dir", "ls"
                    ]
                    cmd_lower = cmd.lower()
                    for item in whitelist:
                        if cmd_lower.startswith(item) or cmd_lower == item:
                            return False  # Các lệnh đọc thông tin hoặc test cục bộ được tự động duyệt
                            
        # Chế độ mặc định auto_safe: các công cụ nguy hại luôn yêu cầu duyệt
        return True


async def wait_for_approval(req_id: str, timeout: float = 120.0) -> bool:
    """Đợi phê duyệt từ người dùng một cách bất đồng bộ (tránh block event loop)."""
    pending_approvals[req_id] = None
    start_time = time.time()
    
    while pending_approvals.get(req_id) is None:
        if time.time() - start_time > timeout:
            pending_approvals[req_id] = False
            break
        await asyncio.sleep(0.2)
        
    result = pending_approvals.get(req_id, False)
    # Dọn dẹp bộ nhớ
    if req_id in pending_approvals:
        del pending_approvals[req_id]
    return bool(result)


def submit_approval(req_id: str, approved: bool) -> bool:
    """Cập nhật kết quả phê duyệt cho một yêu cầu."""
    if req_id in pending_approvals:
        pending_approvals[req_id] = approved
        return True
    return False
