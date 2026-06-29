"""Parses streaming LLM responses into structured chunks."""

from __future__ import annotations

import re


class StreamParser:
    """Parses streaming LLM tokens, extracting thought blocks (<think>...</think>) from output."""

    def __init__(self) -> None:
        self.in_thought = False
        self._buffer = ""

    def feed(self, token: str) -> dict | None:
        """Feed a token and check if it switches thought modes or yields structured chunks."""
        self._buffer += token
        
        # Check start of thought block
        if "<think>" in self._buffer:
            self.in_thought = True
            self._buffer = self._buffer.replace("<think>", "")
            return {"type": "mode_change", "in_thought": True}
            
        # Check end of thought block
        if "</think>" in self._buffer:
            self.in_thought = False
            self._buffer = self._buffer.replace("</think>", "")
            return {"type": "mode_change", "in_thought": False}

        # Clear buffer and return chunk
        chunk = self._buffer
        self._buffer = ""
        if chunk:
            return {
                "type": "thought" if self.in_thought else "text",
                "text": chunk
            }
        return None

    def flush(self) -> dict | None:
        """Flush remaining buffer content."""
        if self._buffer:
            chunk = self._buffer
            self._buffer = ""
            return {
                "type": "thought" if self.in_thought else "text",
                "text": chunk
            }
        return None
