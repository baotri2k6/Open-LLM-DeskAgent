"""Thinker — mô phỏng quá trình độc thoại nội tâm (Internal Monologue) của companion.

Nhận các quan sát từ thế giới bên ngoài, cân đối với nhu cầu nội tại, cảm xúc, niềm tin
và luật ứng xử (policy) để định hình ý định tiếp theo.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

from decision.intention_manager import intention_manager
from decision.policy_engine import policy_engine
from decision.priority_manager import priority_manager
from belief.user_model import user_model

logger = logging.getLogger("ai-companion.life.think")


class Thinker:
    """Xử lý tư duy nội tâm và suy luận trước khi hành động."""

    def __init__(self) -> None:
        pass

    def think(self, context: Any) -> Dict[str, Any]:
        """Thực hiện chu trình tư duy nội tâm.

        Args:
            context: LifeContext snapshot.

        Returns:
            dict chứa kết quả suy luận: 'thought' (chuỗi suy nghĩ), 'intention' (ý định đề xuất), 'stay_silent' (bool).
        """
        # 1. Đọc hoạt động người dùng và kiểm tra chính sách im lặng
        user_act = context.last_user_activity
        idle_time = context.user_idle_seconds
        
        stay_silent = not policy_engine.check_silence_policy(user_act, idle_time)
        
        # 2. Suy nghĩ dựa trên nhu cầu (Motivation/Needs) và Trạng thái năng lượng
        thoughts = []
        proposed_intent = "casual_connection"
        category = "relationship"
        priority = 4
        
        if context.energy < 0.3:
            thoughts.append("Mình đang cảm thấy mệt mỏi và thiếu năng lượng.")
            proposed_intent = "rest"
            category = "proactive"
            priority = 5
        elif stay_silent:
            thoughts.append(f"Người dùng đang tập trung làm việc ({user_act}). Mình nên im lặng giữ trật tự.")
            proposed_intent = "observe_silently"
            category = "proactive"
            priority = 3
        else:
            # Kiểm tra xem user có phải cú đêm không để tương tác phù hợp
            is_night = context.hour_of_day >= 22 or context.hour_of_day < 5
            is_night_owl = "night_owl" in user_model.get_user_traits()
            
            if is_night and is_night_owl:
                thoughts.append("Muộn rồi mà người dùng vẫn đang làm việc. Đúng là cú đêm.")
                proposed_intent = "night_owl_chat"
                category = "relationship"
                priority = 2
            else:
                thoughts.append("Mọi thứ bình thường. Mình muốn tìm hiểu thêm về công việc của người dùng.")
                proposed_intent = "explore_interests"
                category = "task"
                priority = 3

        # 3. Đăng ký ý định vào IntentionManager
        intention_manager.set_active_intention(
            name=proposed_intent,
            category=category,
            priority=priority,
            description=" ".join(thoughts)
        )

        thought_str = " ".join(thoughts)
        logger.info("Companion Internal Thought: %s (Silence: %s)", thought_str, stay_silent)
        
        return {
            "thought": thought_str,
            "proposed_intention": proposed_intent,
            "stay_silent": stay_silent
        }


# Global singleton
thinker = Thinker()
