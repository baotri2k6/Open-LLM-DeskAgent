"""Detects emotional sentiment from text input."""

from __future__ import annotations


class EmotionDetector:
    """Detects primary emotion and sentiment from text conversations."""

    def __init__(self) -> None:
        self.emotions_keywords = {
            "happy": ["vui", "sướng", "tuyệt", "mừng", "yêu", "thích", "cảm ơn"],
            "sad": ["buồn", "khóc", "nản", "chán", "thất vọng", "tệ"],
            "angry": ["tức", "điên", "bực", "ghét", "tồi", "giận"],
            "fear": ["sợ", "lo", "ngại", "hãi"]
        }

    def detect_emotion(self, text: str) -> str:
        """Find matching emotional keyword in text. Returns neutral by default."""
        text_lower = text.lower()
        for emotion, keywords in self.emotions_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return emotion
        return "neutral"


# Global singleton
emotion_detector = EmotionDetector()
