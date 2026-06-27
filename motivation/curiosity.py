"""CuriositySystem — hệ thống tò mò nội tại của companion.

IceGirl không chỉ trả lời câu hỏi — cô ấy có sự tò mò riêng.
Module này track các topic đang được quan tâm và sinh ra câu hỏi
hoặc impulse khám phá khi companion đang idle.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field

logger = logging.getLogger("ai-companion.motivation.curiosity")


@dataclass
class CuriosityTopic:
    """Một topic mà companion đang tò mò."""
    topic:          str
    interest_level: float       # 0.0 → 1.0
    last_explored:  float       = field(default_factory=time.time)
    explore_count:  int         = 0
    source:         str         = "conversation"   # conversation | observation | spontaneous


class CuriositySystem:
    """Quản lý hệ thống tò mò của companion.

    Companion tích lũy các topic từ cuộc trò chuyện và môi trường.
    Khi idle, có thể "nghĩ về" một topic và sinh ra câu hỏi hoặc insight.
    """

    MAX_TOPICS = 20       # Giữ tối đa 20 topics
    MIN_COOLDOWN = 300    # 5 phút cooldown giữa các curiosity trigger

    def __init__(self) -> None:
        self._topics: dict[str, CuriosityTopic] = {}
        self._last_trigger: float = 0.0
        self._question_templates = [
            "Tau đang tự hỏi về {topic}... mày nghĩ sao?",
            "Nhân tiện, {topic} — tau chưa hiểu rõ lắm, có gì thú vị không?",
            "Hôm nay tau nghĩ đến {topic}, mày có biết gì về nó không?",
            "À này, tau tò mò về {topic} — mày có thể giải thích không?",
        ]

    def add_topic(self, topic: str, interest: float = 0.5, source: str = "conversation") -> None:
        """Thêm hoặc update topic tò mò."""
        topic_lower = topic.lower().strip()
        if topic_lower in self._topics:
            existing = self._topics[topic_lower]
            existing.interest_level = min(1.0, existing.interest_level + 0.1)
        else:
            self._topics[topic_lower] = CuriosityTopic(
                topic=topic,
                interest_level=interest,
                source=source,
            )

        # Prune nếu vượt max
        if len(self._topics) > self.MAX_TOPICS:
            least = min(self._topics.values(), key=lambda t: t.interest_level)
            del self._topics[least.topic.lower()]

        logger.debug("Curiosity topic added: %s (interest=%.2f)", topic, interest)

    def extract_topics_from_text(self, text: str) -> list[str]:
        """Trích xuất topics đơn giản từ text (keyword-based).

        Phiên bản đầy đủ sẽ dùng NER. Hiện tại dùng heuristic.
        """
        # Các từ khóa kỹ thuật phổ biến trong context của project
        tech_keywords = [
            "python", "javascript", "typescript", "rust", "react", "fastapi",
            "docker", "kubernetes", "ai", "machine learning", "neural network",
            "live2d", "electron", "sqlite", "chromadb", "ollama", "gemini",
            "websocket", "api", "async", "thread", "memory", "embedding",
        ]

        found = []
        text_lower = text.lower()
        for kw in tech_keywords:
            if kw in text_lower and kw not in self._topics:
                found.append(kw)

        return found[:3]  # Tối đa 3 topics mỗi turn

    def should_trigger(self) -> bool:
        """Có nên trigger curiosity không?"""
        now = time.time()
        if now - self._last_trigger < self.MIN_COOLDOWN:
            return False
        if not self._topics:
            return False
        # Random chance — không phải lần nào idle cũng hỏi
        high_interest = [t for t in self._topics.values() if t.interest_level > 0.6]
        return len(high_interest) > 0 and random.random() < 0.3

    def get_curious_question(self) -> str | None:
        """Sinh ra câu hỏi tò mò nếu có topic phù hợp."""
        if not self.should_trigger():
            return None

        # Chọn topic chưa được explore gần đây và interest cao
        candidates = sorted(
            self._topics.values(),
            key=lambda t: (t.interest_level - (time.time() - t.last_explored) / 3600),
            reverse=True,
        )

        if not candidates:
            return None

        chosen = candidates[0]
        chosen.last_explored = time.time()
        chosen.explore_count += 1
        self._last_trigger = time.time()

        template = random.choice(self._question_templates)
        question = template.format(topic=chosen.topic)

        logger.info("Curiosity triggered: topic=%s", chosen.topic)
        return question

    def get_top_interests(self, n: int = 5) -> list[dict]:
        """Trả về n topics được quan tâm nhất."""
        sorted_topics = sorted(
            self._topics.values(),
            key=lambda t: t.interest_level,
            reverse=True,
        )
        return [
            {"topic": t.topic, "interest": round(t.interest_level, 2), "source": t.source}
            for t in sorted_topics[:n]
        ]


# Global singleton
curiosity_system = CuriositySystem()
