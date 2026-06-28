"""Cognition Engine — Tầng 4: Suy nghĩ và sinh phản hồi (Cognition/LLM Reasoning)."""
from __future__ import annotations
from typing import AsyncGenerator

from llm.manager import LLMService
from persona.dialogue.emotion_parser import EmotionStreamParser

class CognitionEngine:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm = llm_service or LLMService()

    async def reason_stream(self, prompt: str, context: dict, image: str | None = None) -> AsyncGenerator[dict, None]:
        """
        Nhận vào prompt và context packet (Perception + Memory).
        Thực hiện LLM Reasoning và sinh luồng phản hồi chứa:
        - text tokens
        - emotion tags
        """
        parser = EmotionStreamParser()
        
        async for token in self.llm.chat_stream(prompt, context, image=image):
            # Chuyển tiếp trực tiếp nếu token là dict (sự kiện hệ thống hoặc phê duyệt)
            if isinstance(token, dict):
                yield token
                continue
                
            # 1. Feed token vào parser để tìm thẻ cảm xúc [emotion] hoặc emoji
            emotion_chunk = parser.feed(token)
            if emotion_chunk:
                yield emotion_chunk
                
            # 2. Lấy ra văn bản sạch sau khi lọc thẻ cảm xúc
            safe_text = parser.flush_text()
            if safe_text:
                yield {"type": "text", "text": safe_text, "thought": parser.in_thought}
                
        # 3. Đưa nốt phần còn thừa trong parser buffer ra ngoài
        leftover = parser.flush_all()
        if leftover:
            yield {"type": "text", "text": leftover, "thought": parser.in_thought}

