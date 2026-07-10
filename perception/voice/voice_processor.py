"""Processes voice input before STT."""

from __future__ import annotations

import logging

logger = logging.getLogger("ai-companion.perception.voice")


class VoiceProcessor:
    """Processes voice input before STT."""

    def __init__(self) -> None:
        pass

    def clean_audio_data(self, raw_audio: bytes) -> bytes:
        """Simple mock filtering/denoising of raw audio data."""
        logger.debug("VoiceProcessor: Cleaning raw audio bytes")
        return raw_audio


# Global singleton
voice_processor = VoiceProcessor()
