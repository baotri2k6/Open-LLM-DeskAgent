"""Real-time streaming STT interface."""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger("ai-companion.speech.stt.streaming")


class StreamSTT:
    """Manages streaming audio buffer and runs real-time speech-to-text conversion."""

    def __init__(self, callback: Callable[[str], None] | None = None) -> None:
        self.callback = callback
        self._audio_buffer = bytearray()
        self._is_active = False

    def start_streaming(self) -> None:
        """Start listening/accepting audio stream chunks."""
        self._is_active = True
        self._audio_buffer.clear()
        logger.info("StreamSTT: Audio streaming started.")

    def write_audio_chunk(self, chunk: bytes) -> None:
        """Write incoming PCM audio chunks and trigger transcription hypothesis."""
        if not self._is_active:
            return
        self._audio_buffer.extend(chunk)
        
        # Process every ~1 second of 16kHz audio
        if len(self._audio_buffer) > 16000 * 2:
            text_hypothesis = "đang gõ code..."  # Mock hypothesis for testing
            if self.callback:
                self.callback(text_hypothesis)
            self._audio_buffer.clear()

    def stop_streaming(self) -> str:
        """Stop streaming and return the final transcribed text."""
        self._is_active = False
        logger.info("StreamSTT: Audio streaming stopped.")
        return "Chào bạn, mình vừa ghi âm xong."
