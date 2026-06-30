"""Integration test for the Speech Pipeline (STT -> LLM -> TTS)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from interaction.voice.voice_interaction import VoiceInteraction
from runtime.events.event_types import EventType
from runtime.state.state_store import CompanionState


@pytest.mark.anyio
async def test_speech_pipeline_flow() -> None:
    # Instantiate custom VoiceInteraction coordinator
    vi = VoiceInteraction()
    
    # 1. Mock STTService
    mock_stt = MagicMock()
    mock_stt.transcribe_bytes = AsyncMock(return_value={"success": True, "text": "hello icegirl"})
    
    # 2. Mock LLMManager
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = "Xin chào bạn!"
    
    # 3. Mock TTSService
    mock_tts = MagicMock()
    mock_tts.speak = AsyncMock(return_value={"success": True, "audio_url": "cache/tts/response.wav", "duration_ms": 1500})
    
    # Setup service mocks
    vi._stt_service = mock_stt
    vi._llm_manager = mock_llm
    vi._tts_service = mock_tts
    
    # Capture event bus publications by spying on event_bus.publish
    from runtime.eventbus.event_bus import event_bus
    events_captured = []
    original_publish = event_bus.publish
    
    def mock_publish(event, payload=None):
        if isinstance(event, str):
            events_captured.append(event)
        else:
            events_captured.append(event.event_type)
        original_publish(event, payload)
        
    event_bus.publish = mock_publish
    
    try:
        # Run handle_voice_input with fake audio bytes
        res = await vi.handle_voice_input(b"dummy audio wav bytes")
        
        # Verify transcription and companion response pipeline outputs
        assert res["success"] is True
        assert res["text"] == "hello icegirl"
        assert res["reply"] == "Xin chào bạn!"
        assert res["audio_url"] == "cache/tts/response.wav"
        assert res["duration_ms"] == 1500
        
        # Verify event bus triggered correct sequence of pipeline events
        assert EventType.VOICE_DETECTED in events_captured
        assert EventType.SPEECH_RECOGNIZED in events_captured
        assert EventType.LLM_FINISHED in events_captured
        assert EventType.TTS_STARTED in events_captured
        assert EventType.TTS_FINISHED in events_captured
        
    finally:
        event_bus.publish = original_publish
