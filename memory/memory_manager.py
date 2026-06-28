"""MemoryManager — unified facade cho toàn bộ hệ thống memory.

Wraps MemoryService (JSON + ChromaDB) và expose API thống nhất
cho LLM, LifeLoop, PromptBuilder, và API server.

Architecture:
  MemoryManager
  ├── MemoryService  (JSON profile + ChromaDB facts)
  ├── Working Memory (RAM buffer — current conversation turns)
  └── Session Memory (per-session episodic summary)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("ai-companion.memory.manager")


@dataclass
class WorkingMemoryEntry:
    """Một entry trong working memory (RAM, không persist)."""
    role:      str       # "user" | "assistant" | "system"
    content:   str
    timestamp: float = field(default_factory=time.time)
    emotion:   str = "neutral"


class MemoryManager:
    """Unified memory API cho toàn bộ companion.

    Usage:
        from memory.memory_manager import memory_manager
        snippets = memory_manager.recall_for_prompt("câu hỏi user")
        memory_manager.remember("user thích dark mode", "preference")
        memory_manager.add_turn("user", "xin chào")
    """

    MAX_WORKING_MEMORY = 20    # Tối đa 20 turns trong working memory
    MAX_RECALL_RESULTS = 5     # Tối đa 5 kết quả recall cho prompt

    def __init__(self) -> None:
        from memory.working.working_memory import working_memory
        self._working_store = working_memory
        self._service: Any = None   # Lazy init
        self._session_summary: str = ""
        self._session_start: float = time.time()

    def _get_service(self) -> Any:
        """Lazy init MemoryService."""
        if self._service is None:
            try:
                from memory.memory_service import MemoryService
                self._service = MemoryService()
                logger.info("MemoryService initialized")
            except Exception as e:
                logger.warning("MemoryService init failed: %s", e)
                self._service = None
        return self._service

    # ── Working Memory (RAM) ───────────────────────────────────────────────

    def add_turn(self, role: str, content: str, emotion: str = "neutral") -> None:
        """Thêm một turn vào working memory."""
        self._working_store.add_turn(role, content, emotion)

    def get_working_memory(self, last_n: int = 10) -> list[dict]:
        """Lấy n turns gần nhất từ working memory."""
        return self._working_store.get_turns(last_n)

    def get_history_for_llm(self, last_n: int = 15) -> list[dict]:
        """Format working memory cho LLM messages list."""
        turns = self._working_store.entries[-last_n:]
        return [{"role": t.role, "content": t.content} for t in turns]

    def clear_working_memory(self) -> None:
        """Xóa working memory (khi session mới)."""
        self._working_store.clear()

    # ── Persistent Memory ──────────────────────────────────────────────────

    def remember(self, text: str, category: str = "note") -> dict:
        """Lưu một fact vào persistent memory (JSON + ChromaDB nếu có)."""
        svc = self._get_service()
        if svc:
            try:
                result = svc.remember(text, category)
                logger.info("Remembered: [%s] %s", category, text[:60])
                return result
            except Exception as e:
                logger.error("Remember failed: %s", e)
        return {"text": text, "category": category}

    def recall(self, query: str = "") -> list[dict]:
        """Recall facts từ persistent memory theo query."""
        svc = self._get_service()
        if svc:
            try:
                return svc.recall(query)
            except Exception as e:
                logger.warning("Recall failed: %s", e)
        return []

    def recall_for_prompt(self, query: str = "") -> list[str]:
        """Recall và format thành list strings cho PromptBuilder.

        Returns:
            List of strings sẵn sàng inject vào system prompt.
        """
        facts = self.recall(query)
        snippets = []
        for fact in facts[:self.MAX_RECALL_RESULTS]:
            text = fact.get("text", "")
            cat  = fact.get("category", "")
            ts   = fact.get("createdAt", "")[:10] if fact.get("createdAt") else ""
            if text:
                label = f"[{ts}] " if ts else ""
                snippets.append(f"{label}{text}")
        return snippets

    # ── User Profile ───────────────────────────────────────────────────────

    def get_profile(self) -> dict:
        """Lấy user profile đầy đủ."""
        svc = self._get_service()
        if svc:
            try:
                return svc.get_profile()
            except Exception as e:
                logger.warning("Get profile failed: %s", e)
        return {}

    def get_user_name(self) -> str:
        """Tên user nếu đã biết."""
        return self.get_profile().get("name", "")

    # ── Relationship ───────────────────────────────────────────────────────

    def get_relationship(self) -> dict:
        """Thông tin relationship hiện tại."""
        svc = self._get_service()
        if svc:
            try:
                return svc.get_relationship()
            except Exception:
                pass
        return {"score": 15, "level": "Người quen"}

    def update_relationship(self, delta: int) -> dict:
        """Cập nhật relationship score."""
        svc = self._get_service()
        if svc:
            try:
                return svc.update_relationship(delta)
            except Exception as e:
                logger.warning("Relationship update failed: %s", e)
        return {}

    # ── Session ────────────────────────────────────────────────────────────

    def on_session_start(self) -> None:
        """Gọi khi bắt đầu session mới."""
        self.clear_working_memory()
        self._session_start = time.time()
        self._session_summary = ""
        logger.info("MemoryManager: new session started")

    def on_session_end(self, summary: str = "") -> None:
        """Gọi khi kết thúc session — có thể save summary."""
        if summary:
            self._session_summary = summary
            self.remember(summary, category="session_summary")
        logger.info("MemoryManager: session ended (duration=%.0fs)", time.time() - self._session_start)

    # ── Snapshot ───────────────────────────────────────────────────────────

    def get_state_snapshot(self) -> dict:
        """Snapshot cho API /status."""
        return {
            "working_memory_turns": len(self._working),
            "session_duration_s":   int(time.time() - self._session_start),
            "has_vector_store":     getattr(self._get_service(), "_has_vector", False),
        }


# Global singleton
memory_manager = MemoryManager()
