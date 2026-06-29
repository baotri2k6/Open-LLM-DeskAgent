"""Streaming TTS — send audio as it generates."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

logger = logging.getLogger("ai-companion.speech.tts.streaming")


class StreamTTS:
    """Manages streaming TTS audio generation chunks."""

    def __init__(self) -> None:
        pass

    async def stream_audio(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream generated audio bytes chunk-by-chunk for the given text."""
        logger.info("StreamTTS: Generating streaming audio for text: '%s'", text[:50])
        
        # Simulate yielding PCM chunk segments (mocking TTS server stream response)
        yield b"\x00\x00\x00\x00\x00\x00\x00\x00"
        yield b"\x11\x11\x11\x11\x11\x11\x11\x11"
        yield b"\x22\x22\x22\x22\x22\x22\x22\x22"


# Global singleton
stream_tts = StreamTTS()
