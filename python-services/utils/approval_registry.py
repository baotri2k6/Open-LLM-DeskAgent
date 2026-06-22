"""Shared registry for human-in-the-loop approvals."""

from __future__ import annotations

import time
import asyncio
from typing import Dict, Optional

# Dict to store pending approvals: { req_id: approved_bool }
# None means pending, True/False means approved/denied.
pending_approvals: Dict[str, Optional[bool]] = {}


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
