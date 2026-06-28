"""Cognition Engine — Tầng 4: Suy nghĩ và sinh phản hồi (Cognition/LLM Reasoning)."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from llm.manager import LLMService
from persona.dialogue.emotion_parser import EmotionStreamParser
from persona.mood.mood_engine import mood_engine
from persona.emotion.emotion_engine import emotion_engine
from persona.relationship.relationship_tracker import relationship_tracker
from persona.goals.goal_manager import goal_manager
from memory.memory_manager import memory_manager

logger = logging.getLogger("ai-companion.cognition")


class CognitionEngine:
    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm = llm_service or LLMService()

    async def reason_stream(self, prompt: str, context: dict, image: str | None = None) -> AsyncGenerator[dict, None]:
        """
        Nhận vào prompt và context packet.
        Thực hiện các bước:
        1. Phân tích thái độ tin nhắn và cập nhật trạng thái cảm xúc.
        2. Tự động truy xuất ký ức (Memory Retrieval) liên quan từ memory_manager.
        3. Chuẩn bị bối cảnh và nạp trạng thái companion vào context.
        4. Gọi LLM Service để sinh luồng phản hồi.
        5. Lọc cảm xúc qua EmotionStreamParser.
        """
        parser = EmotionStreamParser()

        # ── Step 1: Update Companion States from incoming user text ──────
        try:
            # Ghi nhận tin nhắn mới từ người dùng vào lịch sử memory
            memory_manager.add_turn("user", prompt)
            
            # Cập nhật cảm xúc ngắn hạn từ văn bản của người dùng
            emotion_engine.update_from_user_text(prompt)
            
            # Bổ sung thông tin hoạt động người dùng vào mood_engine
            activity = context.get("perception", {}).get("activity", "unknown")
            mood_engine.inject_activity_modifier(activity)
        except Exception as e:
            logger.warning("CognitionEngine failed to update live companion states: %s", e)

        # ── Step 2: Retrieve Relevant Long-Term Memory Facts ──────
        if prompt and "memory" not in context:
            try:
                recalled = memory_manager.recall_for_prompt(prompt)
                if recalled:
                    context["memory"] = [{"text": s} for s in recalled]
            except Exception as e:
                logger.warning("CognitionEngine memory retrieval failed: %s", e)

        # ── Step 3: Inject Dynamic Companion State into Context ──────
        try:
            mood_state = mood_engine.state
            context["companion"] = {
                "rel_level": relationship_tracker.level,
                "rel_score": relationship_tracker.score,
                "mood": mood_state.mood,
                "time_note": context.get("companion", {}).get("time_note", "")
            }
        except Exception as e:
            logger.warning("CognitionEngine failed to inject companion details: %s", e)

        # ── Step 4: Stream LLM Generation ───
        full_reply_parts = []
        async for token in self.llm.chat_stream(prompt, context, image=image):
            # Chuyển tiếp trực tiếp nếu token là dict (sự kiện hệ thống hoặc phê duyệt)
            if isinstance(token, dict):
                yield token
                continue
                
            # Feed token vào parser để tìm thẻ cảm xúc [emotion] hoặc emoji
            emotion_chunk = parser.feed(token)
            if emotion_chunk:
                yield emotion_chunk
                
            # Lấy ra văn bản sạch sau khi lọc thẻ cảm xúc
            safe_text = parser.flush_text()
            if safe_text:
                full_reply_parts.append(safe_text)
                yield {"type": "text", "text": safe_text, "thought": parser.in_thought}

        # Đưa nốt phần còn thừa trong parser buffer ra ngoài
        leftover = parser.flush_all()
        if leftover:
            full_reply_parts.append(leftover)
            yield {"type": "text", "text": leftover, "thought": parser.in_thought}

        # ── Step 5: Post-Response Reflection & Memory Writeback ───
        full_reply = "".join(full_reply_parts).strip()
        if full_reply:
            try:
                # Ghi nhớ tin nhắn của trợ lý vào lịch sử
                memory_manager.add_turn("assistant", full_reply)
                
                # Cập nhật cảm xúc nhân vật dựa trên nội dung câu trả lời của chính mình
                emotion_engine.update_from_ai_text(full_reply)
                
                # Tích lũy điểm mối quan hệ và kích hoạt hoàn thành mục tiêu (nếu có)
                relationship_tracker.add_points("chat_turn")
                goal_manager.try_complete_by_trigger("conversation")
            except Exception as e:
                logger.warning("CognitionEngine post-response updates failed: %s", e)
