"""ConversationManager — quản lý luồng hội thoại multi-turn.

Theo dõi conversation flow, phát hiện topic shifts,
quản lý conversation depth và biết khi nào nên kết thúc một topic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger("ai-companion.social.conversation")


@dataclass
class ConversationTurn:
    """Một lượt trong cuộc trò chuyện."""
    role:       Literal["user", "assistant"]
    content:    str
    timestamp:  float = field(default_factory=time.time)
    emotion:    str   = "neutral"
    topic:      str   = ""


@dataclass
class ConversationContext:
    """Context của cuộc trò chuyện hiện tại."""
    current_topic:      str             # Topic đang bàn luận
    topic_depth:        int             # Số turn đã nói về topic này
    conversation_type:  str             # casual | technical | emotional | task
    user_engagement:    float           # 0.0 → 1.0 — user có engaged không?
    last_user_turn:     float           # Timestamp lần cuối user nói
    total_turns:        int             # Tổng số turns trong session


class ConversationManager:
    """Quản lý luồng hội thoại và conversation context.

    Cung cấp context để:
    - Companion biết mình đang nói về topic gì
    - Biết user có đang engaged không
    - Biết khi nào nên chuyển chủ đề hoặc kết thúc
    - Inject conversation context vào system prompt
    """

    MAX_TOPIC_DEPTH  = 10    # Tối đa 10 turns về cùng topic trước khi detect topic shift
    ENGAGEMENT_DECAY = 0.1   # Giảm engagement mỗi phút không có response

    def __init__(self) -> None:
        self._turns:    list[ConversationTurn] = []
        self._context = ConversationContext(
            current_topic="",
            topic_depth=0,
            conversation_type="casual",
            user_engagement=0.5,
            last_user_turn=time.time(),
            total_turns=0,
        )
        self._session_start = time.time()

    def on_user_message(self, text: str, emotion: str = "neutral") -> None:
        """Cập nhật context khi user gửi message."""
        self._turns.append(ConversationTurn(
            role="user",
            content=text,
            emotion=emotion,
        ))
        self._context.last_user_turn = time.time()
        self._context.total_turns += 1
        self._context.user_engagement = min(1.0, self._context.user_engagement + 0.15)

        # Detect conversation type từ content
        self._context.conversation_type = self._detect_conv_type(text)

        # Simple topic tracking bằng keyword
        detected_topic = self._detect_topic(text)
        if detected_topic and detected_topic != self._context.current_topic:
            self._context.current_topic = detected_topic
            self._context.topic_depth = 1
        else:
            self._context.topic_depth += 1

    def on_assistant_message(self, text: str) -> None:
        """Cập nhật context khi companion trả lời."""
        self._turns.append(ConversationTurn(
            role="assistant",
            content=text,
        ))

    def tick(self) -> None:
        """Gọi định kỳ để decay engagement."""
        minutes_since_user = (time.time() - self._context.last_user_turn) / 60.0
        decay = self.ENGAGEMENT_DECAY * minutes_since_user
        self._context.user_engagement = max(0.0, self._context.user_engagement - decay)

    def get_recent_turns(self, n: int = 5) -> list[dict]:
        """Trả về n turns gần nhất."""
        recent = self._turns[-n:]
        return [{"role": t.role, "content": t.content, "emotion": t.emotion} for t in recent]

    def _detect_conv_type(self, text: str) -> str:
        """Phát hiện loại conversation từ text."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["code", "bug", "lỗi", "error", "function", "class", "python", "js", "api"]):
            return "technical"
        if any(kw in text_lower for kw in ["buồn", "vui", "cảm xúc", "stress", "mệt", "lo", "nhớ"]):
            return "emotional"
        if any(kw in text_lower for kw in ["làm", "thực hiện", "viết", "tạo", "build", "run", "tìm"]):
            return "task"
        return "casual"

    def _detect_topic(self, text: str) -> str:
        """Detect topic đơn giản từ keywords."""
        text_lower = text.lower()
        topic_keywords = {
            "code": ["python", "javascript", "code", "function", "class", "module"],
            "ai": ["ai", "llm", "model", "gemini", "ollama", "gpt"],
            "project": ["deskagent", "project", "dự án", "repo", "github"],
            "life": ["hôm nay", "hôm qua", "ngủ", "ăn", "mệt", "vui"],
            "tech": ["tech", "programming", "framework", "library"],
        }
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return topic
        return self._context.current_topic  # Giữ topic cũ nếu không detect được

    def describe_for_prompt(self) -> str:
        """Mô tả conversation context cho system prompt."""
        ctx = self._context
        lines = [
            f"Conversation type: {ctx.conversation_type}",
            f"Current topic: {ctx.current_topic or 'general'}",
            f"User engagement: {ctx.user_engagement:.0%}",
            f"Total turns this session: {ctx.total_turns}",
        ]
        return "\n".join(lines)

    def get_state_snapshot(self) -> dict:
        """Snapshot cho API."""
        ctx = self._context
        return {
            "current_topic": ctx.current_topic,
            "conversation_type": ctx.conversation_type,
            "user_engagement": round(ctx.user_engagement, 2),
            "total_turns": ctx.total_turns,
            "topic_depth": ctx.topic_depth,
        }

    def reset(self) -> None:
        """Reset conversation context (khi session mới bắt đầu)."""
        self._turns.clear()
        self._context = ConversationContext(
            current_topic="",
            topic_depth=0,
            conversation_type="casual",
            user_engagement=0.5,
            last_user_turn=time.time(),
            total_turns=0,
        )
        self._session_start = time.time()


# Global singleton
conversation_manager = ConversationManager()
