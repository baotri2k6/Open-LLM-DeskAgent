"""ChatInteraction — adapter xử lý tương tác văn bản (Text Chat).

Điều phối luồng:
User Text Input -> LLM -> TTS (nếu có cấu hình giọng nói cho chat) -> UI Response.
"""

from __future__ import annotations

import logging
from typing import Optional

from runtime.events.event_types import EventType
from runtime.events.base_event import BaseEvent, uuid4
from runtime.eventbus.event_bus import event_bus
from runtime.state.state_store import state_store, CompanionState

logger = logging.getLogger("ai-companion.interaction.chat")


class ChatInteraction:
    """Điều phối toàn bộ quy trình tương tác văn bản với companion."""

    def __init__(self) -> None:
        self._llm_manager = None
        self._tts_service = None

    def _init_services(self) -> None:
        """Lazy load services để tránh circular imports."""
        if self._llm_manager is None:
            try:
                from llm.manager import LLMManager
                self._llm_manager = LLMManager()
            except Exception as e:
                logger.error("Failed to load LLMManager: %s", e)

        if self._tts_service is None:
            try:
                from speech.tts.tts_service import TTSService
                self._tts_service = TTSService()
            except Exception as e:
                logger.error("Failed to load TTSService: %s", e)

    async def handle_chat_input(self, text: str, voice_output_enabled: bool = True) -> dict:
        """Nhận văn bản từ ô chat, xử lý và tạo phản hồi.

        Args:
            text: Văn bản của người dùng.
            voice_output_enabled: Có phát âm thanh tts kèm theo không.

        Returns:
            dict chứa thông tin câu trả lời và âm thanh.
        """
        self._init_services()
        correlation_id = uuid4()
        text = text.strip()

        if not text:
            return {"success": False, "error": "Empty text input"}

        # 1. Phát event nhận tin nhắn
        event_bus.publish(BaseEvent.create(
            event_type=EventType.CLIPBOARD_CHANGED if "http" in text else EventType.VOICE_DETECTED, # placeholder
            source="chat_interaction",
            payload={"text": text},
            correlation_id=correlation_id
        ))

        await state_store.transition(CompanionState.THINKING)

        # 2. Gửi LLM để sinh câu trả lời
        if not self._llm_manager:
            await state_store.transition(CompanionState.IDLE)
            return {"success": False, "error": "LLM manager not available"}

        reply_text = await self._llm_manager.chat(text)
        logger.info("Companion response (chat): '%s'", reply_text)

        event_bus.publish(BaseEvent.create(
            event_type=EventType.LLM_FINISHED,
            source="chat_interaction",
            payload={"text": reply_text},
            correlation_id=correlation_id
        ))

        audio_url = None
        duration_ms = 0

        # 3. Phát TTS nếu được bật
        if voice_output_enabled and self._tts_service:
            await state_store.transition(CompanionState.SPEAKING)
            
            event_bus.publish(BaseEvent.create(
                event_type=EventType.TTS_STARTED,
                source="chat_interaction",
                payload={"text": reply_text},
                correlation_id=correlation_id
            ))

            tts_result = await self._tts_service.speak(reply_text)
            audio_url = tts_result.get("audio_url")
            duration_ms = tts_result.get("duration_ms", 0)

            event_bus.publish(BaseEvent.create(
                event_type=EventType.TTS_FINISHED,
                source="chat_interaction",
                correlation_id=correlation_id
            ))

        await state_store.transition(CompanionState.IDLE)

        # 4. Kích hoạt phản ứng biểu cảm ngẫu nhiên
        try:
            from persona.behavior.reactions.reaction_library import reaction_library
            # 50% cơ hội trigger biểu cảm phù hợp
            if duration_ms > 0:
                reaction_library.trigger_random_positive()
        except Exception:
            pass

        return {
            "success": True,
            "text": text,
            "reply": reply_text,
            "audio_url": audio_url,
            "duration_ms": duration_ms
        }


# Global singleton
chat_interaction = ChatInteraction()
