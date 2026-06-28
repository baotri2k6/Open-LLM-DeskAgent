"""VoiceInteraction — adapter cho xử lý giọng nói đầu vào và đầu ra.

Điều phối luồng:
Audio Input (Mic/WebM) -> STT -> LLM -> TTS -> Audio Output (WebSocket/OBS).
"""

from __future__ import annotations

import logging
import time
from typing import AsyncGenerator, Optional

from runtime.events.event_types import EventType
from runtime.events.base_event import BaseEvent
from runtime.events.base_event import uuid4
from runtime.eventbus.event_bus import event_bus
from runtime.state.state_store import state_store, CompanionState

logger = logging.getLogger("ai-companion.interaction.voice")


class VoiceInteraction:
    """Điều phối toàn bộ quy trình tương tác giọng nói với companion."""

    def __init__(self) -> None:
        self._stt_service = None
        self._tts_service = None
        self._llm_manager = None

    def _init_services(self) -> None:
        """Lazy load services để tránh circular imports lúc khởi động."""
        if self._stt_service is None:
            try:
                from speech.stt.stt_service import STTService
                self._stt_service = STTService()
            except Exception as e:
                logger.error("Failed to load STTService: %s", e)

        if self._tts_service is None:
            try:
                from speech.tts.tts_service import TTSService
                self._tts_service = TTSService()
            except Exception as e:
                logger.error("Failed to load TTSService: %s", e)

        if self._llm_manager is None:
            try:
                from llm.manager import LLMManager
                self._llm_manager = LLMManager()
            except Exception as e:
                logger.error("Failed to load LLMManager: %s", e)

    async def handle_voice_input(self, audio_bytes: bytes) -> dict:
        """Nhận raw audio bytes từ microphone, chuyển thành text và xử lý.

        Args:
            audio_bytes: Dữ liệu âm thanh thô.

        Returns:
            dict chứa thông tin kết quả STT, câu trả lời, và đường dẫn audio.
        """
        self._init_services()
        correlation_id = uuid4()
        
        # 1. Phát event bắt đầu nhận diện giọng nói
        event_bus.publish(BaseEvent.create(
            event_type=EventType.VOICE_DETECTED,
            source="voice_interaction",
            correlation_id=correlation_id
        ))

        await state_store.transition(CompanionState.LISTENING)

        # 2. Thực hiện STT
        if not self._stt_service:
            await state_store.transition(CompanionState.IDLE)
            return {"success": False, "error": "STT service not available"}

        stt_result = await self._stt_service.transcribe_bytes(audio_bytes)
        if not stt_result.get("success"):
            await state_store.transition(CompanionState.IDLE)
            return {"success": False, "error": stt_result.get("error", "STT failed")}

        text = stt_result.get("text", "").strip()
        logger.info("Voice recognized: '%s'", text)

        event_bus.publish(BaseEvent.create(
            event_type=EventType.SPEECH_RECOGNIZED,
            source="voice_interaction",
            payload={"text": text},
            correlation_id=correlation_id
        ))

        if not text:
            # User không nói gì rõ ràng
            await state_store.transition(CompanionState.IDLE)
            return {"success": True, "text": "", "reply": ""}

        # 3. Gửi LLM để sinh phản hồi
        await state_store.transition(CompanionState.THINKING)
        
        if not self._llm_manager:
            await state_store.transition(CompanionState.IDLE)
            return {"success": False, "error": "LLM manager not available"}

        reply_text = await self._llm_manager.chat(text)
        logger.info("Companion response: '%s'", reply_text)

        event_bus.publish(BaseEvent.create(
            event_type=EventType.LLM_FINISHED,
            source="voice_interaction",
            payload={"text": reply_text},
            correlation_id=correlation_id
        ))

        # 4. Phát TTS
        await state_store.transition(CompanionState.SPEAKING)
        
        if not self._tts_service:
            await state_store.transition(CompanionState.IDLE)
            return {"success": True, "text": text, "reply": reply_text, "audio_url": None}

        event_bus.publish(BaseEvent.create(
            event_type=EventType.TTS_STARTED,
            source="voice_interaction",
            payload={"text": reply_text},
            correlation_id=correlation_id
        ))

        tts_result = await self._tts_service.speak(reply_text)
        
        event_bus.publish(BaseEvent.create(
            event_type=EventType.TTS_FINISHED,
            source="voice_interaction",
            correlation_id=correlation_id
        ))

        await state_store.transition(CompanionState.IDLE)

        return {
            "success": True,
            "text": text,
            "reply": reply_text,
            "audio_url": tts_result.get("audio_url"),
            "duration_ms": tts_result.get("duration_ms", 0)
        }


# Global singleton
voice_interaction = VoiceInteraction()
