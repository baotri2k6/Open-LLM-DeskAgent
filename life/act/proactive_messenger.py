"""Proactive Messenger — sends autonomous messages through the WebSocket server."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

logger = logging.getLogger("ai-companion.life")

# ── Message hint → prompt templates ───────────────────────────────────────────
# These are injected as the "user" side of the conversation to trigger
# the companion to generate a contextually appropriate proactive message.

_HINT_PROMPTS: dict[str, str] = {
    "morning_greeting":    "Buổi sáng bắt đầu! Hãy chào người dùng thật nhiệt tình và hỏi thăm hôm nay họ có kế hoạch gì.",
    "idle_long_checkin":   "Người dùng đã im lặng khá lâu. Hãy chủ động hỏi thăm xem họ đang làm gì, có cần giúp gì không, hoặc chia sẻ điều gì đó vui.",
    "idle_short_nudge":    "Người dùng đang tạm dừng. Hãy nhẹ nhàng hỏi thăm hoặc gợi ý điều gì đó thú vị.",
    "share_fun_fact":      "Hãy chủ động chia sẻ một sự thật thú vị hoặc điều hay ho liên quan đến công nghệ, AI, hoặc một chủ đề ngẫu nhiên.",
    "ask_about_project":   "Hãy tò mò hỏi người dùng về dự án họ đang làm, cố gắng hiểu thêm để có thể giúp ích.",
    "express_curiosity":   "Hãy đặt một câu hỏi thú vị xuất phát từ sự tò mò nội tâm của bản thân.",
    "friendly_check_in":   "Hãy tự nhiên hỏi thăm xem người dùng hôm nay thế nào, như một người bạn quan tâm.",
}

_DEFAULT_HINT = "Hãy chủ động bắt chuyện hoặc chia sẻ điều gì đó thú vị với người dùng."


class ProactiveMessenger:
    """
    Sends proactive messages from the companion to the user.

    Flow:
    1. LifeLoop calls `send(decision)` with a Decision object.
    2. ProactiveMessenger builds a synthetic "trigger" message.
    3. Calls LLMService to generate the companion's response.
    4. Pushes the response through the WebSocket server to Electron renderer.
    """

    def __init__(self) -> None:
        self._ws_clients: set = set()  # injected by WebSocket server
        self._llm_service: Any = None  # injected lazily

    def register_ws_clients(self, clients: set) -> None:
        """Inject the WebSocket clients set from the server."""
        self._ws_clients = clients

    async def send(self, action_type: str, message_hint: str) -> bool:
        """
        Generate and send a proactive message.

        Returns True if message was sent successfully.
        """
        trigger_prompt = _HINT_PROMPTS.get(message_hint, _DEFAULT_HINT)

        try:
            llm = self._get_llm()
            if llm is None:
                logger.warning("ProactiveMessenger: LLMService not available")
                return False

            # Generate response using LLM
            full_text = ""
            emotion   = "neutral"
            motion    = "motion_idle"

            async for chunk in llm.chat_stream(
                message=f"[PROACTIVE_TRIGGER] {trigger_prompt}",
                context={"proactive": True, "hint": message_hint},
            ):
                if chunk.get("type") == "text":
                    full_text += chunk.get("text", "")
                elif chunk.get("type") == "emotion":
                    emotion = chunk.get("emotion", emotion)

            if not full_text.strip():
                return False

            # Push to WebSocket clients
            payload = {
                "type":      "companion_message",
                "text":      full_text.strip(),
                "emotion":   emotion,
                "motion":    motion,
                "proactive": True,
                "hint":      message_hint,
            }
            await self._broadcast(payload)
            logger.info(f"ProactiveMessenger: Sent [{message_hint}] — {full_text[:50]}…")
            return True

        except Exception as e:
            logger.error(f"ProactiveMessenger: Error — {e}")
            return False

    async def _broadcast(self, payload: dict) -> None:
        """Send payload to all connected WebSocket clients."""
        if not self._ws_clients:
            logger.debug("ProactiveMessenger: No WebSocket clients connected")
            return
        msg = json.dumps(payload, ensure_ascii=False)
        dead: set = set()
        for client in self._ws_clients:
            try:
                await client.send(msg)
            except Exception:
                dead.add(client)
        self._ws_clients -= dead

    def _get_llm(self):
        """Lazily import LLMService singleton."""
        if self._llm_service is None:
            try:
                from llm.manager import LLMService
                self._llm_service = LLMService()
            except Exception as e:
                logger.error(f"ProactiveMessenger: Cannot load LLMService — {e}")
        return self._llm_service


# ── Global singleton ───────────────────────────────────────────────────────────
proactive_messenger = ProactiveMessenger()
