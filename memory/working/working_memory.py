"""Short-term working memory buffer for active context."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class WorkingMemoryEntry:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    emotion: str = "neutral"


class WorkingMemory:
    """Manages short-term working memory buffer in RAM."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self.entries: list[WorkingMemoryEntry] = []

    def add_turn(self, role: str, content: str, emotion: str = "neutral") -> None:
        self.entries.append(WorkingMemoryEntry(role=role, content=content, emotion=emotion))
        if len(self.entries) > self.max_turns:
            self.entries = self.entries[-self.max_turns:]

    def get_turns(self, last_n: int = 10) -> list[dict]:
        turns = self.entries[-last_n:]
        return [{"role": t.role, "content": t.content, "emotion": t.emotion} for t in turns]

    def clear(self) -> None:
        self.entries.clear()


# Global singleton
working_memory = WorkingMemory()
