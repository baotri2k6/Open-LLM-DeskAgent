"""Context-aware humor helpers for companion responses."""

from __future__ import annotations

import random


class HumorEngine:
    """Generates short, safe humor nudges from conversation context."""

    TOPIC_LINES = {
        "coding": [
            "Bug này chắc đang cosplay feature rồi.",
            "Code không chạy thì mình cho nó một buổi trị liệu nhỏ.",
        ],
        "debug": [
            "Debug là nghệ thuật nhìn chằm chằm cho tới khi lỗi tự thấy ngại.",
            "Ổn, mình lần theo dấu vết như đọc nhật ký của bug.",
        ],
        "deadline": [
            "Deadline dí thì mình đi từng bước, đừng để nó làm đạo diễn phim kinh dị.",
        ],
        "idle": [
            "Tao thấy mày im hơi lâu rồi, máy vẫn sống, chủ nhân thì chưa rõ.",
        ],
    }

    def generate(self, context: str = "", mood: str = "playful") -> str:
        text = context.lower()
        for keyword, lines in self.TOPIC_LINES.items():
            if keyword in text:
                return random.choice(lines)
        if mood in ("calm", "serious"):
            return ""
        return random.choice([
            "Tạm thời mọi thứ vẫn dưới quyền kiểm soát. Ít nhất là trên giấy.",
            "Để tao xem, biết đâu vấn đề chỉ đang trốn hơi kỹ.",
        ])

    def should_use_humor(self, emotion: str = "neutral", context: str = "") -> bool:
        if emotion in {"sad", "anxious"}:
            return False
        return any(key in context.lower() for key in self.TOPIC_LINES) or emotion in {"happy", "excited", "neutral"}


humor_engine = HumorEngine()
