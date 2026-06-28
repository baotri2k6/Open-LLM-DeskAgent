"""Manages context window and compression."""

from __future__ import annotations

import logging
from typing import List
from runtime.context.context_packet import ContextPacket

logger = logging.getLogger("ai-companion.cognition.context")


class ContextManager:
    """Manages the context window history and compression logic."""

    def __init__(self, max_history: int = 15) -> None:
        self.max_history = max_history
        self._history: List[ContextPacket] = []

    def add_packet(self, packet: ContextPacket) -> None:
        """Add a ContextPacket to the history."""
        self._history.append(packet)
        if len(self._history) > self.max_history:
            self._history.pop(0)

    def get_history(self) -> List[ContextPacket]:
        """Get the current context packet history."""
        return self._history

    def clear(self) -> None:
        """Clear context packet history."""
        self._history.clear()


# Global singleton
context_manager = ContextManager()
