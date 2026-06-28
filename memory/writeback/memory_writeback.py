"""Memory Writeback — consolidates dialog into long-term memories."""

from __future__ import annotations

import logging
import asyncio
from typing import List
from memory.semantic.long_term import long_term_store

logger = logging.getLogger("ai-companion.memory.writeback")


class MemoryWriteback:
    """Consolidates dialog into long-term memories in the background."""

    def __init__(self) -> None:
        self._long_term = long_term_store

    async def write_back(self, user_msg: str, assistant_msg: str) -> None:
        """Analyze turn and write relevant facts to long term memory."""
        if len(user_msg.strip()) < 8:
            return
        
        try:
            prompt = (
                f"Hãy đóng vai trò là hệ thống đúc kết ký ức. Phân tích cuộc hội thoại ngắn sau đây:\n\n"
                f"Người dùng: {user_msg}\n"
                f"AI: {assistant_msg}\n\n"
                f"Nhiệm vụ: Nếu cuộc trò chuyện trên có chứa thông tin cá nhân mới, sở thích, thói quen, "
                f"hoặc yêu cầu cụ thể của người dùng cần nhớ lâu dài, hãy đúc kết nó thành 1 câu khẳng định ngắn gọn "
                f"(Ví dụ: 'Người dùng thích uống cà phê sữa', 'Người dùng tên là Nam và đang học lập trình Web'). "
                f"Nếu không có thông tin gì quan trọng hoặc mới mẻ đáng nhớ, CHỈ trả về từ 'NONE'. "
                f"Không giải thích gì thêm."
            )
            
            from llm.manager import LLMService
            llm = LLMService()
            response = await llm.chat(prompt)
            response_clean = response.strip().strip("-* ").strip()
            
            if response_clean and response_clean.upper() != "NONE" and len(response_clean) > 5:
                # Kiểm tra trùng lặp
                existing = self._long_term.search_facts(response_clean, n_results=1)
                is_duplicate = False
                if existing:
                    # check similarity score or subset match
                    if existing[0]["score"] > 0.85:
                        is_duplicate = True
                        
                if not is_duplicate:
                    self._long_term.add_fact(response_clean, category="turn_reflection")
                    logger.info("Memory Writeback: Saved fact: %s", response_clean)
        except Exception as e:
            logger.warning("Memory writeback failed: %s", e)


# Global singleton
memory_writeback = MemoryWriteback()
