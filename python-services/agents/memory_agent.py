"""Memory agent wrapping the JSON memory service."""

from __future__ import annotations

from services.memory_service import MemoryService


class MemoryAgent:
    def __init__(self, service: MemoryService | None = None) -> None:
        self.service = service or MemoryService()

    def remember(self, text: str) -> dict:
        return self.service.remember(text)

    def recall(self, query: str = "") -> list[dict]:
        return self.service.recall(query)

    def profile(self) -> dict:
        return self.service.get_profile()
