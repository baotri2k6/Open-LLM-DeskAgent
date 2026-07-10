"""Handles async token streaming from LLM providers."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

logger = logging.getLogger("ai-companion.llm.streaming")


class StreamHandler:
    """Buffers incoming tokens and yields complete sentences to optimize STT/TTS latency."""

    def __init__(self) -> None:
        self._buffer: list[str] = []

    def feed_token(self, token: str) -> str | None:
        """Feed a single token and return a completed sentence if a boundary is hit."""
        self._buffer.append(token)
        text = "".join(self._buffer)
        
        # Check for sentence boundaries: ., !, ?, \n, or Vietnamese punctuation marks
        if any(boundary in token for boundary in (".", "!", "?", "\n", "。", "！", "？")):
            self._buffer.clear()
            return text.strip()
        return None

    def flush(self) -> str | None:
        """Flush remaining buffer content as the final sentence."""
        if self._buffer:
            text = "".join(self._buffer).strip()
            self._buffer.clear()
            if text:
                return text
        return None
