"""EmpathyEngine — phát hiện cảm xúc user và phản ứng đồng cảm.

Empathy là core của companion experience. Cô ấy không chỉ trả lời —
cô ấy lắng nghe cảm xúc đằng sau lời nói.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("ai-companion.social.empathy")


@dataclass
class UserEmotionReading:
    """Kết quả phân tích cảm xúc từ user input."""
    detected_emotion:   str     # happy | sad | frustrated | anxious | excited | neutral
    confidence:         float   # 0.0 → 1.0
    intensity:          float   # 0.0 → 1.0
    needs_support:      bool    # User có cần hỗ trợ cảm xúc không?
    recommended_tone:   str     # empathetic | celebratory | calm | encouraging | neutral


class EmpathyEngine:
    """Phát hiện cảm xúc user và đưa ra gợi ý tone phản hồi.

    Sử dụng keyword matching kết hợp pattern detection.
    Phiên bản sau sẽ tích hợp sentiment model từ speech/voice.
    """

    # Keywords và emoji patterns
    EMOTION_PATTERNS: dict[str, list[str]] = {
        "frustrated": [
            r"chán", r"mệt", r"khó chịu", r"bực", r"tức", r"lỗi mãi",
            r"không hiểu", r"sao cứ", r"tại sao", r"debug mãi", r"không được",
            r"debug mai", r"mai khong", r"khong duoc", r"buc qua", r"buc",
            r"mãi không", r"không làm được", r"sửa mãi",
            r"🤤", r"😡", r"🤬", r"damn", r"wtf",
        ],
        "sad": [
            r"buồn", r"khóc", r"thất bại", r"không được", r"tệ quá",
            r"cô đơn", r"😢", r"😭", r"😔", r"depressed",
        ],
        "anxious": [
            r"\blo\b", r"sợ", r"lo lắng", r"không biết có được không",
            r"anxious", r"nervous", r"deadline", r"😰", r"😟",
        ],
        "excited": [
            r"tuyệt", r"wow", r"ok rồi", r"xong rồi", r"làm được",
            r"ngon", r"🎉", r"✅", r"🔥", r"great", r"yeah",
        ],
        "happy": [
            r"vui", r"haha", r"lol", r"hihi", r"😄", r"😊", r"😁", r"hehe",
        ],
    }

    # Tone recommendations
    TONE_MAP: dict[str, str] = {
        "frustrated": "empathetic",
        "sad":        "empathetic",
        "anxious":    "calm",
        "excited":    "celebratory",
        "happy":      "celebratory",
        "neutral":    "neutral",
    }

    def __init__(self) -> None:
        # Compile patterns
        self._compiled: dict[str, list[re.Pattern]] = {}
        for emotion, patterns in self.EMOTION_PATTERNS.items():
            self._compiled[emotion] = [
                re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns
            ]

    def analyze(self, text: str) -> UserEmotionReading:
        """Phân tích cảm xúc từ text input.

        Args:
            text: User input (có thể là tiếng Việt hoặc tiếng Anh).

        Returns:
            UserEmotionReading với emotion, confidence, tone recommendation.
        """
        scores: dict[str, int] = {e: 0 for e in self._compiled}

        for emotion, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(text):
                    scores[emotion] += 1

        max_score = max(scores.values())

        if max_score == 0:
            return UserEmotionReading(
                detected_emotion="neutral",
                confidence=0.5,
                intensity=0.0,
                needs_support=False,
                recommended_tone="neutral",
            )

        detected = max(scores, key=lambda e: scores[e])
        # Normalize confidence by number of matching patterns
        total_patterns = len(self.EMOTION_PATTERNS[detected])
        confidence = min(1.0, 0.4 + (max_score / total_patterns) * 0.6)
        intensity = min(1.0, max_score * 0.25)

        needs_support = detected in ("frustrated", "sad", "anxious")

        return UserEmotionReading(
            detected_emotion=detected,
            confidence=confidence,
            intensity=intensity,
            needs_support=needs_support,
            recommended_tone=self.TONE_MAP.get(detected, "neutral"),
        )

    def get_empathy_prefix(self, reading: UserEmotionReading) -> str:
        """Gợi ý prefix để companion thêm vào đầu response khi cần empathy.

        Trả về empty string nếu không cần.
        """
        if not reading.needs_support or reading.confidence < 0.5:
            return ""

        prefixes = {
            "frustrated": [
                "Tao hiểu, debug lâu thật sự mệt.",
                "Ừ, kiểu lỗi này dễ làm mình bực lắm.",
                "Bình tĩnh, từ từ mình cùng xem.",
            ],
            "sad": [
                "Này... mày ổn không?",
                "Nghe có vẻ khó khăn thật.",
                "Tao ở đây nhé.",
            ],
            "anxious": [
                "Thở sâu đi, từ từ thôi.",
                "Ổn thôi, mình xử lý được.",
                "Cứ từng bước một.",
            ],
        }

        import random
        options = prefixes.get(reading.detected_emotion, [])
        return random.choice(options) if options else ""


# Global singleton
empathy_engine = EmpathyEngine()
