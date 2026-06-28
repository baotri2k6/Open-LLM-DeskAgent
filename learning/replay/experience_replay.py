"""ExperienceReplay — tái diễn và phân tích các trải nghiệm trong quá khứ.

Replay lại các task thất bại hoặc thành công để đúc kết bài học hoặc tối ưu hóa chiến lược.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from learning.experience.experience_store import experience_store, Experience

logger = logging.getLogger("ai-companion.learning.replay")


class ExperienceReplay:
    """Tái diễn và phân tích lịch sử thực thi."""

    def __init__(self) -> None:
        pass

    def replay_failures(self) -> List[Dict[str, Any]]:
        """Phân tích toàn bộ các ca thất bại để tìm quy luật chung."""
        failures = experience_store.get_failures()
        analysis_reports = []
        
        for idx, fail in enumerate(failures, start=1):
            report = {
                "index": idx,
                "goal_id": fail.goal_id,
                "goal_desc": fail.goal_desc,
                "lessons": fail.lessons_learned,
                "timestamp": fail.timestamp,
                "recommendation": self._generate_recommendation(fail)
            }
            analysis_reports.append(report)
            
        logger.info("ExperienceReplay analyzed %d failure cases", len(analysis_reports))
        return analysis_reports

    def _generate_recommendation(self, exp: Experience) -> str:
        """Đưa ra khuyến nghị dựa trên bài học kinh nghiệm."""
        lessons_lower = exp.lessons_learned.lower()
        
        if "permission" in lessons_lower or "denied" in lessons_lower:
            return "Khuyến nghị: Yêu cầu phân quyền từ Workspace hoặc liên hệ người dùng điều chỉnh config.json"
            
        if "timeout" in lessons_lower:
            return "Khuyến nghị: Tăng thời gian chờ (timeout) cho các tác vụ shell tiếp theo"
            
        if "not found" in lessons_lower or "command not found" in lessons_lower:
            return "Khuyến nghị: Kiểm tra xem công cụ/phần mềm đích đã được cài đặt và thêm vào PATH chưa"
            
        return "Khuyến nghị: Xem xét lại thiết kế TaskGraph và điều chỉnh tham số đầu vào"


# Global singleton
experience_replay = ExperienceReplay()
